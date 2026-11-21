# Copia lo minimo del servidor MySQL 8.0 instalado para usarlo como MySQL portatil
# de AulaSync (unos 80 MB): mysqld.exe, sus DLL, share/ (mensajes y charsets),
# lib/private (datos ICU para REGEXP) y la licencia GPL.
#   powershell -ExecutionPolicy Bypass -File copiar_mysql.ps1 -Destino dist\AulaSync\mysql
param(
    [Parameter(Mandatory = $true)] [string] $Destino,
    [string] $Origen = $(if ($env:MYSQL_HOME) { $env:MYSQL_HOME } else { 'C:\Program Files\MySQL\MySQL Server 8.0' })
)
$ErrorActionPreference = 'Stop'

$mysqld = Join-Path $Origen 'bin\mysqld.exe'
if (-not (Test-Path $mysqld)) {
    throw "No se encontro $mysqld. Instale MySQL Server 8.0 o indique la carpeta con MYSQL_HOME."
}

if (Test-Path $Destino) { Remove-Item $Destino -Recurse -Force }
$bin = Join-Path $Destino 'bin'
New-Item -ItemType Directory -Path $bin -Force | Out-Null

Copy-Item $mysqld $bin
# DLL que necesita mysqld (se omiten las de depuracion y las de MySQL Router).
Get-ChildItem (Join-Path $Origen 'bin') -Filter '*.dll' |
    Where-Object { $_.Name -notmatch 'debug|mysqlrouter|harness' } |
    Copy-Item -Destination $bin

Copy-Item (Join-Path $Origen 'share') (Join-Path $Destino 'share') -Recurse
New-Item -ItemType Directory -Path (Join-Path $Destino 'lib') -Force | Out-Null
Copy-Item (Join-Path $Origen 'lib\private') (Join-Path $Destino 'lib\private') -Recurse
Copy-Item (Join-Path $Origen 'LICENSE') (Join-Path $Destino 'LICENSE_MYSQL.txt')

$total = (Get-ChildItem $Destino -Recurse -File | Measure-Object Length -Sum).Sum / 1MB
Write-Host ("MySQL portatil copiado en {0} ({1:N0} MB)" -f $Destino, $total)
