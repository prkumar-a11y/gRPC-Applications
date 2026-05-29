#!/bin/bash
# Test script for Akamai endpoint based on working grpcurl command
#
# Original working grpcurl command:
# grpcurl --vv -insecure -d '{"name": "test"}' \
#   -proto job_orchestrator.proto \
#   -authority ion-std-grpc-native-mixed-traffic-ff.wildcard-l1-shared-webexp-ipqa-alta.com \
#   -H "gRPC-Native-Traffic:on" \
#   198.18.76.73:443 \
#   joborchestrator.JobOrchestrator/SubmitJob

# Run the Python test script with equivalent parameters
python3 test_all_rpc_patterns.py \
  198.18.76.73:443 \
  --authority ion-std-grpc-native-mixed-traffic-ff.wildcard-l1-shared-webexp-ipqa-alta.com \
  --header "gRPC-Native-Traffic:on" \
  --insecure
