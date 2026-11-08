# Keep indexer Python and OS patch level aligned with the API image.
FROM python:3.12.16-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HOME=/tmp
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends tesseract-ocr poppler-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /srv/indexer
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m pip check \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin rahbar
COPY pipeline ./pipeline
USER 10001:10001
ENTRYPOINT ["python", "-m", "pipeline.run"]
