#!/bin/sh
# Renderiza templates .tpl do provisioning expandindo variáveis de ambiente
# antes do Grafana ler. Necessário porque o Grafana 10.x não preserva tipo
# string ao expandir ${VAR} no YAML quando o valor é numérico (ex.: chatid
# do Telegram com sinal negativo). Sem este pré-processamento o provisioning
# falha com "cannot unmarshal number into Go struct field Config.chatid".
set -e

SRC=/etc/grafana/provisioning-src
DST=/var/lib/grafana/provisioning

rm -rf "$DST"
mkdir -p "$DST"
cp -r "$SRC/." "$DST/"

find "$DST" -name "*.tpl" | while read -r tpl; do
  out="${tpl%.tpl}"
  sed -e "s|\${TELEGRAM_BOT_TOKEN}|${TELEGRAM_BOT_TOKEN}|g" \
      -e "s|\${TELEGRAM_CHAT_ID}|${TELEGRAM_CHAT_ID}|g" \
      "$tpl" > "$out"
  rm "$tpl"
done

exec /run.sh
