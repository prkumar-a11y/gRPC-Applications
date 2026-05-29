"""gRPC service implementation for Job Orchestrator"""
import asyncio
import logging
import uuid
import time
import random
import hashlib
import struct
from typing import AsyncIterator

import grpc

from generated import job_orchestrator_pb2, job_orchestrator_pb2_grpc
from .models import Job, JobState, LogEntry
from .state_store import StateStore

logger = logging.getLogger(__name__)


def _generate_server_stats_bin() -> bytes:
    """Generate binary server stats for trailer header"""
    # Format: 8 bytes for CPU usage (double), 8 bytes for memory usage (double)
    cpu_usage = random.uniform(0.1, 0.9)  # 10-90% CPU
    memory_usage = random.uniform(0.2, 0.8)  # 20-80% memory
    return struct.pack('dd', cpu_usage, memory_usage)


def _generate_load_metrics_bin() -> bytes:
    """Generate binary load metrics for trailer header"""
    # Format: 4 bytes for QPS (int), 4 bytes for active connections (int), 4 bytes for avg latency ms (int)
    qps = random.randint(10, 1000)
    active_connections = random.randint(1, 100)
    avg_latency_ms = random.randint(5, 200)
    return struct.pack('iii', qps, active_connections, avg_latency_ms)


def _calculate_retry_pushback_ms() -> str:
    """Calculate retry pushback delay hint in milliseconds"""
    # Return a retry delay hint (e.g., exponential backoff suggestion)
    return str(random.randint(100, 5000))  # 100ms to 5 seconds


def _generate_trace_id() -> str:
    """Generate a unique trace ID for request tracing"""
    return f"{uuid.uuid4().hex[:5]}-{uuid.uuid4().hex[:5]}-{uuid.uuid4().hex[:5]}"


def _generate_auth_token(context: grpc.aio.ServicerContext) -> bytes:
    """Generate auth token binary data based on auth-token-bin-size header"""
    # Get metadata
    metadata = {}
    for key, value in context.invocation_metadata():
        metadata[key] = value
    
    # Check if custom size is requested
    token_size_str = metadata.get('auth-token-bin-size', '').strip()
    
    if token_size_str:
        try:
            token_size = int(token_size_str)
            # Cap at 10MB for safety
            if token_size < 0:
                token_size = 4
            elif token_size > 10 * 1024 * 1024:
                logger.warning(f"auth-token-bin-size {token_size} exceeds 10MB, capping at 10MB")
                token_size = 10 * 1024 * 1024
            
            if token_size > 0:
                logger.info(f"Generating {token_size} bytes for auth-token-bin trailer")
                # Generate random binary data
                return bytes(random.getrandbits(8) for _ in range(token_size))
        except ValueError:
            logger.warning(f"Invalid auth-token-bin-size value: {token_size_str}, using default")
    
    # Default 4 bytes
    return b'\x01\x02\x03\x04'


# gRPC status code to message mapping for simulation
GRPC_STATUS_MESSAGES = {
    0: "OK",
    1: "Simulated CANCELLED: The operation was cancelled",
    2: "Simulated UNKNOWN: Unknown error occurred",
    3: "Simulated INVALID_ARGUMENT: Client specified an invalid argument",
    4: "Simulated DEADLINE_EXCEEDED: Deadline expired before operation could complete",
    5: "Simulated NOT_FOUND: Some requested entity was not found",
    6: "Simulated ALREADY_EXISTS: The entity already exists",
    7: "Simulated PERMISSION_DENIED: The caller does not have permission",
    8: "Simulated RESOURCE_EXHAUSTED: Some resource has been exhausted",
    9: "Simulated FAILED_PRECONDITION: Operation rejected due to system state",
    10: "Simulated ABORTED: The operation was aborted",
    11: "Simulated OUT_OF_RANGE: Operation attempted past valid range",
    12: "Simulated UNIMPLEMENTED: Operation not implemented or supported",
    13: "Simulated INTERNAL: Internal server error",
    14: "Simulated UNAVAILABLE: The service is currently unavailable",
    15: "Simulated DATA_LOSS: Unrecoverable data loss or corruption",
    16: "Simulated UNAUTHENTICATED: Request lacks valid authentication credentials",
}


