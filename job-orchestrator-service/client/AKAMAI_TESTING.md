# Testing with Akamai Endpoint

This guide shows how to use the updated `test_all_rpc_patterns.py` script with the Akamai endpoint.

## Quick Start

### Option 1: Using the Helper Script
```bash
cd /home/grpc-envoy-proxy/job-orchestrator-service/client
./test_akamai.sh
```

### Option 2: Direct Python Command
```bash
cd /home/grpc-envoy-proxy/job-orchestrator-service/client
python3 test_all_rpc_patterns.py \
  198.18.76.73:443 \
  --authority ion-std-grpc-native-mixed-traffic-ff.wildcard-l1-shared-webexp-ipqa-alta.com \
  --header "gRPC-Native-Traffic:on" \
  --insecure
```

### Option 3: Using Environment Variables
```bash
export GRPC_SERVER=198.18.76.73:443
export GRPC_AUTHORITY=ion-std-grpc-native-mixed-traffic-ff.wildcard-l1-shared-webexp-ipqa-alta.com
export GRPC_HEADERS="gRPC-Native-Traffic:on"
export GRPC_INSECURE=1

python3 test_all_rpc_patterns.py
```

## Command Line Options

```
usage: test_all_rpc_patterns.py [-h] [-a AUTHORITY] [-H HEADERS] [--insecure] [--tls] [server]

Options:
  server                 Server address (default: localhost:50055 or $GRPC_SERVER)
  -a, --authority        Authority header (SNI override, like grpcurl -authority)
  -H, --header           Custom metadata header (format: "Key:Value", can be used multiple times)
  --insecure            Skip TLS certificate verification (like grpcurl -insecure)
  --tls                 Force TLS (auto-detected for :443 addresses)
```

## Comparison with grpcurl

The updated script now supports the same options as grpcurl:

| grpcurl | Python Script |
|---------|---------------|
| `grpcurl -insecure` | `--insecure` |
| `grpcurl -authority <value>` | `--authority <value>` or `-a <value>` |
| `grpcurl -H "Key:Value"` | `--header "Key:Value"` or `-H "Key:Value"` |
| `grpcurl <host:port>` | `<host:port>` positional argument |

## Multiple Custom Headers

You can add multiple custom headers:

```bash
python3 test_all_rpc_patterns.py 198.18.76.73:443 \
  --authority ion-std-grpc-native-mixed-traffic-ff.wildcard-l1-shared-webexp-ipqa-alta.com \
  -H "gRPC-Native-Traffic:on" \
  -H "Custom-Header:value" \
  -H "Another-Header:another-value" \
  --insecure
```

Or via environment variables (comma-separated):
```bash
export GRPC_HEADERS="gRPC-Native-Traffic:on,Custom-Header:value,Another-Header:another-value"
```

## Testing Local Envoy (Original Usage)

The script still works with local Envoy:

```bash
# Insecure local
python3 test_all_rpc_patterns.py localhost:50055

# Secure local with TLS
python3 test_all_rpc_patterns.py localhost:50051 --tls
```

## What Changed

The script now:
1. ✅ Supports custom authority header (SNI/Host override)
2. ✅ Supports custom metadata headers on all RPC calls
3. ✅ Supports insecure TLS mode (skip certificate verification)
4. ✅ Uses argparse for better command-line parsing
5. ✅ Supports environment variables for configuration
6. ✅ Maintains backward compatibility with local Envoy testing

All custom headers are automatically added to every RPC call (SubmitJob, GetJobStatus, PushLogs, WatchJob, InteractiveSession).
