# ============================================================================
# POST-TOOL AUDIT HOOK (PowerShell)
# Ghi nhật ký audit sau khi AI hoàn thành thực thi công cụ
# ============================================================================

$Input = $input | Out-String
try {
    $Data = $Input | ConvertFrom-Json
    $ToolName = $Data.toolName
} catch {
    $ToolName = "unknown"
}

$Timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
$AuditDir = ".github\hooks\audit-logs"

# Tạo thư mục audit nếu chưa có
if (-not (Test-Path $AuditDir)) {
    New-Item -ItemType Directory -Path $AuditDir -Force | Out-Null
}

# Ghi log
$AuditFile = Join-Path $AuditDir "audit-$(Get-Date -Format 'yyyyMMdd').jsonl"

try {
    $Agent = if ($Data.agentName) { $Data.agentName } else { "unknown" }
    $Status = if ($Data.toolResult.status) { $Data.toolResult.status } else { "completed" }
} catch {
    $Agent = "unknown"
    $Status = "completed"
}

$AuditEntry = @{
    timestamp = $Timestamp
    tool = $ToolName
    agent = $Agent
    status = $Status
    action = "post_tool_audit"
} | ConvertTo-Json -Compress

Add-Content -Path $AuditFile -Value $AuditEntry

# Luôn cho phép (post-tool không chặn)
Write-Output '{"permissionDecision":"allow"}'
exit 0
