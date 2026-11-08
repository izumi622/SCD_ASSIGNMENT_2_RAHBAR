# Newer, explicitly versioned Python / Debian Bookworm base.
FROM python:3.12.16-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HOME=/tmp

# Refresh Debian security packages in the final runtime image. The old pinned
# 3.12.10 base contained fixable libssl, gnutls, apt, perl and other OS CVEs.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv/api
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m pip check \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin rahbar
COPY app ./app
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
