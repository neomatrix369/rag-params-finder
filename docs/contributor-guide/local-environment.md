# Local Environment

![MongoDB](https://img.shields.io/badge/MongoDB_Atlas-47A248?logo=mongodb&logoColor=white)
![Voyage AI](https://img.shields.io/badge/Voyage_AI-FF6B6B)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)

Internal notes for local setup, debugging, and maintenance. Not required for basic contribution — see [development.md](development.md) for the standard dev workflow.

---

## 🗄️ MongoDB Atlas — Full Setup Details

### Connection String Format

```
mongodb+srv://<username>:<password>@<cluster>.mongodb.net/<database>?retryWrites=true&w=majority&appName=<app-name>
```

### Atlas UI Steps (one-time)

1. [cloud.mongodb.com](https://cloud.mongodb.com/) → create a free cluster (M0)
2. **Database Access** → create user with read/write permissions
3. **Network Access** → add your IP or `0.0.0.0/0` for local dev
4. **Connect → Compass** → copy the SRV URI into `MONGODB_URI` in `.env`

### Vector Index Creation

See [getting-started.md](../user-guide/getting-started.md#2-create-the-atlas-vector-index) for the full JSON index definitions. Index creation takes ~1–2 minutes in the Atlas UI. The server will fail vector queries until the index is ready.

### Checking Index Status

Atlas UI → Browse Collections → `chunks` collection → **Search Indexes** tab. Status shows `ACTIVE` when ready.

### Atlas Full Text Search Index (sparse/hybrid retrieval)

Required for `sparse` and `hybrid` retrieval methods. Create once in the Atlas UI:

1. Same **Search Indexes** tab → **Create Search Index** → JSON Editor
2. Name: `text_search_index`

```json
{
  "mappings": {
    "dynamic": false,
    "fields": {
      "text": [{ "type": "string" }],
      "experiment_id": [{ "type": "token" }],
      "embedding_model": [{ "type": "token" }]
    }
  }
}
```

The `text_search_index`, `vector_index_384`, and `vector_index_1024` all coexist on the same `chunks` collection. Skip this index if you only use `dense` retrieval.

---

## 🤖 Voyage AI Setup

1. Sign up at [dash.voyageai.com](https://dash.voyageai.com)
2. Navigate to **API Keys** → create new key
3. Copy the `vo-...` key into `.env` as `VOYAGE_API_KEY`

Check usage and rate limits at [dash.voyageai.com/usage](https://dash.voyageai.com/usage).

---

## 🔑 Full .env Reference

```bash
# MongoDB Atlas (REQUIRED)
MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/rag_params_finder?retryWrites=true&w=majority

# Voyage AI (OPTIONAL — only if using Voyage models)
VOYAGE_API_KEY=vo-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Server URL (used by CLI, default is localhost:8001)
SERVER_URL=http://localhost:8001

# Rate limits (Voyage only — set based on your tier)
VOYAGE_RPM_LIMIT=300
VOYAGE_TPM_LIMIT=1000000

# Optional — stored in experiment metadata / dashboard (“Recover on Boot”); no runtime retry on boot yet (planned: docs/slices/SLICE-10-RUN-RECOVERY.md — boot = INTERRUPTED only).
RECOVER_ON_BOOT=false

# Logging
LOG_LEVEL=INFO   # DEBUG for verbose output
```

Slice 10 *(planned)* documents CLI/API recovery and boot semantics: [`SLICE-10-RUN-RECOVERY.md`](../slices/SLICE-10-RUN-RECOVERY.md).

**Never commit `.env` to git** — it is in `.gitignore`.

---

## 🐛 Debugging Pipeline Failures

### Check server logs

```bash
# Terminal running uvicorn — look for phase transitions and errors
# Filter for relevant phases:
tail -f server.log | grep -i "mongo\|store\|chunk\|embed"
```

### Check run status in MongoDB shell (Atlas UI)

```javascript
// Atlas UI → Collections → run_status
db.run_status.find({run_id: "abc123"})
```

### Common failure points by phase

| Phase | Common cause |
|---|---|
| PARSING | Corrupt PDF, unsupported format |
| EMBEDDING | Voyage API key invalid, rate limit hit |
| STORING | MongoDB connection lost, index not created |
| QUERYING | Vector index not ready, dimension mismatch |

### Error handling modes

- `on_error: continue` — Failed run is logged; other runs continue
- `on_error: stop` — First failure halts the entire experiment

---

## 🗄️ MongoDB Query Patterns

### Get all experiments

```javascript
db.experiments.find({}, {_id: 0}).sort({created_at: -1})
```

### Get experiment with all runs

```javascript
const exp = db.experiments.findOne({experiment_id: "abc123"})
const runs = db.run_status.find({experiment_id: "abc123"}).toArray()
```

### Full cleanup (no cascade delete)

```javascript
const exp_id = "abc123"
db.experiments.deleteOne({experiment_id: exp_id})
db.run_status.deleteMany({experiment_id: exp_id})
db.chunks.deleteMany({experiment_id: exp_id})
db.results.deleteMany({experiment_id: exp_id})
```

---

## ⚡ Performance Notes

### Embedding speed

| Provider | Speed | Notes |
|---|---|---|
| Local (`all-MiniLM-L6-v2`) | ~50 chunks/sec on M1 CPU | No API latency; first run downloads model |
| Voyage (`voyage-3.5-lite`) | ~1000 chunks/min | API rate-limited; free tier is 1M TPM |

### MongoDB Atlas free tier limits

- **M0**: 512 MB storage
- 36-run sweep × 1,000 chunks × 1,024-dim × 4 bytes ≈ **147 MB** — fits comfortably
- Upgrade to M2 ($9/month) when storage exceeds 400 MB

### Monitoring storage

Atlas UI → **Metrics → Storage** — alert when approaching 400 MB (M0 limit is 512 MB).

Local HuggingFace cache:
```bash
du -sh ~/.cache/huggingface/hub
```

---

## 🔒 Security Notes

### Never commit

- `.env` files
- MongoDB connection strings
- Voyage API keys
- Any credentials

### Check before committing

```bash
git diff --cached | grep -i "mongodb\|voyage\|api_key"
```

### If a secret is accidentally committed

1. Rotate the credential immediately (invalidate the old key/password)
2. Remove from git history: use `git filter-branch` or [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)

### Server log safety

Never log full API keys. If needed for debugging, log only first/last 4 characters:
```python
logger.debug(f"API key: {api_key[:4]}...{api_key[-4:]}")
```

---

## 🔧 Maintenance

### Clearing old experiments

```javascript
// Delete experiments older than 30 days
const cutoff = new Date()
cutoff.setDate(cutoff.getDate() - 30)

const oldIds = db.experiments.find(
  {created_at: {$lt: cutoff}},
  {experiment_id: 1}
).toArray().map(e => e.experiment_id)

oldIds.forEach(id => {
  db.experiments.deleteOne({experiment_id: id})
  db.run_status.deleteMany({experiment_id: id})
  db.chunks.deleteMany({experiment_id: id})
  db.results.deleteMany({experiment_id: id})
})
```

Planned: `rag-params-finder cleanup --older-than 30d` CLI command.
