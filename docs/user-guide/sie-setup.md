# SIE Provider Setup

![SIE](https://img.shields.io/badge/SIE-Superlinked_Inference_Engine-blue)
![Docker](https://img.shields.io/badge/Docker-optional-2496ED?logo=docker&logoColor=white)
![BGE-M3](https://img.shields.io/badge/BGE--M3-1024--dim-orange)

The **SIE (Superlinked Inference Engine)** provider runs open-source embedding models
(BGE-M3, Stella-v5, SPLADE-v3) via any SIE-compatible HTTP endpoint.

> **You do not need Docker** if you already have access to a hosted SIE gateway.
> Point the server at it with `SIE_ENDPOINT` and `SIE_API_KEY` in `.env`.
> Docker is a **self-hosted fallback** for teams without a remote gateway.
> **Opt-in only — not part of the default stack.** `./start-services.sh` and `docker compose up`
> start the **server + dashboard only** — they never start SIE.
> Default config keeps `SIE_ENABLED=false` so you are not blocked on warm-up or disk usage.

---

## Environment variables — what each one does

Three server `.env` variables control SIE. They are **not** split into “local” vs “remote” flags — the same three apply to both paths.

| Variable | Role | Local Docker | Remote gateway |
|---|---|---|---|
| `SIE_ENABLED` | **Master on/off** for the SIE provider in this server | `true` | `true` |
| `SIE_ENDPOINT` | **Where** to send encode requests (HTTP base URL) | `http://localhost:8720` (or `http://host.docker.internal:8720` when server is in Docker) | `https://your-sie-gateway.example.com` |
| `SIE_API_KEY` | **Auth** — sent as `Authorization: Bearer …` when set | Usually **unset** | Usually **required** |

`HF_TOKEN` is **not** a server variable for routing — it is only for the **Docker container** to download model weights (Path B).

**When `SIE_ENABLED=false` (default):**

- `GET /health` → `"sie": "disabled"`
- Experiments with `provider: sie` fail preflight
- `POST /api/v1/sweep` defaults to local `all-MiniLM-L6-v2` instead of BGE-M3

**When `SIE_ENABLED=true`:** the server probes whatever URL is in `SIE_ENDPOINT` (local or remote) via `/healthz`.

---

## Choose your path

| Path | When to use | What you need |
|---|---|---|
| **A — Remote gateway** *(recommended if available)* | Your org runs SIE (Helm/K8s, managed gateway, hackathon endpoint) | `SIE_ENABLED=true`, `SIE_ENDPOINT`, `SIE_API_KEY` in server `.env` — **no Docker** |
| **B — Self-hosted Docker** | No remote gateway; you run SIE locally on `:8720` | Docker Desktop, `HF_TOKEN`, warm-up per [§ Self-hosted Docker](#self-hosted-docker-optional) below |

### Path A — Remote gateway (no Docker)

```bash
# .env — server only; no SIE container on your machine
SIE_ENABLED=true
SIE_ENDPOINT=https://your-sie-gateway.example.com
SIE_API_KEY=your_gateway_token
```

Restart the server (`docker compose restart server` or reload uvicorn). Verify:

```bash
curl -H "Authorization: Bearer $SIE_API_KEY" \
  "$SIE_ENDPOINT/healthz"
# → ok
```

When the gateway is warm, `GET http://localhost:8001/health` returns `"sie":"reachable"`.
Skip to [§ Use SIE in a config](#use-sie-in-a-config).

### Path B — Self-hosted Docker

Follow [§ Self-hosted Docker (optional)](#self-hosted-docker-optional) below, then set:

```bash
SIE_ENABLED=true
SIE_ENDPOINT=http://localhost:8720   # host.docker.internal:8720 when server runs in Docker
```

`SIE_API_KEY` is usually empty for local Docker; set it only if you enable auth on the container.

---

## Self-hosted Docker (optional)

Use this path only when you **do not** have a remote `SIE_ENDPOINT`. The image is ~3.8 GB;
first-run model download and warm-up can take 10–30+ minutes on Apple Silicon.

### Prerequisites (Docker path only)

| Requirement | Notes |
|---|---|
| Docker Desktop | 4 GB+ of free disk space |
| `HF_TOKEN` | HuggingFace read token — required for model downloads inside the container |
| Apple Silicon (M1/M2/M3) | Extra `--platform linux/amd64` flag required (see below) |

> **`HF_TOKEN` is only for the Docker path.** Remote gateways manage their own model weights;
> the rag-params-finder server never calls HuggingFace directly.

### Get a HuggingFace token (Docker path only)

1. Sign in at [huggingface.co](https://huggingface.co/settings/tokens)
2. Create a **Read** token
3. Export it in your shell — or add it to `.env`:

```bash
export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx
```

> **Note:** `HF_TOKEN` is only needed by the SIE container for model downloads. It does not
> go into the server's `.env` (the server never calls HuggingFace directly). You can pass it
> as a shell export or add `HF_TOKEN=hf_...` to `.env` and source it.

---

## 1. Start the SIE container

Use this exact command — each flag matters:

```bash
docker run -d \
  --name sie-server \
  -p 8720:8080 \
  -v sie-hf-cache:/app/.cache/huggingface \
  --platform linux/amd64 \
  -e HF_TOKEN=$HF_TOKEN \
  ghcr.io/superlinked/sie-server:latest-cpu-default
```

| Flag | Why |
|---|---|
| `-p 8720:8080` | Container listens on 8080 internally; host port **8720** avoids clashes with Jenkins, Tomcat, Spark, and other services that commonly use 8080 |
| `-v sie-hf-cache:/...` | Persists model weights between restarts — without this, BGE-M3 (~570 MB) re-downloads every time |
| `--platform linux/amd64` | Required on Apple Silicon (M1/M2/M3) — the image is x86-only |
| `-e HF_TOKEN=$HF_TOKEN` | Passed to the container for the initial model download |

Watch logs to confirm startup:

```bash
docker logs -f sie-server
```

---

## 2. Verify the container is reachable

SIE exposes **`/healthz`** (not `/health`) and **`/readyz`**:

```bash
curl http://localhost:8720/healthz
# → ok
```

> **`/healthz` returning `ok` does NOT mean the model is ready to serve requests.**
> It only means the process is alive. Model loading is a separate phase — see step 3.

---

## 3. Wait for the model to warm up

BGE-M3 must be downloaded (first run only) **and** loaded into memory before SIE can
serve encode requests. During warm-up, encode calls return **HTTP 503**. This is expected
and can take:

- **First run (Intel/AMD Linux):** 3–10 minutes (model download ~570 MB + load)
- **First run (Apple Silicon with `--platform linux/amd64`):** 10–30+ minutes — Rosetta 2
  emulation makes weight deserialization much slower; repeated 503s for a long time are
  normal, not necessarily a failure
- **Subsequent runs (cached volume):** 1–3 minutes (load only; no re-download)

### Liveness vs model readiness (do not confuse these)

| Check | Endpoint | `ok` / `200` means |
|---|---|---|
| SIE process alive | `GET /healthz` | HTTP server is running |
| Model can encode | `POST /v1/encode/BAAI/bge-m3` | Weights downloaded **and** loaded |
| App server sees SIE | `GET http://localhost:8001/health` → `"sie":"reachable"` (when `SIE_ENABLED=true`) or `"disabled"` (default) | `/healthz` responded — **not** that BGE-M3 is warm |

You can have all three green at different times. **`/healthz` and app `/health` can pass while encode still returns 503.** Only submit sweeps or experiments after the encode probe returns **HTTP 200**.

### Expected warm-up log sequence

When tailing `docker logs -f sie-server`, you will typically see this progression:

| Phase | Example log line | Meaning |
|---|---|---|
| 1 — Startup | `Starting SIE server on 0.0.0.0:8080` | Container up |
| 2 — Cache warning *(benign)* | `WARNING ... Failed to get disk stats for /app/.cache/huggingface/hub: [Errno 2] No such file or directory` | HF cache `hub/` subdir does not exist yet on a fresh volume — **ignore unless downloads never start** |
| 3 — Download | `Fetching 21 files: 14%\|█▍ \| 3/21 [...]` | Weights downloading into the volume |
| 4 — Load | `Loading BAAI/bge-m3 on device=cpu` | Deserializing into memory (slow on Apple Silicon) |
| 5 — Warm-up traffic | `POST /v1/encode/BAAI/bge-m3 HTTP/1.1" 503 Service Unavailable` | Probes arriving before load completes — **expected** |
| 6 — Ready | `POST /v1/encode/BAAI/bge-m3 HTTP/1.1" 200 OK` | Model ready — safe to run sweeps |
| ✗ — Load failed | `POST /v1/encode/BAAI/bge-m3 HTTP/1.1" 502 Bad Gateway` | **Terminal failure** — do not keep waiting; see [502 Bad Gateway](#encode-returns-502-bad-gateway) |

If phase 2 appears without phase 3 within a few minutes, confirm the volume mount:
`-v sie-hf-cache:/app/.cache/huggingface` (see [Disk cache warning on first start](#disk-cache-warning-on-first-start)).

Poll until the model is ready:

```bash
until curl -sf -o /dev/null -X POST http://localhost:8720/v1/encode/BAAI/bge-m3 \
  -H "Content-Type: application/json" \
  -d '{"items":[{"text":"readiness probe"}]}'; do
  echo "SIE not ready yet — waiting 10s..."
  sleep 10
done
echo "SIE model ready"
```

Watch the container logs for:
```
Model 'BAAI/bge-m3' loaded successfully
```
—or the first **`200 OK`** on `POST /v1/encode/BAAI/bge-m3` in the access log (phase 6 above).

**Only run the server and smoke tests after the model is warm.**

---

## 4. Enable SIE in the server (Docker path)

After the SIE container is warm, tell the app to use it (default is off):

```bash
# .env
SIE_ENABLED=true
SIE_ENDPOINT=http://localhost:8720
```

When the **server runs in Docker** and SIE runs on the host, use:

```bash
SIE_ENDPOINT=http://host.docker.internal:8720
```

Restart the server after editing `.env`. With `SIE_ENABLED=false` (default), `GET /health`
returns `"sie":"disabled"` and sweeps default to local `all-MiniLM-L6-v2` instead of BGE-M3.

---

## Use SIE in a config

Use the ready-made example config for a full CLI pipeline sweep:

```bash
rag-params-finder run --config configs/example-mongodb-sie.yaml
```

See [`configs/example-mongodb-sie.yaml`](../../configs/example-mongodb-sie.yaml) — **80 runs** (bge-m3, stella-v5; all 5 chunking methods; dense/sparse/hybrid/cross-encoder). Prerequisites: reachable SIE gateway (`SIE_ENABLED=true`, `SIE_ENDPOINT`, `SIE_API_KEY` when required) or warm local Docker; `vector_index_1024` + `text_search_index` on Atlas.

Minimal inline snippet:

```yaml
embedding:
  provider: sie
  models:
    - bge-m3
    - stella-v5
    - splade-v3

retrieval:
  retrievers:
    - type: dense
    - type: hybrid
```

The 1024-dim vector index (`vector_index_1024`) is used for SIE models — the same as Voyage.
If you already created `vector_index_1024` for Voyage sweeps, no new index is needed.

---

## 6. Quick smoke test

With the model warm (step 3 complete) and the server running:

```bash
curl -s -X POST http://localhost:8001/api/v1/sweep \
  -H "Content-Type: application/json" \
  -d '{"topic":"machine learning","corpus":["RAG improves retrieval","vector search scales well"]}' \
  | python3 -m json.tool
```

Expected: HTTP 200 with `best_config`, `results`, and `experiment_id` in the response body.

---

## Known Issues and Workarounds

These are real problems encountered during development — not theoretical edge cases.

### `/health` returns 404

**Symptom:** `curl http://localhost:8720/health` returns `{"detail":"Not Found"}`.

**Cause:** SIE's liveness endpoint is `/healthz`, not `/health`.

**Fix:** Use `/healthz` (and `/readyz` for readiness).

---

### Encode returns 503 for minutes after container starts

**Symptom:** SIE access logs show lines like:

```
INFO: 192.168.65.1:21659 - "POST /v1/encode/BAAI/bge-m3 HTTP/1.1" 503 Service Unavailable
```

…repeatedly, even though `/healthz` returns `ok`.

**Cause:** Model is still downloading or loading into memory. Liveness (`/healthz`) and
model readiness are separate states. On Apple Silicon with `--platform linux/amd64`, 503s
can continue for **20–30+ minutes** on first run.

**Fix:** Wait and poll with the **encode probe** (step 3), not `/healthz`. Use the
`sie-hf-cache` volume to avoid re-downloads on restart.

**Not a 503:** If encode returns **`502 Bad Gateway`** or logs `MODEL_LOAD_FAILED` /
`Background writer channel closed`, the load has **failed terminally** — see
[502 Bad Gateway](#encode-returns-502-bad-gateway) (do not keep waiting for 503 to resolve).

---

### Encode fails with "Queue full: … cannot add … (limit: 512)"

**Symptom:** Dashboard run fails in the EMBEDDING phase with:

```
SIE unreachable or encode failed: Queue full: 362 items pending, cannot add 842 more (limit: 512)
```

**Cause:** The SIE gateway caps in-flight encode items at **512 per request**. A single
PDF can produce more chunks than that — e.g. the bundled Pell Grant PDF with `fixed` chunking
at `256+50` yields **842 chunks**. The server must shard encode calls into smaller batches;
without that, one embedding phase sends the full chunk list and hits the cap.

**Fix:** Restart the server so it picks up batching in `embed_documents_sie`, then
**resume** the failed experiment from the dashboard (or re-submit).

**Workarounds on an older server build:**

1. Use larger `chunk_sizes` (e.g. `[512]` only) to reduce chunk count below 512.
2. Run one experiment at a time — a second concurrent sweep adds queue pressure.
3. Restart the SIE container to drain a stuck queue: `docker restart sie-server`.

---

### Encode returns 502 Bad Gateway

**Symptom:** SIE access logs show:

```
INFO: 192.168.65.1:44324 - "POST /v1/encode/BAAI/bge-m3 HTTP/1.1" 502 Bad Gateway
```

**Cause:** In SIE, **502 means terminal model load failure** (`MODEL_LOAD_FAILED`) — the
HTTP server is up, but BGE-M3 could not be loaded on the worker. This is **not** warm-up
(503) and **will not resolve by waiting**. Common triggers:

- Corrupted or incomplete HuggingFace download (stale `.incomplete` blobs in the cache volume)
- Memory pressure or crash during weight deserialization (especially on Apple Silicon under
  `--platform linux/amd64`)
- Transient internal error marked `"permanent": true` by SIE

**Diagnose:**

```bash
docker logs sie-server 2>&1 | tail -50 | grep -iE 'MODEL_LOAD|failed|error|502'
```

Look for `Model 'BAAI/bge-m3' failed to load` or `Background writer channel closed`.

**Fix:** Same recovery as [Background writer channel closed](#background-writer-channel-closed-crash):

```bash
# 1. Clear stale partial downloads (if any)
docker exec sie-server sh -c \
  'rm -f /app/.cache/huggingface/hub/models--BAAI--bge-m3/blobs/*.incomplete \
         /app/.cache/huggingface/hub/.locks/models--BAAI--bge-m3/*.lock' 2>/dev/null || true

# 2. Restart container
docker restart sie-server

# 3. Poll encode until 200 (not 502/503)
until curl -sf -o /dev/null -X POST http://localhost:8720/v1/encode/BAAI/bge-m3 \
  -H "Content-Type: application/json" \
  -d '{"items":[{"text":"probe"}]}'; do sleep 10; done
```

If 502 recurs after restart, wipe the cache volume and re-download:

```bash
docker stop sie-server && docker rm sie-server
docker volume rm sie-hf-cache
# then re-run the docker run command from step 1
```

---

### Disk cache warning on first start

**Symptom:** Shortly after container start:

```
WARNING  sie_server.core.disk_cache: Failed to get disk stats for /app/.cache/huggingface/hub:
[Errno 2] No such file or directory: '/app/.cache/huggingface/hub'
```

**Cause:** SIE's disk-cache manager checks free space under `hub/` before HuggingFace has
created that subdirectory. On a **fresh** `sie-hf-cache` volume this path does not exist yet.
The volume mount targets `/app/.cache/huggingface`; HuggingFace creates `hub/` on first download.

**Fix:**

| Situation | Action |
|---|---|
| Warning once, then `Fetching N files...` in logs | **Ignore** — normal first-run behaviour |
| Warning only, no download progress, endless 503s | Confirm `-v sie-hf-cache:/app/.cache/huggingface` is set; optionally `docker exec sie-server mkdir -p /app/.cache/huggingface/hub` and restart |
| Warning + stuck `.incomplete` blob files (size unchanged >30 min) | Remove incomplete blobs and restart — see [Background writer channel closed](#background-writer-channel-closed-crash) |

Verify the volume is mounted:

```bash
docker inspect sie-server --format '{{range .Mounts}}{{.Destination}} <- {{.Name}}{{"\n"}}{{end}}'
# expect: /app/.cache/huggingface <- sie-hf-cache
```

---

### App `/health` shows `sie: reachable` but sweep fails or hangs

**Symptom:** `GET http://localhost:8001/health` returns `"sie":"reachable"` but
`POST /api/v1/sweep` errors or hangs for many minutes.

**Cause:** App health probes SIE `/healthz` only (process liveness). BGE-M3 may still be
loading (encode still returning 503). Additionally, `sie-sdk` retries for up to **900 seconds**
when encode is unavailable — a sweep submitted too early appears hung.

**Fix:** Complete the encode readiness poll (step 3) before submitting sweeps. Use:

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8720/v1/encode/BAAI/bge-m3 \
  -H "Content-Type: application/json" \
  -d '{"items":[{"text":"readiness probe"}]}'
# must print 200 before running POST /api/v1/sweep
```

---

### "Background writer channel closed" crash

**Symptom:** SIE container logs show a sequence like this (download starts, then fails
mid-way, then encode returns 502 while `/healthz` still returns `ok`):

```
Fetching 30 files:  60%|██████    | 18/30 [02:48<01:52,  9.38s/it]
ERROR    sie_server.core.registry: Background model load failed: BAAI/bge-m3
         (class=UNKNOWN, attempts=1, cooldown=permanent)
...
RuntimeError: Internal error: Internal Writer Error: Background writer channel closed
INFO:     192.168.65.1:44324 - "POST /v1/encode/BAAI/bge-m3 HTTP/1.1" 502 Bad Gateway
INFO:     127.0.0.1:58184 - "GET /healthz HTTP/1.1" 200 OK
```

**What it means:**

| Log fragment | Interpretation |
|---|---|
| `Fetching 30 files: 60%` | HuggingFace `snapshot_download` was in progress |
| `xet_get` / `hf_hub_download` in traceback | Failure while **writing** a weight file to disk (not auth) |
| `cooldown=permanent` | SIE will **not** auto-retry this load — restart required |
| `502` on encode + `200` on `/healthz` | Process alive, model **not** loaded |

**Cause:** Corrupted or interrupted HuggingFace download (common on Apple Silicon under
`--platform linux/amd64`), disk I/O pressure inside Docker, or stale `.incomplete` blobs
left from a prior failed run. **Waiting will not fix it** once `cooldown=permanent` appears.

**Root cause to check first:** if logs also show:

```
OSError: [Errno 28] No space left on device: '/tmp/tmp...'
```

…the HuggingFace download ran out of disk inside the container (often Docker Desktop's
**virtual disk limit**, not just host free space). The `Background writer channel closed`
error frequently follows this. See [No space left on device](#no-space-left-on-device-errno-28).

**Fix (try in order):**

**Step A — Clear partial downloads and restart** (if download failed part-way, e.g. at 60%):

```bash
docker exec sie-server sh -c \
  'rm -f /app/.cache/huggingface/hub/models--BAAI--bge-m3/blobs/*.incomplete \
         /app/.cache/huggingface/hub/.locks/models--BAAI--bge-m3/*.lock' 2>/dev/null || true
docker restart sie-server
# poll encode until HTTP 200 (see step 3)
```

**Step B — Full container + volume reset** (if Step A fails or 502/`cooldown=permanent` recurs):

```bash
docker stop sie-server && docker rm sie-server
docker volume rm sie-hf-cache

docker run -d \
  --name sie-server \
  -p 8720:8080 \
  -v sie-hf-cache:/app/.cache/huggingface \
  --platform linux/amd64 \
  -e HF_TOKEN=$HF_TOKEN \
  ghcr.io/superlinked/sie-server:latest-cpu-default
```

Confirm `HF_TOKEN` is set before Step B — downloads require HuggingFace read access.
Watch `docker logs -f sie-server` until `Fetching 30 files` completes **without** the
`Background writer channel closed` error, then poll encode to 200.

**Step C — If failures repeat at the same file percentage:** increase Docker Desktop memory
(≥ 8 GB recommended for BGE-M3 under amd64 emulation) and ensure ≥ 10 GB free disk for the
cache volume.

---

### No space left on device (Errno 28)

**Symptom:** During `Fetching N files...` or model load:

```
OSError: [Errno 28] No space left on device: '/tmp/tmpbta0hxaa'
```

Often followed by `Background writer channel closed`, `cooldown=permanent`, and **502** on
encode.

**Cause:** HuggingFace downloads large weight files via a temp file under `/tmp` inside the
container. BGE-M3 needs **several GB** for download + cache. On macOS, Docker Desktop uses a
**fixed virtual disk** (Settings → Resources → Disk image size) — host free space can look
fine while Docker's VM is full.

**Diagnose:**

```bash
# Host free space
df -h .

# Docker disk usage (images, volumes, build cache)
docker system df

# Inside the SIE container (if running)
docker exec sie-server df -h /tmp /app/.cache/huggingface
```

**Fix:**

1. **Free Docker disk** — prune unused data (review before `-a`):

```bash
docker system prune -f              # stopped containers, unused networks, dangling images
docker volume prune -f            # unused volumes only — skips sie-hf-cache if in use
docker builder prune -f           # build cache
```

2. **Increase Docker Desktop disk limit** — Docker Desktop → Settings → Resources →
   **Virtual disk limit** → set **≥ 64 GB** (BGE-M3 cache + image + temp files).

3. **Remove corrupt partial cache** then restart SIE:

```bash
docker stop sie-server && docker rm sie-server
docker volume rm sie-hf-cache   # only if you can re-download; needs HF_TOKEN

docker run -d \
  --name sie-server \
  -p 8720:8080 \
  -v sie-hf-cache:/app/.cache/huggingface \
  --platform linux/amd64 \
  -e HF_TOKEN=$HF_TOKEN \
  ghcr.io/superlinked/sie-server:latest-cpu-default
```

4. **Host cleanup** if `df -h` shows the Mac disk is full — remove old Docker images,
   clear `~/Library/Containers/com.docker.docker/` only via Docker Desktop settings (do not
   manually delete while Docker is running).

After freeing space, watch `docker logs -f sie-server` until `Fetching 30 files` reaches
**100%** without `Errno 28`, then poll encode to HTTP 200.

---

### `POST /api/v1/sweep` hangs for 15 minutes when SIE is down

**Symptom:** A sweep request hangs with no output for up to 900 seconds before returning an error.

**Cause:** `sie-sdk` has an internal retry budget of **900 seconds (15 minutes)** when it
cannot connect. This is an SDK design choice — the application has no way to short-circuit it.

**Fix (prevention):** Always confirm SIE is reachable before submitting a sweep:

```bash
curl http://localhost:8720/healthz   # → ok
```

If the container isn't up, start it and wait for the model (step 3) before submitting sweeps.

There is no in-flight cancellation once the SDK starts retrying. Kill the server process
and restart if needed.

---

### Port 8720 still in use / wrong process

**Symptom:** `curl http://localhost:8720/healthz` returns an unexpected response, or
connection refused even though Docker says the container is running.

**Cause:** Another process is bound to 8720, or the Docker port mapping did not apply
because the container was started without `-p 8720:8080`.

**Fix:**

```bash
# Check what is on 8720
lsof -i :8720

# Verify the SIE container is actually mapped
docker ps --filter name=sie-server --format "table {{.Names}}\t{{.Ports}}"
```

---

### SIE container not started by `start-services.sh`

**Symptom:** `./start-services.sh` starts the server and dashboard but SIE is not running.

**Cause:** SIE runs as a separate container outside the main Docker Compose stack — by design,
since it is a heavyweight external service (~3.8 GB) that can be shared across restarts.

**Fix:** Start SIE manually before running `./start-services.sh` (or before starting uvicorn manually).

---

### Docker Desktop becomes unresponsive after `start-services.sh`

**Symptom:** Docker Desktop hangs or stops responding on the second run of `start-services.sh`.

**Cause:** The script may have previously killed Docker port-proxy processes with `kill -9`.

**Fix:** Run `docker compose down` before re-running `start-services.sh`:

```bash
docker compose down
./start-services.sh
```

---

### Server container unhealthy (Atlas IP allowlist)

**Symptom:** `docker ps` shows the server container as `unhealthy` after ~2 minutes. Server
logs show `TLSV1_ALERT_INTERNAL_ERROR` when connecting to MongoDB.

**Cause:** The Docker container's egress IP differs from your host IP. Atlas Network Access
only allows your host IP — not the Docker NAT address.

**Fix:** Add the Docker egress IP to Atlas Network Access:

1. Check the egress IP: `curl https://api.ipify.org` from inside the container, or check
   the Atlas "Failed connections" log to see the rejected source IP.
2. Atlas UI → Security → Network Access → Add IP Address → paste the IP.
3. For local development, `0.0.0.0/0` (allow all) is acceptable if the cluster is private.

---

### `sie-sdk` websockets version pin blocks security upgrades

**Symptom:** `uv pip install` or dependency resolution fails with a conflict involving
`websockets`, `langchain`, or `langsmith`.

**Cause:** `sie-sdk` pins `websockets>=14,<15`. Some versions of `langsmith` require
`websockets>=15`. These cannot co-exist until `sie-sdk` updates its pin.

**Workaround:** Keep `langchain` / `langsmith` pinned to versions compatible with
`websockets<15`. See `pyproject.toml` for the current pinned ranges. If you need a newer
`langchain`, open an issue — the `sie-sdk` vendor controls the pin.

---

### NumPy 2.x ABI warning with `aim`

**Symptom:** Server starts but logs a warning like `_ARRAY_API not found` from torch.

**Cause:** The `aim` experiment logger installs NumPy 2.x; PyTorch was compiled against
NumPy 1.x. The warning is non-fatal — the server runs correctly — but indicates an ABI mismatch.

**Fix:** `pyproject.toml` pins `numpy<2`. If you manually install `aim` outside of `uv`,
ensure NumPy stays below 2.0.

---

## Aim experiment UI

Every sweep run (`POST /api/v1/sweep` and full pipeline runs) is logged to Aim via
`server/core/aim_logger.py`. Runs are stored in `./.aim` (gitignored).

### Start the UI (Docker — recommended)

Host `aim up` may fail on macOS with `cryptography` / OpenSSL errors
(`symbol not found: _BIO_ADDR_free`). Use the Docker helper instead:

```bash
./scripts/aim-ui.sh
# → http://localhost:43800
```

The script starts the `aim-ui` Compose profile, bind-mounts `./.aim` (shared with the
server container), and migrates existing runs from the server container on first use.

```bash
./scripts/aim-ui.sh --stop   # stop the UI container
```

### Verify logging

```bash
# Trigger a sweep (SIE must be warm if using bge-m3)
curl -X POST http://localhost:8001/api/v1/sweep \
  -H "Content-Type: application/json" \
  -d '{"topic":"test","corpus":["chunk one","chunk two"]}'

# Check run count in the local repo
python3 -c "import sqlite3; c=sqlite3.connect('.aim/run_metadata.sqlite'); print(c.execute('SELECT count(*) FROM run').fetchone()[0])"
```

Open http://localhost:43800 after `./scripts/aim-ui.sh` — you should see runs with
`model_name`, `model_source`, `retrieval_method`, `score`, `topic`, and `experiment_id`.

---

## Diagnostics Cheat Sheet

```bash
# Is the SIE container running?
docker ps --filter name=sie-server

# Is the process alive?
curl http://localhost:8720/healthz

# Is the model ready? (200 = yes, 503 = still loading)
curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8720/v1/encode/BAAI/bge-m3 \
  -H "Content-Type: application/json" \
  -d '{"items":[{"text":"test"}]}'

# Container logs (model load progress)
docker logs -f sie-server

# Disk used by the HF cache volume
docker system df -v | grep sie-hf-cache

# Port in use?
lsof -i :8720

# Python: which SIE base URL will the server use?
python3 -c "import os; print(os.getenv('SIE_ENDPOINT', 'http://localhost:8720'))"
```

---

## First-Run Setup Checklist

### Path A — Remote gateway (no Docker)

```
[ ] SIE_ENABLED=true, SIE_ENDPOINT, SIE_API_KEY in server .env
[ ] curl -H "Authorization: Bearer $SIE_API_KEY" "$SIE_ENDPOINT/healthz" → ok
[ ] vector_index_1024 + text_search_index on Atlas chunks collection
[ ] Server running: uvicorn server.main:app --reload --port 8001
[ ] GET http://localhost:8001/health shows sie: reachable
[ ] rag-params-finder run --config configs/example-mongodb-sie.yaml --detach
```

### Path B — Self-hosted Docker

```
[ ] Docker Desktop installed and running
[ ] HF_TOKEN exported: export HF_TOKEN=hf_...
[ ] SIE container started (with --platform linux/amd64 on Apple Silicon)
[ ] curl http://localhost:8720/healthz → ok
[ ] Model warm-up poll passes (HTTP 200 from POST /v1/encode/BAAI/bge-m3)
[ ] SIE_ENABLED=true, SIE_ENDPOINT=http://localhost:8720 in server .env
[ ] vector_index_1024 + text_search_index on Atlas
[ ] GET http://localhost:8001/health shows sie: reachable
[ ] Smoke test: curl POST /api/v1/sweep returns HTTP 200
```

---

## Related docs

- [Getting Started](getting-started.md) — install, configure, first experiment
- [MongoDB Setup](mongodb-setup.md) — Atlas vector search indexes
- [Troubleshooting](troubleshooting.md) — general error fixes
- [Configuration reference](configuration.md) — full YAML reference including `provider: sie`
