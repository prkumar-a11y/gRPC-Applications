#!/usr/bin/env python3
"""
Test script with insecure TLS (skips certificate verification)
"""

# Set environment variable BEFORE importing grpc
import os
os.environ['GRPC_DEFAULT_SSL_ROOTS_FILE_PATH'] = '/dev/null'

import grpc
import sys
import time

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from generated import job_orchestrator_pb2, job_orchestrator_pb2_grpc

def test_insecure_tls(server_address):
    """Test with insecure TLS"""
    print(f"Connecting to {server_address} with insecure TLS...")
    
    # Use SSL channel with no root certificates = skip verification
    credentials = grpc.ssl_channel_credentials()
    options = [
        ('grpc.ssl_target_name_override', 'ion-std-grpc-native-mixed-traffic-ff.wildcard-l1-shared-webexp-ipqa-alta.com'),
    ]
    
    channel = grpc.secure_channel(server_address, credentials, options=options)
    stub = job_orchestrator_pb2_grpc.JobOrchestratorStub(channel)
    
    try:
        job_spec = job_orchestrator_pb2.JobSpec(
            name=f"test-job-{int(time.time())}",
            params={'test': 'insecure'}
        )
        
        job_ack = stub.SubmitJob(job_spec)
        print(f"✅ Success! Job ID: {job_ack.job_id}")
        return 0
    except grpc.RpcError as e:
        print(f"❌ Error: {e.code()} - {e.details()}")
        return 1
    finally:
        channel.close()

if __name__ == '__main__':
    server = sys.argv[1] if len(sys.argv) > 1 else 'localhost:50055'
    sys.exit(test_insecure_tls(server))
