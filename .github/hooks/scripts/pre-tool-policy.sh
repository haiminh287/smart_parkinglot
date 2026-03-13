#!/bin/bash
# ============================================================================
# PRE-TOOL POLICY HOOK
# Kiểm toán bảo mật trước khi cho phép AI chạy bất kỳ công cụ nào
# ============================================================================

# Nắm bắt tải trọng JSON từ Copilot
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.toolName // empty')
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# ============================================================================
# RULE 1: Kiểm tra công cụ bash - chặn lệnh phá hoại
# ============================================================================
if [ "$TOOL_NAME" = "bash" ] || [ "$TOOL_NAME" = "terminal" ]; then
    COMMAND=$(echo "$INPUT" | jq -r '.toolArgs.command // empty')
    
    # Pattern nguy hiểm Level 1: CRITICAL - Xóa toàn bộ hệ thống
    if echo "$COMMAND" | grep -Eq 'rm\s+-rf\s+/|rm\s+-rf\s+\.\*|rm\s+-rf\s+~|rmdir\s+/|mkfs\.|dd\s+if='; then
        echo "{\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"[CRITICAL] Lệnh bị từ chối: Phát hiện lệnh xóa hệ thống hoặc format ổ đĩa. Timestamp: $TIMESTAMP\"}"
        exit 0
    fi
    
    # Pattern nguy hiểm Level 2: HIGH - SQL phá hoại
    if echo "$COMMAND" | grep -Eiq 'DROP\s+TABLE|DROP\s+DATABASE|TRUNCATE\s+TABLE|DELETE\s+FROM\s+\w+\s*;|ALTER\s+TABLE.*DROP'; then
        echo "{\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"[HIGH] Lệnh bị từ chối: Phát hiện SQL phá hoại (DROP/TRUNCATE/DELETE ALL). Timestamp: $TIMESTAMP\"}"
        exit 0
    fi
    
    # Pattern nguy hiểm Level 3: HIGH - Network exploits
    if echo "$COMMAND" | grep -Eq 'curl.*\|\s*sh|wget.*\|\s*sh|curl.*\|\s*bash|wget.*\|\s*bash'; then
        echo "{\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"[HIGH] Lệnh bị từ chối: Phát hiện tải và thực thi script từ remote. Timestamp: $TIMESTAMP\"}"
        exit 0
    fi
    
    # Pattern nguy hiểm Level 4: MEDIUM - Credential exposure
    if echo "$COMMAND" | grep -Eq 'cat\s+.*\.env\b|cat\s+.*credentials|cat\s+.*\.pem|cat\s+.*id_rsa'; then
        echo "{\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"[MEDIUM] Lệnh bị từ chối: Phát hiện truy cập file chứa credentials. Timestamp: $TIMESTAMP\"}"
        exit 0
    fi
    
    # Pattern nguy hiểm Level 5: MEDIUM - Permission escalation
    if echo "$COMMAND" | grep -Eq 'chmod\s+777|chmod\s+-R\s+777|chown\s+root|sudo\s+su'; then
        echo "{\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"[MEDIUM] Lệnh bị từ chối: Phát hiện thay đổi quyền nguy hiểm. Timestamp: $TIMESTAMP\"}"
        exit 0
    fi
    
    # Pattern nguy hiểm Level 6: MEDIUM - Sensitive file modifications
    if echo "$COMMAND" | grep -Eq 'vim\s+/etc/|nano\s+/etc/|echo.*>>\s+/etc/|cat.*>\s+/etc/'; then
        echo "{\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"[MEDIUM] Lệnh bị từ chối: Phát hiện sửa đổi file hệ thống. Timestamp: $TIMESTAMP\"}"
        exit 0
    fi
fi

# ============================================================================
# RULE 2: Kiểm tra công cụ write/edit - chặn ghi file nhạy cảm
# ============================================================================
if [ "$TOOL_NAME" = "write" ] || [ "$TOOL_NAME" = "edit" ]; then
    FILE_PATH=$(echo "$INPUT" | jq -r '.toolArgs.filePath // .toolArgs.path // empty')
    
    # Chặn ghi vào file môi trường thật
    if echo "$FILE_PATH" | grep -Eq '\.env$|\.env\.local$|\.env\.production$'; then
        # Cho phép .env.example
        if ! echo "$FILE_PATH" | grep -Eq '\.env\.example$'; then
            echo "{\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"[HIGH] Ghi file bị từ chối: Không được tạo/sửa file .env thật. Chỉ sử dụng .env.example. Timestamp: $TIMESTAMP\"}"
            exit 0
        fi
    fi
    
    # Chặn ghi vào file SSH keys
    if echo "$FILE_PATH" | grep -Eq 'id_rsa|id_ed25519|\.pem$|\.key$'; then
        echo "{\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"[CRITICAL] Ghi file bị từ chối: Không được tạo/sửa private keys. Timestamp: $TIMESTAMP\"}"
        exit 0
    fi
fi

# ============================================================================
# ALLOW: Chấp thuận cho công cụ hoạt động
# ============================================================================
echo '{"permissionDecision":"allow"}'
exit 0
