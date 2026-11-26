# Backup do banco (MySQL no Docker) para a pasta backups/
# Uso, na raiz do projeto:   .\scripts\backup.ps1
# Resultado: backups\backup-AAAAMMDD-HHMM.sql   (a pasta backups/ não vai para o GitHub)

$ErrorActionPreference = "Stop"
$arquivo = "backup-$(Get-Date -Format 'yyyyMMdd-HHmm').sql"
New-Item -ItemType Directory -Force -Path backups | Out-Null

# O mysqldump roda dentro do container e grava o arquivo lá; depois copiamos para cá.
# (Assim o arquivo não passa pelo PowerShell, que poderia trocar a codificação.)
docker compose exec -T mysql sh -c "mysqldump -u root -proot --single-transaction controle_atendimento > /tmp/$arquivo"
docker compose cp "mysql:/tmp/$arquivo" "backups/$arquivo"

Write-Host "Backup salvo em backups\$arquivo"
