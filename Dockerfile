FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends chromium fonts-wqy-zenhei ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 muse
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

ENV MUSE2API_HOST=0.0.0.0 \
    MUSE2API_DATA_DIR=/app/data \
    MUSE2API_CHROMIUM_PATH=/usr/bin/chromium

RUN mkdir -p /app/data && chown -R muse:muse /app
USER muse

EXPOSE 18610
CMD ["museai"]
