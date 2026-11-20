# Empaqueta la entrega final: exe + codigo fuente + scripts BD + documentos + LEEME.
# Ejecutar despues de build.bat. No incluye config.ini real ni credenciales.
$ErrorActionPreference = 'Stop'

$raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
$ejecutable = Join-Path $raiz 'dist\AulaSync\AulaSync.exe'
if (-not (Test-Path $ejecutable)) {
    throw 'No se encontro AulaSync.exe. Ejecute primero build.bat.'
}

$zip = Join-Path $raiz 'Entrega5_GrupoXX.zip'
$tmp = Join-Path $env:TEMP ('aulasync_entrega_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp -Force | Out-Null

try {
    # 1) Aplicacion compilada (exe + dependencias + sql/ + tesseract/ opcional).
    $app = Join-Path $tmp 'AulaSync'
    New-Item -ItemType Directory -Path $app -Force | Out-Null
    Copy-Item -Path (Join-Path $raiz 'dist\AulaSync\*') -Destination $app -Recurse -Force

    # Limpieza: nunca distribuir credenciales ni datos generados por el desarrollador.
    Remove-Item (Join-Path $app 'config.ini') -Force -ErrorAction SilentlyContinue
    $bandeja = Join-Path $app 'data\solicitudes'
    if (Test-Path $bandeja) { Remove-Item $bandeja -Recurse -Force }
    New-Item -ItemType Directory -Path $bandeja -Force | Out-Null
    Copy-Item -Path (Join-Path $raiz 'datos_demo\solicitudes\*') -Destination $bandeja -Recurse -Force
    $perfiles = Join-Path $app 'data\perfiles'
    if (Test-Path $perfiles) {
        Get-ChildItem $perfiles -Filter '*.json' -ErrorAction SilentlyContinue |
            Remove-Item -Force -ErrorAction SilentlyContinue
    }

    # 2) Codigo fuente documentado, sin entornos ni artefactos de compilacion.
    $fuente = Join-Path $tmp 'codigo_fuente'
    New-Item -ItemType Directory -Path $fuente -Force | Out-Null
    $excluir = @(
        '.git', '.venv', 'build', 'dist', '__pycache__', '.pytest_cache',
        'tesseract', 'data', 'documentos', 'script_bd'
    )
    Get-ChildItem -Path $raiz -Force | Where-Object { $excluir -notcontains $_.Name } |
        Copy-Item -Destination $fuente -Recurse -Force
    Get-ChildItem -Path $fuente -Recurse -Include '*.pyc', 'config.ini' -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path $fuente -Recurse -Directory -Filter '__pycache__' -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

    # 3) Scripts SQL 01 a 06 y documentacion de entrega.
    Copy-Item -Path (Join-Path $raiz 'script_bd') -Destination (Join-Path $tmp 'script_bd') -Recurse -Force
    Copy-Item -Path (Join-Path $raiz 'documentos') -Destination (Join-Path $tmp 'documentos') -Recurse -Force
    Copy-Item -Path (Join-Path $raiz 'LEEME.txt') -Destination (Join-Path $tmp 'LEEME.txt') -Force

    if (Test-Path $zip) { Remove-Item $zip -Force }
    Compress-Archive -Path (Join-Path $tmp '*') -DestinationPath $zip -Force
}
finally {
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "Listo: $zip"
