$ErrorActionPreference = "Stop"

function Run-Step {
    param(
        [string]$Label,
        [scriptblock]$Command
    )

    Write-Host "`n== $Label =="

    & $Command

    if ($LASTEXITCODE -ne 0) {
        throw "Fallo: $Label (exit code $LASTEXITCODE)"
    }
}

# Ir a la raiz del repo
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$venvPython = Join-Path ".venv" "Scripts\python.exe"
$pycacheRoot = Join-Path $env:TEMP "agenda_ai_pycache"

if (-not (Test-Path $venvPython)) {
    throw "No existe .venv o no se encontro .\.venv\Scripts\python.exe. Corre primero el setup del entorno."
}

if (-not (Test-Path $pycacheRoot)) {
    New-Item -ItemType Directory -Path $pycacheRoot | Out-Null
}

$env:PYTHONPYCACHEPREFIX = $pycacheRoot

Run-Step "Compilando app" {
    & $venvPython -m compileall app
}

Run-Step "Probando imports criticos" {
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
        throw "No se encontro run.py en la raiz del repo."
    }
    Write-Host "run.py encontrado."
}

if (Test-Path "tests") {
    Run-Step "Corriendo tests automaticos" {
        & $venvPython -m unittest discover -s tests -p "test_*.py" -v
    }
}

Write-Host "`nValidacion finalizada correctamente."
