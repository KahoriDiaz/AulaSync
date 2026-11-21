# Empaqueta la entrega final: exe + codigo fuente + scripts BD + LEEME + acceso directo.
# Ejecutar despues de build.bat. No incluye config.ini, entornos ni archivos .md.
$ErrorActionPreference = 'Stop'

$raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
$ejecutable = Join-Path $raiz 'dist\AulaSync\AulaSync.exe'
if (-not (Test-Path $ejecutable)) {
    throw 'No se encontro AulaSync.exe. Ejecute primero build.bat.'
}

$zip = Join-Path $raiz 'Entrega5_GrupoXX.zip'
$tmp = Join-Path $env:TEMP ('aulasync_entrega_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp -Force | Out-Null

# Nunca se distribuyen: entornos, cache, credenciales ni especificaciones .md
$excluirCarpetas = @('.git', '.venv', 'venv', 'entorno', 'build', 'dist', '__pycache__',
    '.pytest_cache', '.claude', 'tesseract', 'data', 'script_bd', 'mysql', 'mysql_data',
    'mysql_plantilla')
# En la app compilada NO se borran *.zip ni *.pyc: PyInstaller necesita base_library.zip.
$excluirApp = @('config.ini', '*.md')
$excluirFuente = @('*.pyc', 'config.ini', '*.md', '*.zip', '*.spec', '*.lnk')

function Limpiar-Carpeta([string] $ruta, [string[]] $excluirArchivos) {
    Get-ChildItem -Path $ruta -Recurse -Force -Directory -ErrorAction SilentlyContinue |
        Where-Object { @('__pycache__', '.pytest_cache', '.git', '.venv', 'mysql_data') -contains $_.Name } |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Path $ruta -Recurse -Force -File -Include $excluirArchivos -ErrorAction SilentlyContinue |
        Remove-Item -Force -ErrorAction SilentlyContinue
}

try {
    # 1) Aplicacion compilada (exe + dependencias + sql/ + tesseract/ opcional).
    $app = Join-Path $tmp 'AulaSync'
    New-Item -ItemType Directory -Path $app -Force | Out-Null
    Copy-Item -Path (Join-Path $raiz 'dist\AulaSync\*') -Destination $app -Recurse -Force
    Limpiar-Carpeta $app $excluirApp
    if (-not (Test-Path (Join-Path $app '_internal\base_library.zip'))) {
        throw 'Falta _internal\base_library.zip: el ejecutable no arrancaria.'
    }
    if (-not (Test-Path (Join-Path $app 'mysql\bin\mysqld.exe'))) {
        throw 'Falta el MySQL portatil en dist\AulaSync\mysql. Ejecute build.bat.'
    }
    if (-not (Test-Path (Join-Path $app 'mysql_plantilla\aulasync_bd_lista.txt'))) {
        throw 'Falta la plantilla de la base en dist\AulaSync\mysql_plantilla. Ejecute build.bat.'
    }

    # 2) Codigo fuente, sin entornos ni artefactos de compilacion.
    $fuente = Join-Path $tmp 'codigo_fuente'
    New-Item -ItemType Directory -Path $fuente -Force | Out-Null
    Get-ChildItem -Path $raiz -Force | Where-Object {
        $excluirCarpetas -notcontains $_.Name -and -not ($_.Name -like '*.zip')
    } | Copy-Item -Destination $fuente -Recurse -Force
    Limpiar-Carpeta $fuente $excluirFuente

    # 3) Scripts SQL 01 a 06 y LEEME.
    Copy-Item -Path (Join-Path $raiz 'script_bd') -Destination (Join-Path $tmp 'script_bd') -Recurse -Force
    Copy-Item -Path (Join-Path $raiz 'LEEME.txt') -Destination (Join-Path $tmp 'LEEME.txt') -Force

    # 4) Acceso directo con ruta relativa: explorer.exe abre AulaSync\AulaSync.exe
    #    respecto de la carpeta donde se descomprima el ZIP.
    $shell = New-Object -ComObject WScript.Shell
    $acceso = $shell.CreateShortcut((Join-Path $tmp 'AulaSync.lnk'))
    $acceso.TargetPath = Join-Path $env:WINDIR 'explorer.exe'
    $acceso.Arguments = 'AulaSync\AulaSync.exe'
    $acceso.WorkingDirectory = ''
    $acceso.IconLocation = 'AulaSync\AulaSync.exe,0'
    $acceso.Description = 'Abrir AulaSync'
    $acceso.Save()
    Copy-Item -Path (Join-Path $tmp 'AulaSync.lnk') -Destination (Join-Path $raiz 'AulaSync.lnk') -Force

    if (Test-Path $zip) { Remove-Item $zip -Force }
    Compress-Archive -Path (Join-Path $tmp '*') -DestinationPath $zip -Force
}
finally {
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "Listo: $zip"
