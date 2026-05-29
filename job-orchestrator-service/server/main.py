"""gRPC server main entry point"""
import asyncio
import logging
import os

import grpc
from grpc_reflection.v1alpha import reflection

from generated import job_orchestrator_pb2, job_orchestrator_pb2_grpc
from .service_impl import JobOrchestratorServicer
from .state_store import StateStore

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - [%(threadName)s %(thread)d] - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def serve():
    """Start the gRPC server"""
    # Create state store
    state_store = StateStore()
    
    # Create server with compression support (negotiated with client)
    # Don't hardcode compression algorithm - let it be negotiated based on client's grpc-accept-encoding header
    server = grpc.aio.server()
    
    # Add service
    servicer = JobOrchestratorServicer(state_store)
    job_orchestrator_pb2_grpc.add_JobOrchestratorServicer_to_server(servicer, server)
    
    # Enable reflection
    SERVICE_NAMES = (
        job_orchestrator_pb2.DESCRIPTOR.services_by_name['JobOrchestrator'].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)
    
    # Bind to configured host and port so the Linux service can be adjusted without code changes.
    host = os.getenv('JOB_ORCHESTRATOR_HOST', '0.0.0.0')
    port = os.getenv('JOB_ORCHESTRATOR_PORT', '50055')
    listen_addr = f'{host}:{port}'
    server.add_insecure_port(listen_addr)
    
    logger.info(f"Starting Job Orchestrator gRPC server on {listen_addr}")
    await server.start()
    
    # Setup graceful shutdown
    async def shutdown():
        logger.info("Shutting down server...")
        await server.stop(5)
        
        # Cancel background tasks
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("Server stopped")
    
    # Wait for termination
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        await shutdown()


def main():
    """Main entry point"""
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        logger.info("Server interrupted")


if __name__ == '__main__':
    main()
