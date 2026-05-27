#!/bin/bash
# setup_rclone.sh — Documentação executável do setup inicial do rclone
#
# Este script NÃO roda automaticamente. Ele orienta passo a passo o que
# fazer na primeira vez para configurar o rclone na VM para os dois
# destinos de backup (Oracle Object Storage + Google Drive).
#
# Rode com:  bash scripts/setup_rclone.sh

cat <<'EOF'
╔══════════════════════════════════════════════════════════════════════╗
║         SETUP INICIAL DO BACKUP DUPLO ARGUS AI                       ║
║         (Oracle Object Storage + Google Drive)                       ║
╚══════════════════════════════════════════════════════════════════════╝

Roteiro em 5 passos. Faça cada um e depois rode o backup manualmente
para validar antes de habilitar o cron.

═══════════════════════════════════════════════════════════════════════
PASSO 1 — Instalar rclone e gpg na VM
═══════════════════════════════════════════════════════════════════════

  sudo apt update
  sudo apt install -y rclone gnupg

Confirma versões:

  rclone version    # deve ser >= 1.60
  gpg --version

═══════════════════════════════════════════════════════════════════════
PASSO 2 — Configurar remote "oracle" (S3-compatible)
═══════════════════════════════════════════════════════════════════════

  rclone config

Escolha:
  n) New remote
  name>  oracle
  Storage>  s3                          (S3 Compliant Storage Providers)
  provider>  Other
  env_auth>  false                       (vamos colocar credenciais inline)
  access_key_id>  <Access Key do Oracle Object Storage>
  secret_access_key>  <Secret Key do Oracle — guardada no seu cofre de senhas>
  region>  sa-saopaulo-1
  endpoint>  https://grjzkxyb1rpa.compat.objectstorage.sa-saopaulo-1.oraclecloud.com
  location_constraint>  (deixa em branco — Enter)
  acl>  private
  Edit advanced config?  No
  Keep this "oracle" remote?  Yes

Teste:

  rclone lsd oracle:                    # deve listar "argus-backups"
  rclone touch oracle:argus-backups/.test_oracle
  rclone delete oracle:argus-backups/.test_oracle

═══════════════════════════════════════════════════════════════════════
PASSO 3 — Configurar remote "gdrive" (Google Drive)
═══════════════════════════════════════════════════════════════════════

A VM não tem browser, então o fluxo é:
  - Rodar 'rclone authorize "drive"' no seu PC (que tem browser)
  - Copiar o token retornado e colar na config da VM

NO SEU PC (não na VM):
  rclone authorize "drive"

  → vai abrir o browser, faz login com alexmabud@gmail.com
  → autoriza o app rclone
  → terminal mostra um TOKEN JSON grande tipo:
       {"access_token":"...","token_type":"Bearer",...}
  → COPIA o JSON inteiro

NA VM:
  rclone config

  n) New remote
  name>  gdrive
  Storage>  drive                       (Google Drive)
  client_id>  (deixa vazio — usa o default do rclone)
  client_secret>  (deixa vazio)
  scope>  drive                          (acesso total)
  service_account_file>  (deixa vazio)
  Edit advanced config?  No
  Use auto config?  No                  (importante — VM sem browser!)
  config_token>  <COLA AQUI O JSON DO PC>
  Configure this as a Shared Drive?  No
  Keep this "gdrive" remote?  Yes

Teste:

  rclone mkdir gdrive:Argus_Backups
  rclone touch gdrive:Argus_Backups/.test_gdrive
  rclone delete gdrive:Argus_Backups/.test_gdrive

═══════════════════════════════════════════════════════════════════════
PASSO 4 — Salvar senha do GPG
═══════════════════════════════════════════════════════════════════════

A senha do GPG (que você salvou no seu cofre de senhas) precisa estar acessível
ao script de backup que roda via cron — sem prompt interativo.

Crie o arquivo:

  sudo bash -c 'cat > /root/.argus_gpg_passphrase'
  # cola a senha, depois Ctrl+D

Endurece permissões (CRÍTICO):

  sudo chown root:root /root/.argus_gpg_passphrase
  sudo chmod 600 /root/.argus_gpg_passphrase

Verifique:

  sudo ls -la /root/.argus_gpg_passphrase
  # deve mostrar: -rw------- 1 root root ... .argus_gpg_passphrase

═══════════════════════════════════════════════════════════════════════
PASSO 5 — Validar com backup manual
═══════════════════════════════════════════════════════════════════════

Rode o backup uma vez manualmente:

  sudo /home/ubuntu/argus-ai/scripts/backup_to_clouds.sh

Demora ~2-5 min na primeira vez (precisa subir 335MB+ das fotos pro
Google Drive). Acompanha o log:

  tail -f /var/log/argus_backup.log

Resultado esperado: "=== Backup concluído com sucesso ==="

Confere se os arquivos chegaram:

  rclone ls oracle:argus-backups/banco/
  rclone ls oracle:argus-backups/env/
  rclone ls oracle:argus-backups/grafana/
  rclone ls gdrive:Argus_Backups/banco/
  rclone ls gdrive:Argus_Backups/fotos/ | head

═══════════════════════════════════════════════════════════════════════
PASSO 6 — Habilitar cron diário (apenas após validação OK)
═══════════════════════════════════════════════════════════════════════

  sudo tee /etc/cron.d/argus-backup-clouds > /dev/null <<CRON
# Backup diário do Argus AI para Oracle + Google Drive
# Roda 03:00 BRT (06:00 UTC) — sistema ocioso a essa hora.
MAILTO=""
0 6 * * * root /home/ubuntu/argus-ai/scripts/backup_to_clouds.sh
CRON

  sudo chmod 644 /etc/cron.d/argus-backup-clouds

Pronto. Daqui pra frente, todo dia às 03h vai rodar automaticamente.

Monitoramento: o script atualiza a métrica
  argus_backup_clouds_last_success_timestamp_seconds
em /mnt/banco/textfile/backup_clouds.prom — o Prometheus já coleta
esse diretório via node-exporter textfile collector.

═══════════════════════════════════════════════════════════════════════
EOF
