"""CLI client for Job Orchestrator gRPC service"""
import asyncio
import argparse
import sys
import time
from pathlib import Path

import grpc

from generated import job_orchestrator_pb2, job_orchestrator_pb2_grpc


async def submit_job(stub, name: str, params: dict):
    """Submit a new job (UNARY)"""
    request = job_orchestrator_pb2.JobSpec(
        name=name,
        params=params
    )
    
    response = await stub.SubmitJob(request)
    print(f"✓ Job submitted successfully!")
    print(f"  Job ID: {response.job_id}")
    print(f"  Message: {response.message}")
    return response.job_id


async def get_status(stub, job_id: str):
    """Get job status (UNARY)"""
    request = job_orchestrator_pb2.JobId(id=job_id)
    
    try:
        response = await stub.GetJobStatus(request)
        print(f"Job Status for {job_id}:")
        print(f"  State: {response.state}")
        print(f"  Message: {response.message}")
        print(f"  Created: {time.ctime(response.created_at / 1000)}")
        print(f"  Updated: {time.ctime(response.updated_at / 1000)}")
        print(f"  Params: {dict(response.params)}")
    except grpc.RpcError as e:
        print(f"✗ Error: {e.details()}")


async def push_logs(stub, job_id: str, log_file: str):
    """Push logs from file (CLIENT STREAMING)"""
    async def log_generator():
        """Generate log lines from file"""
        try:
            with open(log_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Determine log level
                    level = "INFO"
                    if "ERROR" in line.upper():
                        level = "ERROR"
                    elif "WARN" in line.upper():
                        level = "WARN"
                    elif "DEBUG" in line.upper():
                        level = "DEBUG"
                    
                    yield job_orchestrator_pb2.LogLine(
                        job_id=job_id,
                        line=line,
                        timestamp_ms=int(time.time() * 1000),
                        level=level
                    )
                    
                    # Small delay to simulate streaming
                    await asyncio.sleep(0.1)
        except FileNotFoundError:
            print(f"✗ Error: File '{log_file}' not found")
            return
    
    try:
        response = await stub.PushLogs(log_generator())
        print(f"✓ Logs pushed successfully!")
        print(f"  Job ID: {response.job_id}")
        print(f"  Total lines: {response.total_lines}")
        print(f"  Error lines: {response.error_lines}")
        print(f"  Warning lines: {response.warn_lines}")
        print(f"  Summary: {response.message}")
    except grpc.RpcError as e:
        print(f"✗ Error: {e.details()}")


async def watch_job(stub, job_id: str):
    """Watch job updates (SERVER STREAMING)"""
    request = job_orchestrator_pb2.JobId(id=job_id)
    
    print(f"Watching job {job_id}... (Press Ctrl+C to stop)")
    print("-" * 80)
    
    try:
        async for update in stub.WatchJob(request):
            timestamp = time.ctime(update.timestamp_ms / 1000)
            print(f"[{timestamp}] {update.state} ({update.progress_percent}%): {update.detail}")
            
            # Stop if job reached terminal state
            if update.state in ['COMPLETED', 'FAILED']:
                print("-" * 80)
                print(f"Job finished with state: {update.state}")
                break
    except grpc.RpcError as e:
        print(f"✗ Error: {e.details()}")
    except KeyboardInterrupt:
        print("\n✓ Stopped watching")


async def interactive_shell(stub, job_id: str):
    """Interactive session (BIDIRECTIONAL STREAMING)"""
    print(f"Interactive session for job {job_id}")
    print("Commands: PAUSE, RESUME, CANCEL, SET_LOG_LEVEL <level>, GET_STATUS, quit")
    print("-" * 80)
    
    # Queue for sending messages
    send_queue = asyncio.Queue()
    
    async def send_messages():
        """Send control messages to server"""
        while True:
            msg = await send_queue.get()
            if msg is None:
                break
            yield msg
    
    async def receive_messages(response_stream):
        """Receive session events from server"""
        try:
            async for event in response_stream:
                timestamp = time.ctime(event.timestamp_ms / 1000)
                print(f"[{timestamp}] [{event.event_type}] {event.payload}")
        except grpc.RpcError as e:
            print(f"✗ Connection error: {e.details()}")
    
    async def read_input():
        """Read user input and send commands"""
        loop = asyncio.get_event_loop()
        
        while True:
            try:
                # Read input in executor to not block
                line = await loop.run_in_executor(None, input, "> ")
                line = line.strip()
                
                if not line:
                    continue
                
                if line.lower() == 'quit':
                    await send_queue.put(None)
                    break
                
                # Parse command
                parts = line.split(maxsplit=1)
                command = parts[0].upper()
                arg = parts[1] if len(parts) > 1 else ""
                
                # Send control message
                msg = job_orchestrator_pb2.ControlMessage(
                    job_id=job_id,
                    command=command,
                    arg=arg
                )
                await send_queue.put(msg)
            
            except EOFError:
                await send_queue.put(None)
                break
    
    try:
        # Start bidirectional stream
        response_stream = stub.InteractiveSession(send_messages())
        
        # Run receiver and input reader concurrently
        await asyncio.gather(
            receive_messages(response_stream),
            read_input()
        )
    
    except KeyboardInterrupt:
        print("\n✓ Session ended")
    
    print("-" * 80)
    print("Session closed")


async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='Job Orchestrator gRPC Client')
    parser.add_argument('--server', default='localhost:50055', help='Server address')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Submit command
    submit_parser = subparsers.add_parser('submit', help='Submit a new job')
    submit_parser.add_argument('--name', required=True, help='Job name')
    submit_parser.add_argument('--param', action='append', help='Job parameters (key=value)', default=[])
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Get job status')
    status_parser.add_argument('--job-id', required=True, help='Job ID')
    
    # Push logs command
    logs_parser = subparsers.add_parser('push-logs', help='Push logs from file')
    logs_parser.add_argument('--job-id', required=True, help='Job ID')
    logs_parser.add_argument('file', help='Log file path')
    
    # Watch command
    watch_parser = subparsers.add_parser('watch', help='Watch job updates')
    watch_parser.add_argument('--job-id', required=True, help='Job ID')
    
    # Shell command
    shell_parser = subparsers.add_parser('shell', help='Interactive shell')
    shell_parser.add_argument('--job-id', required=True, help='Job ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Parse params
    params = {}
    if args.command == 'submit':
        for param in args.param:
            if '=' in param:
                key, value = param.split('=', 1)
                params[key] = value
    
    # Connect to server
    async with grpc.aio.insecure_channel(args.server) as channel:
        stub = job_orchestrator_pb2_grpc.JobOrchestratorStub(channel)
        
        # Execute command
        if args.command == 'submit':
            await submit_job(stub, args.name, params)
        
        elif args.command == 'status':
            await get_status(stub, args.job_id)
        
        elif args.command == 'push-logs':
            await push_logs(stub, args.job_id, args.file)
        
        elif args.command == 'watch':
            await watch_job(stub, args.job_id)
        
        elif args.command == 'shell':
            await interactive_shell(stub, args.job_id)


if __name__ == '__main__':
    asyncio.run(main())
