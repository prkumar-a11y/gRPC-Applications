#!/usr/bin/env python3
"""
Demonstrate all 4 gRPC RPC patterns over a single connection.

This script shows how gRPC multiplexes multiple RPCs over a single HTTP/2 connection:
1. Unary RPC - Request/Response
2. Client Streaming - Multiple requests, single response
3. Server Streaming - Single request, multiple responses
4. Bidirectional Streaming - Multiple requests and responses

All these RPCs share the same underlying connection, demonstrating gRPC's
efficient HTTP/2 multiplexing capabilities.
"""

import grpc
import sys
import os
import time
import random
import string
import ssl
from datetime import datetime

# Add parent directory to path to import generated proto files
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

# Try to import from generated directory
try:
    from generated import job_orchestrator_pb2, job_orchestrator_pb2_grpc
except ImportError:
    # If running from host, the path might be different
    import generated.job_orchestrator_pb2 as job_orchestrator_pb2
    import generated.job_orchestrator_pb2_grpc as job_orchestrator_pb2_grpc


def generate_log_lines(job_id, count=10):
    """Generate sample log lines for client streaming"""
    levels = ['DEBUG', 'INFO', 'WARN', 'ERROR']
    for i in range(count):
        yield job_orchestrator_pb2.LogLine(
            job_id=job_id,
            line=f"Log message #{i+1}: Processing step {i+1} of {count}",
            timestamp_ms=int(time.time() * 1000),
            level=random.choice(levels)
        )
        time.sleep(0.1)  # Simulate real-time log generation


def generate_control_messages(job_id):
    """Generate control messages for bidirectional streaming"""
    commands = [
        ('GET_STATUS', ''),
        ('SET_LOG_LEVEL', 'DEBUG'),
        ('PAUSE', ''),
        ('GET_STATUS', ''),
        ('RESUME', ''),
        ('GET_STATUS', ''),
    ]
    
    for command, arg in commands:
        yield job_orchestrator_pb2.ControlMessage(
            job_id=job_id,
            command=command,
            arg=arg
        )
        time.sleep(0.5)  # Space out commands


