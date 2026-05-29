"""Quick test for custom steps parameter"""
import asyncio
import grpc
from generated import job_orchestrator_pb2, job_orchestrator_pb2_grpc

async def test():
    async with grpc.aio.insecure_channel('localhost:50055') as channel:
        stub = job_orchestrator_pb2_grpc.JobOrchestratorStub(channel)
        
        # Test 1: Submit job with 3 steps
        print("Test 1: Submitting job with 3 steps...")
        response = await stub.SubmitJob(
            job_orchestrator_pb2.JobSpec(
                name="test-3-steps",
                params={"steps": "3"}
            )
        )
        job_id_1 = response.job_id
        print(f"  Job ID: {job_id_1}")
        
        # Test 2: Submit job with 20 steps
        print("\nTest 2: Submitting job with 20 steps...")
        response = await stub.SubmitJob(
            job_orchestrator_pb2.JobSpec(
                name="test-20-steps",
                params={"steps": "20", "env": "qa"}
            )
        )
        job_id_2 = response.job_id
        print(f"  Job ID: {job_id_2}")
        
        # Test 3: Default (no steps param)
        print("\nTest 3: Submitting job with default steps...")
        response = await stub.SubmitJob(
            job_orchestrator_pb2.JobSpec(
                name="test-default",
                params={}
            )
        )
        job_id_3 = response.job_id
        print(f"  Job ID: {job_id_3}")
        
        # Wait a bit for jobs to start
        await asyncio.sleep(3)
        
        # Check status of all jobs
        for job_id, expected in [(job_id_1, "3"), (job_id_2, "20"), (job_id_3, "default")]:
            status = await stub.GetJobStatus(job_orchestrator_pb2.JobId(id=job_id))
            print(f"\nJob {job_id} ({expected}):")
            print(f"  State: {status.state}")
            print(f"  Message: {status.message}")
            print(f"  Params: {dict(status.params)}")

if __name__ == '__main__':
    try:
        asyncio.run(test())
    except grpc.RpcError as e:
        print(f"Error: {e.details()}")
        print("Make sure the server is running: make server")
