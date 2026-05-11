#!/bin/bash
# E2E test chatbot RAG — 5 FAQ queries + 1 negative (not in KB)
# Usage: bash scripts/test_chatbot_rag.sh

set -e

GATEWAY_SECRET="gw-prod-wnMbXWEHc49KXVjhae4IGU7TZfoj4HHEDTOtzYvE"
USER_ID="08fc117f-5a57-48a0-ac99-5b2c44e6ae71"
USER_EMAIL="testdriver@parksmart.com"

queries=(
  "Chính sách hủy booking có phí không?"
  "Giờ mở cửa bãi Vincom mấy giờ?"
  "Xe container có được vào bãi không?"
  "Bãi Aeon có hỗ trợ xe điện không?"
  "Làm sao đăng ký tài khoản mới?"
  "Giá bitcoin hôm nay bao nhiêu?"
)

echo "=========================================="
echo "Testing Chatbot RAG E2E"
echo "=========================================="

pass=0
fail=0
for q in "${queries[@]}"; do
  echo ""
  echo "Q: $q"
  resp=$(docker exec gateway-service-go wget -qO- --timeout=45 \
    --header="X-Gateway-Secret: $GATEWAY_SECRET" \
    --header="X-User-ID: $USER_ID" \
    --header="X-User-Email: $USER_EMAIL" \
    --header="Content-Type: application/json" \
    --post-data="{\"message\":\"$q\"}" \
    http://chatbot-service-fastapi:8008/chatbot/chat/ 2>&1)

  intent=$(echo "$resp" | python -c "import json,sys; print(json.loads(sys.stdin.read()).get('intent', '?'))" 2>/dev/null)
  response_text=$(echo "$resp" | python -c "import json,sys; print(json.loads(sys.stdin.read()).get('response', ''))" 2>/dev/null)

  echo "  Intent: $intent"
  echo "  Response (200 chars): ${response_text:0:200}"

  if [ "$intent" = "faq" ]; then
    pass=$((pass + 1))
    echo "  ✓ classified as faq"
  else
    fail=$((fail + 1))
    echo "  ⚠️  classified as: $intent (expected faq)"
  fi
done

echo ""
echo "=========================================="
echo "SUMMARY: $pass pass / $((pass+fail)) total"
echo "=========================================="
