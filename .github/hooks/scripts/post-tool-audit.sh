#!/bin/bash
# ============================================================================
# POST-TOOL AUDIT HOOK
# Ghi nhật ký audit sau khi AI hoàn thành thực thi công cụ
# ============================================================================

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.toolName // "unknown"')
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
AUDIT_DIR=".github/hooks/audit-logs"

# Tạo thư mục audit nếu chưa có
mkdir -p "$AUDIT_DIR"

# Ghi log
AUDIT_FILE="$AUDIT_DIR/audit-$(date -u +%Y%m%d).jsonl"
AGENT=$(echo "$INPUT" | jq -r '.agentName // "unknown"')
STATUS=$(echo "$INPUT" | jq -r '.toolResult.status // "completed"')

# Tạo entry audit
AUDIT_ENTRY=$(jq -n \
  --arg timestamp "$TIMESTAMP" \
  --arg tool "$TOOL_NAME" \
  --arg agent "$AGENT" \
  --arg status "$STATUS" \
  '{
    timestamp: $timestamp,
    tool: $tool,
    agent: $agent,
    status: $status,
    action: "post_tool_audit"
  }')

echo "$AUDIT_ENTRY" >> "$AUDIT_FILE"

# Luôn cho phép (post-tool không chặn)
echo '{"permissionDecision":"allow"}'
exit 0
