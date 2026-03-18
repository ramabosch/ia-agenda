$ErrorActionPreference = "Stop"

function Run-Step {
    param(
        [string]$Label,
        [scriptblock]$Command
    )

    Write-Host "`n== $Label =="

    & $Command

    if ($LASTEXITCODE -ne 0) {
        throw "Falló: $Label (exit code $LASTEXITCODE)"
    }
}

# Ir a la raíz del repo
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$venvPython = Join-Path ".venv" "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    throw "No existe .venv o no se encontró .\.venv\Scripts\python.exe. Corré primero el setup del entorno."
}

Run-Step "Compilando app" {
    & $venvPython -m compileall app
}

Run-Step "Probando imports críticos" {
    $tempPy = Join-Path $env:TEMP "agenda_ai_validate_imports.py"

    $pyCode = @"
import importlib
import sys

repo_root = r'$repoRoot'
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

modules = [
    "app.services.query_parser_service",
    "app.services.llm_parser_service",
    "app.services.hybrid_parser_service",
    "app.services.reference_resolver",
    "app.services.query_response_service",
    "app.services.task_service",
    "app.services.project_service",
]

for name in modules:
    importlib.import_module(name)

print("OK_IMPORTS")
"@

    Set-Content -Path $tempPy -Value $pyCode -Encoding UTF8
    & $venvPython $tempPy
    $exitCode = $LASTEXITCODE

    Remove-Item $tempPy -ErrorAction SilentlyContinue

    if ($exitCode -ne 0) {
        exit $exitCode
    }
}

Run-Step "Verificando entrypoint" {
    if (-not (Test-Path "run.py")) {
        throw "No se encontró run.py en la raíz del repo."
    }
    Write-Host "run.py encontrado."
}

Write-Host "`nValidación finalizada correctamente."