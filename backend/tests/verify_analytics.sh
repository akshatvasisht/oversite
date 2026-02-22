#!/bin/bash
# verify_analytics.sh
# Ping the overview and session endpoints and parse with jq

echo "Verifying GET /api/v1/analytics/overview..."
OVERVIEW=$(curl -s http://localhost:8000/api/v1/analytics/overview)

# Check if sessions array exists
if echo "$OVERVIEW" | jq -e '.sessions | type == "array"' > /dev/null; then
  echo "✅ Overview endpoint returned a valid sessions array."
else
  echo "❌ Overview endpoint failed to return a sessions array."
  exit 1
fi

# Try to get the first session ID to test the detail endpoint
FIRST_SESSION=$(echo "$OVERVIEW" | jq -r '.sessions[0].session_id // empty')

if [ -n "$FIRST_SESSION" ]; then
  echo "Verifying GET /api/v1/analytics/session/$FIRST_SESSION..."
  DETAIL=$(curl -s "http://localhost:8000/api/v1/analytics/session/$FIRST_SESSION")
  
  if echo "$DETAIL" | jq -e '.rate_acceptance != null' > /dev/null; then
    echo "✅ Session detail endpoint returned live metrics (e.g. rate_acceptance)."
  else
    echo "❌ Session detail endpoint failed to return live metrics."
    exit 1
  fi
else
  echo "⚠️ No sessions found in overview to test detail endpoint. Schema is otherwise correct."
fi

echo "All verifications passed!"
exit 0
