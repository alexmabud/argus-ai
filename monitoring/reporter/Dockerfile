FROM python:3.11-alpine

RUN apk add --no-cache dcron tzdata

ENV TZ=America/Sao_Paulo

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY daily_report.py .

# Cron: todo dia às 8h BRT
RUN echo "0 8 * * * /usr/local/bin/python /app/daily_report.py >> /proc/1/fd/1 2>&1" \
    > /etc/crontabs/root

CMD ["crond", "-f", "-l", "2"]
