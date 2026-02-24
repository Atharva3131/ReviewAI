# Comprehensive Code Quality Check Script for Revive AI (PowerShell)
# Runs quality checks for both backend and frontend

# Color functions
function Write-Header {
    param([string]$Message)
    Write-Host "`n================================================================================" -ForegroundColor Blue
    Write-Host $Message -ForegroundColor Blue
    Write-Host "================================================================================`n" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Error-Message {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Write-Warning-Message {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

# Track results
$BackendSuccess = $false
$FrontendSuccess = $false

# Parse arguments
$FixMode = $args -contains "--fix"

Write-Header "Revive AI - Comprehensive Code Quality Checks"

# Backend quality checks
Write-Header "Backend Quality Checks"
Push-Location backend

try {
    if ($FixMode) {
        Write-Warning-Message "Running in fix mode..."
        python scripts/quality_check.py --fix
        if ($LASTEXITCODE -eq 0) {
            $BackendSuccess = $true
            Write-Success "Backend formatting fixes applied"
        } else {
            Write-Error-Message "Backend formatting fixes failed"
        }
    } else {
        python scripts/quality_check.py
        if ($LASTEXITCODE -eq 0) {
            $BackendSuccess = $true
            Write-Success "Backend quality checks passed"
        } else {
            Write-Error-Message "Backend quality checks failed"
        }
    }
} catch {
    Write-Error-Message "Backend quality checks encountered an error: $_"
} finally {
    Pop-Location
}

# Frontend quality checks
Write-Header "Frontend Quality Checks"
Push-Location frontend

try {
    if ($FixMode) {
        node scripts/quality-check.js --fix
        if ($LASTEXITCODE -eq 0) {
            $FrontendSuccess = $true
            Write-Success "Frontend formatting fixes applied"
        } else {
            Write-Error-Message "Frontend formatting fixes failed"
        }
    } else {
        node scripts/quality-check.js
        if ($LASTEXITCODE -eq 0) {
            $FrontendSuccess = $true
            Write-Success "Frontend quality checks passed"
        } else {
            Write-Error-Message "Frontend quality checks failed"
        }
    }
} catch {
    Write-Error-Message "Frontend quality checks encountered an error: $_"
} finally {
    Pop-Location
}

# Summary
Write-Header "Quality Check Summary"

if ($BackendSuccess) {
    Write-Success "Backend: PASSED"
} else {
    Write-Error-Message "Backend: FAILED"
}

if ($FrontendSuccess) {
    Write-Success "Frontend: PASSED"
} else {
    Write-Error-Message "Frontend: FAILED"
}

# Exit with appropriate code
if ($BackendSuccess -and $FrontendSuccess) {
    Write-Success "`n✓ All quality checks passed!"
    exit 0
} else {
    Write-Error-Message "`n✗ Some quality checks failed"
    if (-not $FixMode) {
        Write-Warning-Message "Run with --fix to auto-fix formatting issues"
    }
    exit 1
}
