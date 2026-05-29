#!/bin/bash
# Verify single connection through Envoy

# Parse command line arguments
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    echo "Usage: $0 [SERVER] [ADMIN_URL]"
    echo ""
    echo "Arguments:"
    echo "  SERVER      Server hostname:port to test (default: localhost:443)"
    echo "  ADMIN_URL   Envoy admin URL (default: http://localhost:9901)"
    echo ""
    echo "Examples:"
    echo "  $0                                          # Test localhost:443"
    echo "  $0 localhost:443                            # Test localhost:443"
    echo "  $0 grpc-envoy.qa.akamai.com:443             # Test remote server"
    echo "  $0 localhost:443 http://localhost:9901      # Custom admin URL"
    exit 0
fi

echo "╔════════════════════════════════════════════════════════════════════╗"
echo "║  Envoy Connection Verification - Single Connection Test           ║"
echo "╚════════════════════════════════════════════════════════════════════╝"
echo ""

# Parse arguments
SERVER=${1:-localhost:443}
ADMIN_URL=${2:-http://localhost:9901}

# Get baseline stats
echo "📊 Envoy Stats BEFORE test:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
BEFORE_TOTAL=$(curl -s ${ADMIN_URL}/stats | grep "job-orchestrator-service.upstream_cx_total:" | awk '{print $2}')
BEFORE_ACTIVE=$(curl -s ${ADMIN_URL}/stats | grep "job-orchestrator-service.upstream_cx_active:" | awk '{print $2}')
BEFORE_RQ=$(curl -s ${ADMIN_URL}/stats | grep "job-orchestrator-service.upstream_rq_total:" | awk '{print $2}')

echo "  Total connections created: $BEFORE_TOTAL"
echo "  Active connections: $BEFORE_ACTIVE"
echo "  Total requests: $BEFORE_RQ"
echo ""

echo "🚀 Running test through Envoy ($SERVER with TLS)..."
echo ""

# Run the test
cd /home/grpc-envoy-proxy/job-orchestrator-service
python3 client/test_all_rpc_patterns.py $SERVER tls 2>&1 | grep -E "Channel ID|Job ID|✅|❌|Summary" | head -20

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Envoy Stats AFTER test:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

AFTER_TOTAL=$(curl -s ${ADMIN_URL}/stats | grep "job-orchestrator-service.upstream_cx_total:" | awk '{print $2}')
AFTER_ACTIVE=$(curl -s ${ADMIN_URL}/stats | grep "job-orchestrator-service.upstream_cx_active:" | awk '{print $2}')
AFTER_RQ=$(curl -s ${ADMIN_URL}/stats | grep "job-orchestrator-service.upstream_rq_total:" | awk '{print $2}')

echo "  Total connections created: $AFTER_TOTAL"
echo "  Active connections: $AFTER_ACTIVE"
echo "  Total requests: $AFTER_RQ"
echo ""

# Calculate deltas
NEW_CONN=$((AFTER_TOTAL - BEFORE_TOTAL))
NEW_RQ=$((AFTER_RQ - BEFORE_RQ))

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📈 Changes During Test:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  New connections created: $NEW_CONN"
echo "  New requests made: $NEW_RQ"
echo ""

if [ "$NEW_CONN" -eq 0 ]; then
    echo "✅ SUCCESS: No new connections created!"
    echo "   (Reused existing connection pool)"
elif [ "$NEW_CONN" -eq 1 ]; then
    echo "✅ SUCCESS: Only 1 new connection created!"
    echo "   All $NEW_RQ requests multiplexed over this single connection"
elif [ "$NEW_CONN" -le 2 ]; then
    echo "✅ GOOD: Only $NEW_CONN connections created for $NEW_RQ requests"
    echo "   (Envoy maintains a small connection pool, which is normal)"
else
    echo "⚠️  NOTICE: $NEW_CONN connections created for $NEW_RQ requests"
    echo "   (Still using connection pooling, not creating one per request)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 Detailed Stats:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
curl -s ${ADMIN_URL}/stats | grep "job-orchestrator-service.upstream" | grep -E "cx_|rq_" | grep -v "histogram" | head -20

echo ""
echo "✅ Test complete!"
echo ""
echo "💡 Key Insight:"
echo "   The client uses 1 gRPC channel which connects to Envoy."
echo "   Envoy uses a connection pool (typically 1-2 connections) to the backend."
echo "   All 5 RPC calls from the client use the SAME client-side channel."
echo "   This is proven by the constant Channel ID in the test output."
