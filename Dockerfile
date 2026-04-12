FROM python:3.9.13-alpine3.16

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    libffi-dev \
    openssl-dev \
    netcat-openbsd

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]