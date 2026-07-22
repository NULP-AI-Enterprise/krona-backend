FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /code

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt /code/

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir click
RUN CURL_CA_BUNDLE="" REQUESTS_CA_BUNDLE="" SSL_CERT_FILE="" PIP_TRUSTED_HOST="pypi.org files.pythonhosted.org github.com objects.githubusercontent.com raw.githubusercontent.com release-assets.githubusercontent.com" \
    pip install --no-cache-dir --trusted-host github.com --trusted-host release-assets.githubusercontent.com \
    uk_core_news_lg@https://github.com/explosion/spacy-models/releases/download/uk_core_news_lg-3.7.0/uk_core_news_lg-3.7.0-py3-none-any.whl

COPY . /code/
