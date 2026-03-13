# ============================================================================
# PRE-TOOL POLICY HOOK (PowerShell)
# Kiểm toán bảo mật trước khi cho phép AI chạy bất kỳ công cụ nào
# ============================================================================

$Input = $input | Out-String
try {
    $Data = $Input | ConvertFrom-Json
    $ToolName = $Data.toolName
} catch {
    Write-Output '{"permissionDecision":"allow"}'
    exit 0
}

$Timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")

# ============================================================================
# RULE 1: Kiểm tra terminal — chặn lệnh phá hoại
# ============================================================================
if ($ToolName -eq "runInTerminal" -or $ToolName -eq "bash" -or $ToolName -eq "terminal") {
    $Command = $Data.toolArgs.command

    # Level 1: CRITICAL — Xóa toàn bộ hệ thống
    if ($Command -match 'rm\s+-rf\s+/|rmdir\s+/s|del\s+/s\s+/q\s+C:\\|format\s+C:') {
        Write-Output "{`"permissionDecision`":`"deny`",`"permissionDecisionReason`":`"[CRITICAL] Lệnh bị từ chối: Phát hiện lệnh xóa hệ thống. Timestamp: $Timestamp`"}"
        exit 0
    }

    # Level 2: HIGH — SQL phá hoại
    if ($Command -match '(?i)DROP\s+TABLE|DROP\s+DATABASE|TRUNCATE\s+TABLE|DELETE\s+FROM\s+\w+\s*;') {
        Write-Output "{`"permissionDecision`":`"deny`",`"permissionDecisionReason`":`"[HIGH] Lệnh bị từ chối: Phát hiện SQL phá hoại. Timestamp: $Timestamp`"}"
        exit 0
    }

    # Level 3: HIGH — Remote code execution
    if ($Command -match 'curl.*\|\s*sh|wget.*\|\s*sh|curl.*\|\s*bash|Invoke-Expression.*Download') {
        Write-Output "{`"permissionDecision`":`"deny`",`"permissionDecisionReason`":`"[HIGH] Lệnh bị từ chối: Tải và thực thi script từ remote. Timestamp: $Timestamp`"}"
        exit 0
    }

    # Level 4: MEDIUM — Credential exposure
    if ($Command -match '(?i)cat\s+.*\.env\b|type\s+.*\.env\b|Get-Content.*\.env|cat\s+.*credentials|cat\s+.*\.pem|cat\s+.*id_rsa') {
        Write-Output "{`"permissionDecision`":`"deny`",`"permissionDecisionReason`":`"[MEDIUM] Lệnh bị từ chối: Truy cập file chứa credentials. Timestamp: $Timestamp`"}"
        exit 0
    }
}

# ============================================================================
# RULE 2: Kiểm tra write/edit — chặn ghi file nhạy cảm
# ============================================================================
if ($ToolName -eq "editFiles" -or $ToolName -eq "write" -or $ToolName -eq "edit") {
    $FilePath = if ($Data.toolArgs.filePath) { $Data.toolArgs.filePath } else { $Data.toolArgs.path }

    if ($FilePath) {
        # Chặn ghi vào file .env thật (cho phép .env.example)
        if ($FilePath -match '\.env$|\.env\.local$|\.env\.production$' -and $FilePath -notmatch '\.env\.example$') {
            Write-Output "{`"permissionDecision`":`"deny`",`"permissionDecisionReason`":`"[HIGH] Không được tạo/sửa file .env thật. Dùng .env.example. Timestamp: $Timestamp`"}"
            exit 0
        }

        # Chặn ghi vào private keys
        if ($FilePath -match 'id_rsa|id_ed25519|\.pem$|\.key$') {
            Write-Output "{`"permissionDecision`":`"deny`",`"permissionDecisionReason`":`"[CRITICAL] Không được tạo/sửa private keys. Timestamp: $Timestamp`"}"
            exit 0
        }
    }
}

# ============================================================================
# ALLOW: Chấp thuận
# ============================================================================
Write-Output '{"permissionDecision":"allow"}'
exit 0