def _set_compression_from_client(context: grpc.aio.ServicerContext) -> None:
    """Set compression based on client's grpc-accept-encoding header"""
    # Get metadata
    metadata = {}
    for key, value in context.invocation_metadata():
        metadata[key] = value
    
    # Check what encodings the client accepts
    accept_encoding = metadata.get('grpc-accept-encoding', '').lower()
    
    # Set compression based on client preference
    # The grpc-accept-encoding header contains comma-separated list of accepted encodings
    if 'deflate' in accept_encoding:
        context.set_compression(grpc.Compression.Deflate)
        logger.debug("Using deflate compression based on client request")
    elif 'gzip' in accept_encoding:
        context.set_compression(grpc.Compression.Gzip)
        logger.debug("Using gzip compression based on client request")
    # If no specific encoding is requested or only 'identity', don't set compression
    # which allows gRPC to use its default behavior


async def _check_simulate_error(context: grpc.aio.ServicerContext) -> None:
    """Check if simulate-grpc-status header is present and abort if needed"""
    # Get metadata
    metadata = {}
    for key, value in context.invocation_metadata():
        metadata[key] = value
    
    simulate_status = metadata.get('simulate-grpc-status', '').strip()
    
    if simulate_status:
        try:
            status_code = int(simulate_status)
            if status_code == 0:
                # Status 0 is OK, don't abort
                return
            
            # Map integer to gRPC status code
            status_map = {
                1: grpc.StatusCode.CANCELLED,
                2: grpc.StatusCode.UNKNOWN,
                3: grpc.StatusCode.INVALID_ARGUMENT,
                4: grpc.StatusCode.DEADLINE_EXCEEDED,
                5: grpc.StatusCode.NOT_FOUND,
                6: grpc.StatusCode.ALREADY_EXISTS,
                7: grpc.StatusCode.PERMISSION_DENIED,
                8: grpc.StatusCode.RESOURCE_EXHAUSTED,
                9: grpc.StatusCode.FAILED_PRECONDITION,
                10: grpc.StatusCode.ABORTED,
                11: grpc.StatusCode.OUT_OF_RANGE,
                12: grpc.StatusCode.UNIMPLEMENTED,
                13: grpc.StatusCode.INTERNAL,
                14: grpc.StatusCode.UNAVAILABLE,
                15: grpc.StatusCode.DATA_LOSS,
                16: grpc.StatusCode.UNAUTHENTICATED,
            }
            
            grpc_status = status_map.get(status_code)
            message = GRPC_STATUS_MESSAGES.get(status_code, f"Simulated error with status code {status_code}")
            
            if grpc_status:
                logger.info(f"Simulating gRPC error: status={status_code}, message={message}")
                # Send initial metadata first to force a separate response HEADERS frame,
                # ensuring grpc-status and grpc-message are sent as trailers (not trailers-only mode)
                await context.send_initial_metadata([])
                await context.abort(grpc_status, message)
        except ValueError:
            logger.warning(f"Invalid simulate-grpc-status value: {simulate_status}")


