# python:3.12-slim, NOT -alpine (the box template's default). Lesesalen depends on
# nh3 (Rust) and Pillow (C); both publish manylinux wheels but musl coverage is
# patchier, and a source build would drag a Rust toolchain onto a 3.7 GB box.
# Switching this back to alpine turns a 20-second pull into a toolchain build.
FROM python:3.12-slim

WORKDIR /app

RUN adduser --system --group --home /app lesesalen

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# The Svelte client is built in CI and committed to client/dist (ADR 0001) — the
# box never runs Node. If the directory is missing the app still boots and serves
# the API; only the UI is gone.
COPY client/dist ./client/dist

# robots.txt + sitemap.xml must be in the image — a selective COPY that omits them
# ships 404s (hetzner-server/NEW-SERVICE.md).
COPY robots.txt sitemap.xml ./
COPY app ./app

# Git-derived site dates, written by scripts/generate-page-dates.sh (run by
# `make deploy`/`make verify` — the image has no .git). The trailing glob makes
# the COPY a no-op when the file is absent, so a bare `docker build` still
# works; the app then falls back to boot time.
COPY page-dates.jso[n] ./

ENV LESESALEN_DATA_DIR=/data
RUN mkdir -p /data && chown -R lesesalen:lesesalen /data /app
USER lesesalen

# This image's git identity, written by scripts/generate-build-info.sh on the
# checkout at deploy and served at /version (naustet-server ADR 0022). It sits at
# the image root, next to page-dates.json, because that is where app/shell.py's
# `parent.parent` already looks.
#
# THE LAST COPY, deliberately — and after the chown too: `built_at` changes on
# every single deploy, so anything below this line would be rebuilt every deploy.
# The glob makes it a no-op when the file is absent, so a bare `docker build`
# still works; /version then reports source "unknown" rather than guessing.
# (Ownership stays root:root at mode 0644, which the unprivileged user can read.)
COPY build-info.jso[n] ./

EXPOSE 8080
# --no-access-log is load-bearing, not tidiness: /api/berik receives the URIs of
# the posts someone is reading, and we promise not to log them (ADR 0003).
# Uvicorn's access log writes the path of every request.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]
