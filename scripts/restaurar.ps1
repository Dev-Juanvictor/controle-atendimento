# Restaura um backup feito pelo backup.ps1
# Uso, na raiz do projeto:   .\scripts\restaurar.ps1 backups\backup-20261127-1030.sql
# ATENÇÃO: substitui os dados atuais do banco pelos do arquivo.

param([Parameter(Mandatory = $true)][string]$Arquivo)

$ErrorActionPreference = "Stop"
$nome = Split-Path $Arquivo -Leaf

docker compose cp $Arquivo "mysql:/tmp/$nome"
docker compose exec -T mysql sh -c "mysql -u root -proot controle_atendimento < /tmp/$nome"

Write-Host "Banco restaurado a partir de $Arquivo"
