FROM python:3.10-slim

# Systempakete inklusive libpq-dev installieren:
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./

RUN python -m pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Ajout d'un certificat SSL personnalisé pour Zscaler dans le répertoire des certificats CA
ADD ./certifcats/ZscalerRootCertificate-2048-SHA256.crt /usr/local/share/ca-certificates/ZscalerRootCertificate.crt

# Modification des permissions du certificat et mise à jour des certificats CA pour prendre en compte le nouveau certificat
RUN chmod 644 /usr/local/share/ca-certificates/ZscalerRootCertificate.crt && update-ca-certificates

# Définition de la variable d'environnement pour utiliser le certificat SSL personnalisé dans les requêtes HTTP
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
