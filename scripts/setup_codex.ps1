$ErrorActionPreference = "Stop"

Write-Host "== Agenda AI setup =="

# Ir a la raíz del repo
Set-Location (Split-Path -Parent $PSScriptRoot)

# Detectar Python
$pythonCmd = $null

try {
    python --version | Out-Null
    $pythonCmd = "python"
} catch {}

if (-not $pythonCmd) {
    try {
        py --version | Out-Null
        $pythonCmd = "py"
    } catch {}
}

if (-not $pythonCmd) {
    throw "No se encontró Python en PATH."
}

# Crear venv si no existe
if (-not (Test-Path ".venv")) {
    Write-Host "Creando entorno virtual .venv..."
    if ($pythonCmd -eq "py") {
        py -m venv .venv
    } else {
        python -m venv .venv
    }
} else {
    Write-Host ".venv ya existe."
}

# Resolver ejecutable de Python del venv
$venvPython = Join-Path ".venv" "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "No se encontró $venvPython"
}

Write-Host "Actualizando pip..."
& $venvPython -m pip install --upgrade pip

if (Test-Path "requirements.txt") {
    Write-Host "Instalando requirements..."
    & $venvPython -m pip install -r requirements.txt
} else {
    Write-Host "No existe requirements.txt, se omite instalación."
}

Write-Host "Setup finalizado."
Write-Host "Usar este Python para validaciones: $venvPython"