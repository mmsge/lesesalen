# Standard service targets for the Hetzner box. Slug is this service's dir name.
SERVER ?= msge
SLUG   ?= lesesalen
PORT   ?= 4023

deploy:            ## Pull, rebuild, restart (run on the server in /srv/$(SLUG))
	git pull --ff-only
	./scripts/generate-page-dates.sh || echo "WARN: page dates not regenerated — pages will stamp boot time"
	docker compose up -d --build

logs:              ## Follow container logs
	docker compose logs -f --tail=100

status:            ## Show container status
	docker compose ps

verify:            ## Build + boot + hit /healthz (local smoke test)
	./scripts/generate-page-dates.sh || echo "WARN: page dates not regenerated — pages will stamp boot time"
	docker compose up -d --build
	@sleep 5
	@curl -fsS http://172.18.0.1:$(PORT)/healthz && echo "  OK" || (echo "  FAILED"; exit 1)

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
