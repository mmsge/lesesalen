# Standard service targets for the Hetzner box. Slug is this service's dir name.
SERVER ?= msge
SLUG   ?= lesesalen
PORT   ?= 4023

deploy:            ## Pull, rebuild, restart (run on the server in /srv/$(SLUG))
	git pull --ff-only
	./scripts/generate-page-dates.sh || echo "WARN: page dates not regenerated — pages will stamp boot time"
	@# BEFORE the build, always (naustet-server ADR 0022): the SHA has to be baked
	@# into the IMAGE. That is what makes a git pull with no rebuild visible — the
	@# checkout moves, the container keeps serving the old commit at /version.
	./scripts/generate-build-info.sh || echo "WARN: build info not regenerated — /version will report source=unknown"
	docker compose up -d --build

logs:              ## Follow container logs
	docker compose logs -f --tail=100

status:            ## Show container status
	docker compose ps

verify:            ## Build + boot + hit /healthz, /version, /health (local smoke test)
	./scripts/generate-page-dates.sh || echo "WARN: page dates not regenerated — pages will stamp boot time"
	./scripts/generate-build-info.sh || echo "WARN: build info not regenerated — /version will report source=unknown"
	docker compose up -d --build
	@sleep 5
	@curl -fsS http://172.18.0.1:$(PORT)/healthz | grep -qx ok && echo "  /healthz OK" || (echo "  /healthz FAILED"; exit 1)
	@# source must be "build-info": "unknown" means the file never reached the
	@# image (a .dockerignore or a missing COPY), and /version silently lies.
	@curl -fsS http://172.18.0.1:$(PORT)/version | grep -q '"source": *"build-info"' && echo "  /version OK" || (echo "  /version FAILED"; exit 1)
	@# degraded is a 200 on purpose, so -f is the right check here; only a real
	@# failure (503) should make verify fail.
	@curl -fsS http://172.18.0.1:$(PORT)/health | grep -q '"checks"' && echo "  /health OK" || (echo "  /health FAILED"; exit 1)

remote-deploy:     ## Deploy from a laptop over SSH
	ssh $(SERVER) 'cd /srv/$(SLUG) && make deploy'

# ─── client (never built on the box — see ADR 0001) ───────────────────────────
client:            ## Build the Svelte client into client/dist (commit the result)
	cd client && npm ci && npm run build

client-dev:        ## Vite dev server on :5173, proxying /api to a local server
	cd client && npm install && npm run dev

test:              ## Run the server test suite
	python -m pytest -q

.PHONY: deploy logs status verify remote-deploy client client-dev test