class JobOrchestratorServicer(job_orchestrator_pb2_grpc.JobOrchestratorServicer):
    """Implementation of JobOrchestrator service"""
    
    def __init__(self, state_store: StateStore):
        self.state = state_store
        self.background_tasks = set()
    
    # UNARY RPC: Submit a job
    async def SubmitJob(
        self,
        request: job_orchestrator_pb2.JobSpec,
        context: grpc.aio.ServicerContext
    ) -> job_orchestrator_pb2.JobAck:
        """Submit a new job for execution"""
        # Check for simulated error status
        await _check_simulate_error(context)
        
        # Validate input data
        if not request.name or request.name.strip() == "":
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Payload not as expected: job name cannot be empty"
            )
        
        if len(request.name) > 100:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Payload not as expected: job name exceeds maximum length of 100 characters"
            )
        
        job_id = str(uuid.uuid4())[:8]
        
        logger.info(f"Submitting job: {request.name} with params: {dict(request.params)}")
        
        # Create job
        job = Job(
            job_id=job_id,
            name=request.name,
            params=dict(request.params),
            state=JobState.PENDING
        )
        
        await self.state.create_job(job)
        
        # Start background execution
        task = asyncio.create_task(self._execute_job(job_id))
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        
        # Set trailer headers
        context.set_trailing_metadata([
            ('grpc-server-stats-bin', _generate_server_stats_bin()),
            ('grpc-retry-pushback-ms', _calculate_retry_pushback_ms()),
            ('endpoint-load-metrics-bin', _generate_load_metrics_bin()),
            ('x-trace-id', _generate_trace_id()),
            ('client-version', '1.76.0'),
            ('feature-flags', 'beta-mode'),
            ('auth-token-bin', _generate_auth_token(context))
        ])
        
        return job_orchestrator_pb2.JobAck(
            job_id=job_id,
            message=f"Job '{request.name}' submitted successfully"
        )
    
    # UNARY RPC: Get job status
    async def GetJobStatus(
        self,
        request: job_orchestrator_pb2.JobId,
        context: grpc.aio.ServicerContext
    ) -> job_orchestrator_pb2.JobStatus:
        """Get current status of a job"""
        # Check for simulated error status
        await _check_simulate_error(context)
        
        job = await self.state.get_job(request.id)
        
        if not job:
            await context.abort(grpc.StatusCode.NOT_FOUND, f"Job {request.id} not found")
        
        # Set trailer headers
        context.set_trailing_metadata([
            ('grpc-server-stats-bin', _generate_server_stats_bin()),
            ('grpc-retry-pushback-ms', _calculate_retry_pushback_ms()),
            ('endpoint-load-metrics-bin', _generate_load_metrics_bin()),
            ('x-trace-id', _generate_trace_id()),
            ('client-version', '1.76.0'),
            ('feature-flags', 'beta-mode'),
            ('auth-token-bin', _generate_auth_token(context))
        ])
        
        return job_orchestrator_pb2.JobStatus(
            job_id=job.job_id,
            state=job.state.value,
            message=job.message,
            created_at=job.created_at,
            updated_at=job.updated_at,
            params=job.params
        )
    
    # CLIENT STREAMING RPC: Push logs
    async def PushLogs(
        self,
        request_iterator: AsyncIterator[job_orchestrator_pb2.LogLine],
        context: grpc.aio.ServicerContext
    ) -> job_orchestrator_pb2.LogSummary:
        """Receive stream of log lines and return summary"""
        # Check for simulated error status
        await _check_simulate_error(context)
        
        total_lines = 0
        error_lines = 0
        warn_lines = 0
        job_id = None
        
        try:
            async for log_line in request_iterator:
                job_id = log_line.job_id
                
                # Validate input data
                if not job_id or job_id.strip() == "":
                    raise ValueError("Payload not as expected: job_id cannot be empty")
                
                if not log_line.line or log_line.line.strip() == "":
                    # Skip empty log lines instead of raising error
                    continue
                
                if len(log_line.line) > 10 * 1024 * 1024:
                    raise ValueError("Payload not as expected: log line exceeds maximum length of 10MB")
                
                total_lines += 1
                
                # Count error and warning lines
                line_lower = log_line.line.lower()
                if 'error' in line_lower or log_line.level == 'ERROR':
                    error_lines += 1
                if 'warn' in line_lower or log_line.level == 'WARN':
                    warn_lines += 1
                
                # Store log
                log_entry = LogEntry(
                    job_id=log_line.job_id,
                    line=log_line.line,
                    timestamp_ms=log_line.timestamp_ms,
                    level=log_line.level or "INFO"
                )
                await self.state.add_log(log_entry)
                
                # Notify session subscribers about new log
                await self.state.notify_session_subscribers(
                    job_id,
                    'LOG',
                    f"[{log_line.level or 'INFO'}] {log_line.line}"
                )
            
            logger.info(f"Received {total_lines} log lines for job {job_id}")
            
            # Set trailer headers
            context.set_trailing_metadata([
                ('grpc-server-stats-bin', _generate_server_stats_bin()),
                ('grpc-retry-pushback-ms', _calculate_retry_pushback_ms()),
                ('endpoint-load-metrics-bin', _generate_load_metrics_bin()),
                ('x-trace-id', _generate_trace_id()),
                ('client-version', '1.76.0'),
                ('feature-flags', 'beta-mode'),
                ('auth-token-bin', _generate_auth_token(context))
            ])
            
            return job_orchestrator_pb2.LogSummary(
                job_id=job_id or "unknown",
                total_lines=total_lines,
                error_lines=error_lines,
                warn_lines=warn_lines,
                message=f"Processed {total_lines} log lines ({error_lines} errors, {warn_lines} warnings)"
            )
        
        except Exception as e:
            logger.error(f"Error in PushLogs: {e}")
            raise
    
    # SERVER STREAMING RPC: Watch job updates
    async def WatchJob(
        self,
        request: job_orchestrator_pb2.JobId,
        context: grpc.aio.ServicerContext
    ) -> AsyncIterator[job_orchestrator_pb2.JobUpdate]:
        """Stream job updates to client"""
        # Check for simulated error status
        await _check_simulate_error(context)
        
        # Enable compression based on client's accept-encoding header
        _set_compression_from_client(context)
        
        # Validate input data
        if not request.id or request.id.strip() == "":
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Payload not as expected: job_id cannot be empty"
            )
        
        job = await self.state.get_job(request.id)
        
        if not job:
            await context.abort(grpc.StatusCode.NOT_FOUND, f"Job {request.id} not found")
        
        logger.info(f"Client watching job {request.id}")
        
        # Send initial status
        yield job_orchestrator_pb2.JobUpdate(
            job_id=job.job_id,
            state=job.state.value,
            detail=f"Current state: {job.message or 'Initialized'}",
            timestamp_ms=int(time.time() * 1000),
            progress_percent=job.progress
        )
        
        # Create queue for updates
        update_queue = asyncio.Queue()
        
        async def on_job_update(updated_job: Job):
            """Callback for job updates"""
            await update_queue.put(updated_job)
        
        # Subscribe to updates
        await self.state.subscribe_to_job(request.id, on_job_update)
        
        try:
            # Stream updates until job completes or client disconnects
            while True:
                # Check if context is cancelled
                if context.cancelled():
                    logger.info(f"Client disconnected from job {request.id}")
                    break
                
                try:
                    # Wait for update with timeout for heartbeat
                    updated_job = await asyncio.wait_for(update_queue.get(), timeout=5.0)
                    
                    yield job_orchestrator_pb2.JobUpdate(
                        job_id=updated_job.job_id,
                        state=updated_job.state.value,
                        detail=updated_job.message,
                        timestamp_ms=updated_job.updated_at,
                        progress_percent=updated_job.progress
                    )
                    
                    # If job is in terminal state, end stream
                    if updated_job.state in [JobState.COMPLETED, JobState.FAILED]:
                        logger.info(f"Job {request.id} reached terminal state: {updated_job.state}")
                        break
                
                except asyncio.TimeoutError:
                    # Send heartbeat
                    current_job = await self.state.get_job(request.id)
                    if current_job:
                        yield job_orchestrator_pb2.JobUpdate(
                            job_id=current_job.job_id,
                            state=current_job.state.value,
                            detail="[Heartbeat]",
                            timestamp_ms=int(time.time() * 1000),
                            progress_percent=current_job.progress
                        )
        
        finally:
            # Cleanup subscription
            await self.state.unsubscribe_from_job(request.id, on_job_update)
            logger.info(f"Stopped watching job {request.id}")
            
            # Set trailer headers
            context.set_trailing_metadata([
                ('grpc-server-stats-bin', _generate_server_stats_bin()),
                ('grpc-retry-pushback-ms', _calculate_retry_pushback_ms()),
                ('endpoint-load-metrics-bin', _generate_load_metrics_bin()),
                ('x-trace-id', _generate_trace_id()),
                ('client-version', '1.76.0'),
                ('feature-flags', 'beta-mode'),
                ('auth-token-bin', _generate_auth_token(context))
            ])
    
    # BIDIRECTIONAL STREAMING RPC: Interactive session
    async def InteractiveSession(
        self,
        request_iterator: AsyncIterator[job_orchestrator_pb2.ControlMessage],
        context: grpc.aio.ServicerContext
    ) -> AsyncIterator[job_orchestrator_pb2.SessionEvent]:
        """Interactive session for job control"""
        # Check for simulated error status
        await _check_simulate_error(context)
        
        # Enable compression based on client's accept-encoding header
        _set_compression_from_client(context)
        
        session_queue = asyncio.Queue()
        session_active = True
        current_job_id = None
        
        async def handle_commands():
            """Handle incoming control messages"""
            nonlocal current_job_id, session_active
            
            try:
                async for control_msg in request_iterator:
                    current_job_id = control_msg.job_id
                    command = control_msg.command.upper()
                    
                    # Validate input data
                    if not current_job_id or current_job_id.strip() == "":
                        await session_queue.put({
                            'job_id': 'unknown',
                            'event_type': 'ERROR',
                            'payload': 'Payload not as expected: job_id cannot be empty',
                            'timestamp_ms': int(time.time() * 1000)
                        })
                        continue
                    
                    if not command or command.strip() == "":
                        await session_queue.put({
                            'job_id': current_job_id,
                            'event_type': 'ERROR',
                            'payload': 'Payload not as expected: command cannot be empty',
                            'timestamp_ms': int(time.time() * 1000)
                        })
                        continue
                    
                    logger.info(f"Session command for job {current_job_id}: {command}")
                    
                    job = await self.state.get_job(current_job_id)
                    if not job:
                        await session_queue.put({
                            'job_id': current_job_id,
                            'event_type': 'ERROR',
                            'payload': f'Job {current_job_id} not found',
                            'timestamp_ms': int(time.time() * 1000)
                        })
                        continue
                    
                    # Process command
                    if command == 'PAUSE':
                        await self.state.update_job(current_job_id, JobState.PAUSED, "Paused by user")
                        await session_queue.put({
                            'job_id': current_job_id,
                            'event_type': 'ACK',
                            'payload': 'Job paused',
                            'timestamp_ms': int(time.time() * 1000)
                        })
                    
                    elif command == 'RESUME':
                        if job.state == JobState.PAUSED:
                            await self.state.update_job(current_job_id, JobState.RUNNING, "Resumed by user")
                            await session_queue.put({
                                'job_id': current_job_id,
                                'event_type': 'ACK',
                                'payload': 'Job resumed',
                                'timestamp_ms': int(time.time() * 1000)
                            })
                        else:
                            await session_queue.put({
                                'job_id': current_job_id,
                                'event_type': 'ERROR',
                                'payload': f'Cannot resume job in state {job.state}',
                                'timestamp_ms': int(time.time() * 1000)
                            })
                    
                    elif command == 'CANCEL':
                        await self.state.update_job(current_job_id, JobState.FAILED, "Cancelled by user")
                        await session_queue.put({
                            'job_id': current_job_id,
                            'event_type': 'ACK',
                            'payload': 'Job cancelled',
                            'timestamp_ms': int(time.time() * 1000)
                        })
                    
                    elif command == 'SET_LOG_LEVEL':
                        level = control_msg.arg.upper() or 'INFO'
                        job.log_level = level
                        await session_queue.put({
                            'job_id': current_job_id,
                            'event_type': 'ACK',
                            'payload': f'Log level set to {level}',
                            'timestamp_ms': int(time.time() * 1000)
                        })
                    
                    elif command == 'GET_STATUS':
                        await session_queue.put({
                            'job_id': current_job_id,
                            'event_type': 'STATUS',
                            'payload': f'State: {job.state.value}, Progress: {job.progress}%, Message: {job.message}',
                            'timestamp_ms': int(time.time() * 1000)
                        })
                    
                    else:
                        await session_queue.put({
                            'job_id': current_job_id,
                            'event_type': 'ERROR',
                            'payload': f'Unknown command: {command}',
                            'timestamp_ms': int(time.time() * 1000)
                        })
            
            except Exception as e:
                logger.error(f"Error handling commands: {e}")
            finally:
                session_active = False
        
        # Start command handler
        command_task = asyncio.create_task(handle_commands())
        
        try:
            # Send welcome message
            yield job_orchestrator_pb2.SessionEvent(
                job_id="",
                event_type="ACK",
                payload="Interactive session started. Available commands: PAUSE, RESUME, CANCEL, SET_LOG_LEVEL, GET_STATUS",
                timestamp_ms=int(time.time() * 1000)
            )
            
            # Stream events
            while session_active or not session_queue.empty():
                try:
                    event = await asyncio.wait_for(session_queue.get(), timeout=2.0)
                    
                    yield job_orchestrator_pb2.SessionEvent(
                        job_id=event['job_id'],
                        event_type=event['event_type'],
                        payload=event['payload'],
                        timestamp_ms=event['timestamp_ms']
                    )
                
                except asyncio.TimeoutError:
                    # Check if client disconnected
                    if context.cancelled():
                        break
        
        finally:
            command_task.cancel()
            if current_job_id:
                await self.state.unsubscribe_from_session(current_job_id, session_queue)
            logger.info("Interactive session ended")
            
            # Set trailer headers
            context.set_trailing_metadata([
                ('grpc-server-stats-bin', _generate_server_stats_bin()),
                ('grpc-retry-pushback-ms', _calculate_retry_pushback_ms()),
                ('endpoint-load-metrics-bin', _generate_load_metrics_bin()),
                ('x-trace-id', _generate_trace_id()),
                ('client-version', '1.76.0'),
                ('feature-flags', 'beta-mode'),
                ('auth-token-bin', _generate_auth_token(context))
            ])
    
    async def _execute_job(self, job_id: str):
        """Background task to simulate job execution"""
        try:
            # Get job to read params
            job = await self.state.get_job(job_id)
            
            # Get number of steps from params, default to 10
            num_steps = int(job.params.get('steps', 10))
            if num_steps < 1:
                num_steps = 1
            elif num_steps > 1000:
                num_steps = 1000  # Cap at 1000 for sanity
            
            # Wait a bit before starting
            await asyncio.sleep(2)
            
            # Start job
            await self.state.update_job(job_id, JobState.RUNNING, f"Job started ({num_steps} steps)", progress=0)
            
            # Simulate work in stages
            for i in range(1, num_steps + 1):
                job = await self.state.get_job(job_id)
                
                # Check if paused or cancelled
                if job.state == JobState.PAUSED:
                    # Wait for resume
                    while job.state == JobState.PAUSED:
                        await asyncio.sleep(1)
                        job = await self.state.get_job(job_id)
                
                if job.state == JobState.FAILED:
                    logger.info(f"Job {job_id} was cancelled")
                    return
                
                # Simulate work
                await asyncio.sleep(random.uniform(1, 3))
                
                progress = int((i / num_steps) * 100)
                await self.state.update_job(
                    job_id,
                    JobState.RUNNING,
                    f"Processing step {i}/{num_steps}",
                    progress=progress
                )
                
                # Occasionally send log events
                if i % 3 == 0:
                    await self.state.notify_session_subscribers(
                        job_id,
                        'LOG',
                        f"Completed {progress}% of work"
                    )
            
            # Randomly succeed or fail (90% success)
            if random.random() < 0.9:
                await self.state.update_job(job_id, JobState.COMPLETED, "Job completed successfully", progress=100)
            else:
                await self.state.update_job(job_id, JobState.FAILED, "Job failed due to simulated error", progress=100)
        
        except Exception as e:
            logger.error(f"Error executing job {job_id}: {e}")
            await self.state.update_job(job_id, JobState.FAILED, f"Internal error: {str(e)}")
    
    # BIDIRECTIONAL STREAMING RPC: Sized data exchange for testing
    async def SizedInteractiveSession(
        self,
        request_iterator: AsyncIterator[job_orchestrator_pb2.SizedDataPacket],
        context: grpc.aio.ServicerContext
    ) -> AsyncIterator[job_orchestrator_pb2.SizedDataPacket]:
        """Bidirectional streaming for sized data exchange and processing"""
        # Check for simulated error status
        await _check_simulate_error(context)
        
        # Enable compression based on client's accept-encoding header
        _set_compression_from_client(context)
        
        logger.info("SizedInteractiveSession started")
        
        packet_count = 0
        total_bytes_received = 0
        total_bytes_sent = 0
        
        try:
            # Send welcome message
            yield job_orchestrator_pb2.SizedDataPacket(
                packet_id="session-init",
                log_file="",
                data=b"",
                data_size=0,
                timestamp_ms=int(time.time() * 1000),
                processed=True,
                checksum="",
                processing_info="Interactive session started.",
                metadata={"event_type": "ACK", "session_status": "started"}
            )
            
            async for packet in request_iterator:
                packet_count += 1
                
                # Validate input
                if not packet.packet_id or packet.packet_id.strip() == "":
                    logger.warning("Received packet with empty packet_id, generating one")
                    packet.packet_id = f"auto-{uuid.uuid4().hex[:8]}"
                
                received_size = len(packet.data) if packet.data else 0
                total_bytes_received += received_size
                
                logger.info(
                    f"Received packet #{packet_count}: id={packet.packet_id}, "
                    f"data_size={received_size}, log_file={packet.log_file[:50] if packet.log_file else 'None'}..."
                )
                
                # Process the packet - calculate checksum if not provided
                if packet.data and not packet.checksum:
                    checksum = hashlib.md5(packet.data).hexdigest()
                else:
                    checksum = packet.checksum
                
                # Prepare processing info
                processing_info = {
                    'received_at': int(time.time() * 1000),
                    'packet_number': packet_count,
                    'bytes_received': received_size,
                    'total_bytes_received': total_bytes_received,
                }
                
                # Add compression info if data is compressible
                if packet.data and len(packet.data) > 100:
                    # Check if data is compressible by looking for patterns
                    sample = packet.data[:100]
                    unique_bytes = len(set(sample))
                    if unique_bytes < 20:  # Likely compressible
                        processing_info['data_type'] = 'compressible'
                    else:
                        processing_info['data_type'] = 'random'
                
                # Create response packet
                response_packet = job_orchestrator_pb2.SizedDataPacket(
                    packet_id=packet.packet_id,
                    log_file=packet.log_file,
                    data=packet.data,  # Echo back the data
                    data_size=received_size,
                    timestamp_ms=int(time.time() * 1000),
                    processed=True,  # Mark as processed
                    checksum=checksum,
                    processing_info=str(processing_info)
                )
                
                # Copy metadata and add server processing metadata
                for key, value in packet.metadata.items():
                    response_packet.metadata[key] = value
                response_packet.metadata['server_processed'] = 'true'
                response_packet.metadata['processing_time_ms'] = str(int(time.time() * 1000) - packet.timestamp_ms)
                response_packet.metadata['packet_count'] = str(packet_count)
                
                total_bytes_sent += received_size
                
                logger.info(
                    f"Sending processed packet #{packet_count}: id={packet.packet_id}, "
                    f"processed=True, checksum={checksum[:8]}..."
                )
                
                yield response_packet
                
                # Check for client disconnect
                if context.cancelled():
                    logger.info(f"Client disconnected after {packet_count} packets")
                    break
        
        except Exception as e:
            logger.error(f"Error in SizedInteractiveSession: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        finally:
            logger.info(
                f"SizedInteractiveSession ended: packets={packet_count}, "
                f"received={total_bytes_received} bytes, sent={total_bytes_sent} bytes"
            )
            
            # Set trailer headers
            context.set_trailing_metadata([
                ('grpc-server-stats-bin', _generate_server_stats_bin()),
                ('grpc-retry-pushback-ms', _calculate_retry_pushback_ms()),
                ('endpoint-load-metrics-bin', _generate_load_metrics_bin()),
                ('x-trace-id', _generate_trace_id()),
                ('session-packets-processed', str(packet_count)),
                ('session-bytes-received', str(total_bytes_received)),
                ('session-bytes-sent', str(total_bytes_sent)),
                ('auth-token-bin', _generate_auth_token(context))
            ])
    
    # SERVER STREAMING RPC: Stress/load testing endpoint
    async def GetSizedResponse(
        self,
        request: job_orchestrator_pb2.SizedResponseRequest,
        context: grpc.aio.ServicerContext
    ) -> AsyncIterator[job_orchestrator_pb2.SizedResponseChunk]:
        """Generate sized response for stress/load testing"""
        # Check for simulated error status
        await _check_simulate_error(context)
        
        # Enable compression based on client's accept-encoding header
        _set_compression_from_client(context)
        
        # Validate input
        if request.stream_size <= 0:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Payload not as expected: stream_size must be greater than 0"
            )
        
        if request.total_size <= 0:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Payload not as expected: total_size must be greater than 0"
            )
        
        if request.stream_size > 10 * 1024 * 1024:  # 10MB max per chunk
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Payload not as expected: stream_size cannot exceed 10MB (10485760 bytes)"
            )
        
        if request.total_size > 1024 * 1024 * 1024:  # 1GB max total
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Payload not as expected: total_size cannot exceed 1GB (1073741824 bytes)"
            )
        
        if request.delay_ms < 0:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Payload not as expected: delay_ms cannot be negative"
            )
        
        if request.error_rate < 0.0 or request.error_rate > 1.0:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Payload not as expected: error_rate must be between 0.0 and 1.0"
            )
        
        # Calculate number of chunks
        total_chunks = (request.total_size + request.stream_size - 1) // request.stream_size
        total_sent = 0
        delay_seconds = request.delay_ms / 1000.0 if request.delay_ms > 0 else 0
        include_metadata = request.include_metadata if hasattr(request, 'include_metadata') else True
        
        logger.info(
            f"Starting sized response: stream_size={request.stream_size}, "
            f"total_size={request.total_size}, chunks={total_chunks}, "
            f"delay={request.delay_ms}ms, compressible={request.compressible}, "
            f"error_rate={request.error_rate}"
        )
        
        for chunk_num in range(1, total_chunks + 1):
            # Check for client disconnect
            if context.cancelled():
                logger.info(f"Client disconnected during sized response at chunk {chunk_num}/{total_chunks}")
                break
            
            # Simulate random errors if requested
            if request.error_rate > 0 and random.random() < request.error_rate:
                await context.abort(
                    grpc.StatusCode.INTERNAL,
                    f"Simulated error at chunk {chunk_num}/{total_chunks}"
                )
            
            # Calculate chunk size (last chunk may be smaller)
            remaining = request.total_size - total_sent
            chunk_size = min(request.stream_size, remaining)
            
            # Generate data
            if request.compressible:
                # Compressible data: repeating pattern
                pattern = b"ABCDEFGH" * 128  # 1KB repeating pattern
                data = (pattern * ((chunk_size // len(pattern)) + 1))[:chunk_size]
            else:
                # Random data (incompressible)
                data = bytes(random.getrandbits(8) for _ in range(chunk_size))
            
            # Calculate checksum if metadata is included
            checksum = ""
            if include_metadata:
                checksum = hashlib.md5(data).hexdigest()
            
            total_sent += chunk_size
            
            # Create response
            chunk_response = job_orchestrator_pb2.SizedResponseChunk(
                chunk_number=chunk_num,
                total_chunks=total_chunks,
                data=data,
                chunk_size=chunk_size,
                total_sent=total_sent,
                timestamp_ms=int(time.time() * 1000),
                checksum=checksum
            )
            
            yield chunk_response
            
            # Add delay if requested
            if delay_seconds > 0 and chunk_num < total_chunks:
                await asyncio.sleep(delay_seconds)
        
        logger.info(
            f"Completed sized response: sent {total_sent} bytes in {total_chunks} chunks"
        )
        
        # Set trailer headers
        context.set_trailing_metadata([
            ('grpc-server-stats-bin', _generate_server_stats_bin()),
            ('grpc-retry-pushback-ms', _calculate_retry_pushback_ms()),
            ('endpoint-load-metrics-bin', _generate_load_metrics_bin()),
            ('x-trace-id', _generate_trace_id()),
            ('client-version', '1.76.0'),
            ('feature-flags', 'beta-mode'),
            ('auth-token-bin', _generate_auth_token(context))
        ])
    
    # UNARY RPC: Just trailers, no response body
    async def JustTrailers(
        self,
        request: job_orchestrator_pb2.Empty,
        context: grpc.aio.ServicerContext
    ) -> job_orchestrator_pb2.Empty:
        """Return only trailers with no meaningful response body"""
        # Check for simulated error status
        await _check_simulate_error(context)
        
        logger.info("JustTrailers endpoint called - returning only trailers")
        
        # Set trailer headers only - this is the main purpose of this endpoint
        context.set_trailing_metadata([
            ('grpc-server-stats-bin', _generate_server_stats_bin()),
            ('grpc-retry-pushback-ms', _calculate_retry_pushback_ms()),
            ('endpoint-load-metrics-bin', _generate_load_metrics_bin()),
            ('x-trace-id', _generate_trace_id()),
            ('client-version', '1.76.0'),
            ('feature-flags', 'beta-mode'),
            ('auth-token-bin', _generate_auth_token(context))
        ])
        
        # Return empty message
        return job_orchestrator_pb2.Empty()
    
    # UNARY RPC: Generate sized response in single unary call
    async def UnarySizedResponse(
        self,
        request: job_orchestrator_pb2.SizedResponseRequest,
        context: grpc.aio.ServicerContext
    ) -> job_orchestrator_pb2.UnarySizedResponseData:
        """Generate sized response as a single unary response"""
        # Check for simulated error status
        await _check_simulate_error(context)
        
        # Enable compression based on client's accept-encoding header
        _set_compression_from_client(context)
        
        # Validate input - for unary, we ignore stream_size and just use total_size
        if request.total_size <= 0:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Payload not as expected: total_size must be greater than 0"
            )
        
        if request.total_size > 100 * 1024 * 1024:  # 100MB max for unary
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Payload not as expected: total_size cannot exceed 100MB (104857600 bytes) for unary response"
            )
        
        if request.error_rate < 0.0 or request.error_rate > 1.0:
            await context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Payload not as expected: error_rate must be between 0.0 and 1.0"
            )
        
        # Simulate random error if requested
        if request.error_rate > 0 and random.random() < request.error_rate:
            await context.abort(
                grpc.StatusCode.INTERNAL,
                f"Simulated error during unary sized response"
            )
        
        include_metadata = request.include_metadata if hasattr(request, 'include_metadata') else True
        data_size = request.total_size
        
        logger.info(
            f"Starting unary sized response: total_size={request.total_size}, "
            f"compressible={request.compressible}, error_rate={request.error_rate}"
        )
        
        # Generate data
        if request.compressible:
            # Compressible data: repeating pattern
            pattern = b"ABCDEFGH" * 128  # 1KB repeating pattern
            data = (pattern * ((data_size // len(pattern)) + 1))[:data_size]
        else:
            # Random data (incompressible)
            data = bytes(random.getrandbits(8) for _ in range(data_size))
        
        # Calculate checksum if metadata is included
        checksum = ""
        if include_metadata:
            checksum = hashlib.md5(data).hexdigest()
        
        # Create response
        response = job_orchestrator_pb2.UnarySizedResponseData(
            data=data,
            data_size=data_size,
            timestamp_ms=int(time.time() * 1000),
            checksum=checksum
        )
        
        logger.info(
            f"Completed unary sized response: sent {data_size} bytes"
        )
        
        # Set trailer headers
        context.set_trailing_metadata([
            ('grpc-server-stats-bin', _generate_server_stats_bin()),
            ('grpc-retry-pushback-ms', _calculate_retry_pushback_ms()),
            ('endpoint-load-metrics-bin', _generate_load_metrics_bin()),
            ('x-trace-id', _generate_trace_id()),
            ('client-version', '1.76.0'),
            ('feature-flags', 'beta-mode'),
            ('auth-token-bin', _generate_auth_token(context))
        ])
        
        return response

