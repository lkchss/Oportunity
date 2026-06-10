# PostToolUse hook (Write|Edit): run the Opportunity pytest suite when a .py
# file inside this project changes. Silent on pass; on failure, surfaces the
# pytest summary to the model (additionalContext) and a short note to the user.
# Non-blocking: the edit always stands; this only reports.

$ErrorActionPreference = 'SilentlyContinue'

# Hook input arrives as JSON on stdin.
$raw = [Console]::In.ReadToEnd()
if (-not $raw) { exit 0 }
try { $payload = $raw | ConvertFrom-Json } catch { exit 0 }

$fp = $payload.tool_input.file_path
if (-not $fp) { exit 0 }
if ($fp -notlike '*.py') { exit 0 }

# project root = three hops up from .claude\hooks\run-tests.ps1
$proj = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSCommandPath))

# only run for edits inside this project (case/slash-insensitive prefix match)
$fpNorm = $fp.ToLower().Replace('/', '\')
$projNorm = $proj.ToLower()
if (-not $fpNorm.StartsWith($projNorm)) { exit 0 }

Push-Location $proj
$out = & python -m pytest tests/ -q 2>&1 | Out-String
$code = $LASTEXITCODE
Pop-Location

if ($code -ne 0) {
    $tail = ($out -split "`r?`n" | Where-Object { $_ -ne '' } | Select-Object -Last 15) -join "`n"
    $ctx = "Opportunity pytest FAILED after editing $fp`n`n$tail"
    $obj = @{
        systemMessage      = "Opportunity tests failed after edit - see context"
        hookSpecificOutput = @{
            hookEventName     = "PostToolUse"
            additionalContext = $ctx
        }
    }
    Write-Output ($obj | ConvertTo-Json -Depth 5 -Compress)
}
exit 0