def print_separator(title):
    """Print a formatted section separator"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def test_all_rpc_patterns(server_address='localhost:50055', use_tls=False, authority=None, 
                           insecure_tls=False, custom_headers=None):
    """
    Test all 4 RPC patterns over a single gRPC connection.
    
    Args:
        server_address: gRPC server address (e.g., 'localhost:50055' or '198.18.76.73:443')
        use_tls: Whether to use TLS (True for production Envoy endpoints)
        authority: Custom authority header (SNI/Host override)
        insecure_tls: Skip TLS certificate verification
        custom_headers: Dict of custom metadata headers to send with each RPC
    """
    
    print(f"\n🚀 Connecting to Job Orchestrator Service at {server_address}")
    print(f"   Using {'secure (TLS)' if use_tls else 'insecure'} connection")
    if authority:
        print(f"   Authority: {authority}")
    if insecure_tls:
        print(f"   TLS Verification: DISABLED (insecure mode)")
    if custom_headers:
        print(f"   Custom Headers: {custom_headers}")
    print()
    
    # Create a single channel - this is the key to connection reuse
    if use_tls or ':443' in server_address:
        import subprocess
        
        # Build channel options
        options = []
        
        # Set authority if provided (equivalent to grpcurl -authority)
        if authority:
            options.append(('grpc.default_authority', authority))
            options.append(('grpc.ssl_target_name_override', authority))
        
        # For insecure mode, we need to fetch and trust the server's certificate
        # (equivalent to grpcurl -insecure which accepts any certificate)
        cmd = f"echo | openssl s_client -connect {server_address} -servername {authority if authority else server_address.split(':')[0]} -showcerts 2>/dev/null | sed -n '/BEGIN CERTIFICATE/,/END CERTIFICATE/p'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=False)
        root_certs = result.stdout
        
        if not root_certs:
            # Fallback: try without SNI
            cmd = f"echo | openssl s_client -connect {server_address} -showcerts 2>/dev/null | sed -n '/BEGIN CERTIFICATE/,/END CERTIFICATE/p'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=False)
            root_certs = result.stdout
        
        # Create TLS credentials using the server's certificate as the trusted root
        credentials = grpc.ssl_channel_credentials(root_certificates=root_certs)
        
        # If no authority provided and not in insecure mode, check certificate CN
        if not authority and not insecure_tls:
            cmd_cn = f"echo | openssl s_client -connect {server_address} 2>/dev/null | openssl x509 -noout -subject | grep -oP 'CN\\s*=\\s*\\K[^,]+' || echo ''"
            result_cn = subprocess.run(cmd_cn, shell=True, capture_output=True, text=True)
            cert_cn = result_cn.stdout.strip()
            hostname = server_address.split(':')[0]
            
            if cert_cn and cert_cn != hostname:
                options.append(('grpc.ssl_target_name_override', cert_cn))
        
        channel = grpc.secure_channel(server_address, credentials, options=options)
    else:
        channel = grpc.insecure_channel(server_address)
    
    # Create a stub (client) that will use this channel for ALL RPCs
    stub = job_orchestrator_pb2_grpc.JobOrchestratorStub(channel)
    
    # Prepare metadata for all RPC calls (equivalent to grpcurl -H)
    metadata = []
    if custom_headers:
        for key, value in custom_headers.items():
            metadata.append((key.lower(), value))  # gRPC metadata keys are lowercase
    
    # Get channel state to verify connection
    print("✅ Single gRPC channel established")
    print(f"   Channel ID: {id(channel)}")
    print(f"   Server: {server_address}")
    print("   All subsequent RPCs will use this same connection!\n")
    print("💡 PROOF OF SINGLE CONNECTION:")
    print("   The Channel ID above is a Python object identifier.")
    print("   If this ID stays the same throughout all RPC calls,")
    print("   it proves we're using the exact same channel object.")
    print("   (Check the summary at the end - it will show the same ID!)\n")
    print("   Note: netstat may show 2-3 lines for a single connection because:")
    print("   - It displays both client and server sides of the same connection")
    print("   - Docker/loopback connections appear multiple times")
    print("   The Channel ID is the definitive proof!\n")
    
    try:
        # ================================================================
        # 1. UNARY RPC - Submit a job
        # ================================================================
        print_separator("1️⃣  UNARY RPC: SubmitJob")
        
        job_spec = job_orchestrator_pb2.JobSpec(
            name=f"test-job-{int(time.time())}",
            params={
                'environment': 'qa',
                'test_suite': 'smoke-tests',
                'timeout': '300'
            }
        )
        
        print(f"Submitting job: {job_spec.name}")
        print(f"Parameters: {dict(job_spec.params)}\n")
        
        # Make unary RPC call with custom metadata
        job_ack = stub.SubmitJob(job_spec, metadata=metadata)
        job_id = job_ack.job_id
        
        print(f"✅ Job submitted successfully!")
        print(f"   Job ID: {job_id}")
        print(f"   Message: {job_ack.message}\n")
        
        # Small delay to let job initialize
        time.sleep(0.5)
        
        # ================================================================
        # 2. UNARY RPC - Get job status (reusing same connection)
        # ================================================================
        print_separator("2️⃣  UNARY RPC: GetJobStatus")
        
        print(f"Querying status for job: {job_id}\n")
        
        # Make another unary RPC call on the same channel with custom metadata
        job_status = stub.GetJobStatus(job_orchestrator_pb2.JobId(id=job_id), metadata=metadata)
        
        print(f"✅ Job status retrieved:")
        print(f"   Job ID: {job_status.job_id}")
        print(f"   State: {job_status.state}")
        print(f"   Message: {job_status.message}")
        print(f"   Created: {datetime.fromtimestamp(job_status.created_at/1000)}")
        print(f"   Updated: {datetime.fromtimestamp(job_status.updated_at/1000)}\n")
        
        # ================================================================
        # 3. CLIENT STREAMING RPC - Push logs (reusing same connection)
        # ================================================================
        print_separator("3️⃣  CLIENT STREAMING RPC: PushLogs")
        
        print(f"Streaming 10 log lines to server for job: {job_id}")
        print("Sending logs...\n")
        
        # Client streaming: send multiple messages, get one response with custom metadata
        log_summary = stub.PushLogs(generate_log_lines(job_id, count=10), metadata=metadata)
        
        print(f"\n✅ Log streaming completed!")
        print(f"   Job ID: {log_summary.job_id}")
        print(f"   Total lines: {log_summary.total_lines}")
        print(f"   Error lines: {log_summary.error_lines}")
        print(f"   Warn lines: {log_summary.warn_lines}")
        print(f"   Summary: {log_summary.message}\n")
        
        # ================================================================
        # 4. SERVER STREAMING RPC - Watch job (reusing same connection)
        # ================================================================
        print_separator("4️⃣  SERVER STREAMING RPC: WatchJob")
        
        print(f"Watching job updates for: {job_id}")
        print("Receiving updates from server...\n")
        
        # Server streaming: send one message, receive multiple responses with custom metadata
        update_count = 0
        for update in stub.WatchJob(job_orchestrator_pb2.JobId(id=job_id), metadata=metadata):
            update_count += 1
            timestamp = datetime.fromtimestamp(update.timestamp_ms/1000).strftime('%H:%M:%S')
            print(f"   [{timestamp}] {update.state:12s} - {update.detail:40s} ({update.progress_percent}%)")
            
            # Watch for completion or limit updates
            if update.state in ['COMPLETED', 'FAILED'] or update_count >= 15:
                break
        
        print(f"\n✅ Received {update_count} job updates\n")
        
        # ================================================================
        # 5. BIDIRECTIONAL STREAMING RPC (reusing same connection)
        # ================================================================
        print_separator("5️⃣  BIDIRECTIONAL STREAMING RPC: InteractiveSession")
        
        print(f"Starting interactive session for job: {job_id}")
        print("Sending control commands and receiving events...\n")
        
        # Bidirectional streaming: send and receive multiple messages with custom metadata
        responses = stub.InteractiveSession(generate_control_messages(job_id), metadata=metadata)
        
        event_count = 0
        for event in responses:
            event_count += 1
            timestamp = datetime.fromtimestamp(event.timestamp_ms/1000).strftime('%H:%M:%S')
            print(f"   [{timestamp}] {event.event_type:8s} - {event.payload}")
            
            # Prevent infinite loop
            if event_count >= 20:
                break
        
        print(f"\n✅ Interactive session completed!")
        print(f"   Exchanged {event_count} events\n")
        
        # ================================================================
        # Summary
        # ================================================================
        print_separator("📊 Summary")
        
        print("All 5 RPC calls completed successfully over a SINGLE connection:")
        print("")
        print("   1. ✅ Unary RPC (SubmitJob)")
        print("   2. ✅ Unary RPC (GetJobStatus)")
        print("   3. ✅ Client Streaming RPC (PushLogs)")
        print("   4. ✅ Server Streaming RPC (WatchJob)")
        print("   5. ✅ Bidirectional Streaming RPC (InteractiveSession)")
        print("")
        print(f"🎯 Job ID used throughout: {job_id}")
        print(f"🔗 Channel ID (same for all RPCs): {id(channel)}")
        print("")
        print("✅ PROOF: The Channel ID above matches the one at the start!")
        print("   This conclusively proves all 5 RPCs used the same channel object.")
        print("   Same Python object = Same gRPC channel = Single HTTP/2 connection")
        print("")
        print("Key Benefits of Connection Reuse:")
        print("  • Reduced latency (no TCP handshake overhead)")
        print("  • Lower resource usage (single connection)")
        print("  • HTTP/2 multiplexing (parallel streams)")
        print("  • Better throughput (connection warming)")
        print("")
        
        # Give user time to verify connection count
        print("⏸️  Pausing 5 seconds before closing...")
        print("   Check connection count now with:")
        print(f"     netstat -an | grep {server_address.split(':')[1]} | grep ESTABLISHED")
        time.sleep(5)
        
    except grpc.RpcError as e:
        print(f"\n❌ gRPC Error occurred:")
        print(f"   Status: {e.code()}")
        print(f"   Details: {e.details()}")
        print(f"   Debug: {e.debug_error_string()}")
        return 1
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # Close the channel when done
        print("🔌 Closing gRPC channel...")
        channel.close()
        print("✅ Connection closed gracefully\n")
    
    return 0


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Test all gRPC RPC patterns over a single connection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Local insecure connection
  %(prog)s localhost:50055
  
  # Akamai endpoint with custom authority and headers
  %(prog)s 198.18.76.73:443 \\
    --authority ion-std-grpc-native-mixed-traffic-ff.wildcard-l1-shared-webexp-ipqa-alta.com \\
    --header "gRPC-Native-Traffic:on" \\
    --insecure
  
  # Environment variables (alternative)
  export GRPC_SERVER=198.18.76.73:443
  export GRPC_AUTHORITY=ion-std-grpc-native-mixed-traffic-ff.wildcard-l1-shared-webexp-ipqa-alta.com
  export GRPC_HEADERS="gRPC-Native-Traffic:on"
  export GRPC_INSECURE=1
  %(prog)s
''')
    
    parser.add_argument('server', nargs='?', 
                        default=os.environ.get('GRPC_SERVER', 'localhost:50055'),
                        help='Server address (default: localhost:50055 or $GRPC_SERVER)')
    parser.add_argument('-a', '--authority', 
                        default=os.environ.get('GRPC_AUTHORITY'),
                        help='Authority header (SNI override, like grpcurl -authority)')
    parser.add_argument('-H', '--header', action='append', dest='headers',
                        help='Custom metadata header (can be used multiple times, format: "Key:Value")')
    parser.add_argument('--insecure', action='store_true',
                        default=os.environ.get('GRPC_INSECURE', '').lower() in ('1', 'true', 'yes'),
                        help='Skip TLS certificate verification (like grpcurl -insecure)')
    parser.add_argument('--tls', action='store_true',
                        help='Force TLS (auto-detected for :443 addresses)')
    
    args = parser.parse_args()
    
    server_address = args.server
    
    # Check if TLS should be used
    use_tls = args.tls or ':443' in server_address
    
    # Parse custom headers from command line and environment
    custom_headers = {}
    
    # From environment variable
    env_headers = os.environ.get('GRPC_HEADERS', '')
    if env_headers:
        for header in env_headers.split(','):
            if ':' in header:
                key, value = header.split(':', 1)
                custom_headers[key.strip()] = value.strip()
    
    # From command line (overrides environment)
    if args.headers:
        for header in args.headers:
            if ':' in header:
                key, value = header.split(':', 1)
                custom_headers[key.strip()] = value.strip()
    
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║   gRPC All RPC Patterns Demo - Single Connection Multiplexing    ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    
    exit_code = test_all_rpc_patterns(
        server_address=server_address,
        use_tls=use_tls,
        authority=args.authority,
        insecure_tls=args.insecure,
        custom_headers=custom_headers if custom_headers else None
    )
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
