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
  # awk lê os valores via ENVIRON[], nunca embutidos no "programa" como o sed
  # fazia — assim qualquer caractere no token/chatid (inclusive o delimitador
  # '|' que derrubava o sed) é tratado como dado literal. Usamos ENVIRON em vez
  # de -v porque -v processa escapes em C (transformaria '\g' em 'g').
  # No BEGIN escapamos '\' e '&' porque na string de substituição do gsub eles
  # têm significado especial ('&' = trecho casado).
  awk '
    BEGIN {
      tok = ENVIRON["TELEGRAM_BOT_TOKEN"]
      cid = ENVIRON["TELEGRAM_CHAT_ID"]
      gsub(/[\\&]/, "\\\\&", tok)
      gsub(/[\\&]/, "\\\\&", cid)
    }
    {
      gsub(/\$\{TELEGRAM_BOT_TOKEN\}/, tok)
      gsub(/\$\{TELEGRAM_CHAT_ID\}/, cid)
      print
    }
  ' "$tpl" > "$out"
  rm "$tpl"
done

exec /run.sh
