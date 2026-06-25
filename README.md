> **Part of AgentSave** — This is the self-hosted backend component of [AgentSave](https://github.com/aks-builds/agentsave), the AI agent cost-efficiency platform. Use it only if you want a local dashboard to track your agent runs and token savings. The SDK ([agentsave](https://github.com/aks-builds/agentsave)) works independently without this backend — you do not need this repo just to use the SDK.

# agentsave-dashboard — Self-Hosted Dashboard Backend

[![CI](https://github.com/aks-builds/agentsave-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/aks-builds/agentsave-dashboard/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/agentsave-dashboard.svg)](https://pypi.org/project/agentsave-dashboard/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

> A FastAPI + SQLite backend that receives telemetry from the AgentSave SDK and exposes cost, token, and run metrics over a local HTTP API. Runs entirely on your machine — no cloud account required.

---

## What it does

- Receives run telemetry from the `agentsave` SDK via `POST /api/events`
- Stores per-run data (framework, model, tokens before/after, task success) in a local SQLite database
- Serves aggregated metrics, daily token buckets, run history, and billing/tier information over a REST API
- Validates RS256-signed JWT license keys offline against a bundled public key — no license server call, no internet required
- Enforces data retention windows per tier (7 days on Free, 90 days on Pro, 365 days on Enterprise)
- Generates a unique `ask-xxx` API key on first run and prints it once so you can connect the SDK

---

## Quick Start

### 1. Install

```bash
pip install agentsave-dashboard
```

### 2. Start the server

```bash
agentsave-dashboard serve --host 127.0.0.1 --port 8000
```

On first run the server creates `~/.agentsave-dashboard/data.db`, generates an API key, and prints it to the terminal:

```
Your AgentSave Dashboard API key (shown once):

  ask-a1b2c3d4e5f6...

Run: agentsave login --dashboard-url http://127.0.0.1:8000 --api-key ask-a1b2c3d4...
```

### 3. Connect the SDK

In your project — wherever you installed `agentsave` — run:

```bash
agentsave login --dashboard-url http://127.0.0.1:8000 --api-key ask-a1b2c3d4...
```

After this, every agent run instrumented with `agentsave` will POST its telemetry to your local dashboard automatically.

### 4. (Optional) Activate a license key

If you have a Pro or Enterprise JWT license key, pass it at startup:

```bash
agentsave-dashboard serve --license-key <your-JWT>
```

The key is stored in the local database; subsequent restarts without `--license-key` will use the stored key.

---

## API Reference

All endpoints except `/api/health` require `Authorization: Bearer <api-key>`.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/health` | None | Returns `{"status":"ok","version":"0.1.0"}` |
| `POST` | `/api/events` | Bearer | Ingest a run event from the SDK |
| `GET` | `/api/runs` | Bearer | Paginated run history with computed `reduction_pct` |
| `GET` | `/api/metrics` | Bearer | Aggregate stats: total runs, tokens saved, cost saved, success rate, breakdown by framework |
| `GET` | `/api/tokens` | Bearer | Daily token buckets; accepts `?window=Nd` (e.g. `?window=30d`, default `30d`) |
| `GET` | `/api/billing` | Bearer | Current tier, features, seat count, and license expiry from the stored JWT |

### `POST /api/events` payload

```json
{
  "run_id": "unique-run-identifier",
  "framework": "langchain",
  "model_name": "gpt-4o",
  "tokens_before": 4200,
  "tokens_after": 3100,
  "task_success": true,
  "timestamp": "2026-06-25T10:00:00Z"
}
```

### `GET /api/runs` query parameters

| Parameter | Default | Range |
|-----------|---------|-------|
| `page` | `1` | — |
| `per_page` | `50` | 1–200 |

### `GET /api/metrics` response shape

```json
{
  "total_runs": 1042,
  "total_tokens_saved": 1280000,
  "total_tokens_before": 4800000,
  "reduction_pct": 26.67,
  "total_cost_saved_usd": 3.84,
  "success_rate": 0.97,
  "by_framework": {
    "langchain": { "runs": 600, "tokens_saved": 720000 },
    "autogen":   { "runs": 442, "tokens_saved": 560000 }
  }
}
```

---

## License Tiers

Tiers are encoded in RS256-signed JWTs issued by AgentSave. The public key is bundled in the package; validation is fully offline. An expired or invalid token silently falls back to Free.

| Feature | Free | Pro | Enterprise |
|---------|------|-----|------------|
| Run history | 7 days | 90 days | 365 days |
| Unlimited projects | No | Yes | Yes |
| Webhook alerts | No | Yes | Yes |
| CSV export | No | Yes | Yes |
| SSO / SAML | No | No | Yes |
| Audit logs | No | No | Yes |
| InferRoute integration | No | No | Yes |
| Seats | 1 | Per license | Per license |

The `GET /api/billing` endpoint returns the full feature set and expiry date for the active license.

---

## Configuration

| CLI flag | Environment variable | Default | Description |
|----------|----------------------|---------|-------------|
| `--host` | — | `127.0.0.1` | Interface to bind |
| `--port` | — | `8000` | Port to listen on |
| `--license-key` | — | — | RS256 JWT to activate Pro or Enterprise tier |
| — | `AGENTSAVE_TEST_MODE` | unset | Set to `1` to mount test-only routes and use an in-memory DB |

The database is stored at `~/.agentsave-dashboard/data.db`. There is no other configuration file.

---

## Architecture

```
agentsave SDK  ──POST /api/events──►  agentsave-dashboard (FastAPI)
                                              │
                              ┌───────────────┼───────────────┐
                              ▼               ▼               ▼
                          runs table    config table    api_keys table
                              │               │
                              ▼               ▼
                         aggregator      resolve_tier()
                         (metrics,       (JWT decode,
                          tokens,         RS256 verify,
                          billing)        feature flags)
                              │
                              ▼
                    GET /api/metrics, /api/runs,
                    /api/tokens, /api/billing
                              │
                              ▼
                    agentsave-ui  (separate repo)
```

**Key design choices:**

- **No cloud dependency.** License keys are RS256 JWTs verified against a public key bundled in the package. The server never makes an outbound network call.
- **SQLite only.** Designed for single-user, self-hosted use. No PostgreSQL or external database required.
- **API key security.** Keys are stored as SHA-256 hashes; the plaintext is shown exactly once on first boot and never stored.
- **Retention enforcement.** A background task at startup deletes runs older than the tier's `history_days` limit.

---

## Running the Tests

```bash
pip install -e ".[dev]"
AGENTSAVE_TEST_MODE=1 pytest tests/ -q
```

The test suite uses isolated per-test SQLite databases (temporary files, not `:memory:`, so async tests share state correctly within a test). 26 tests cover auth, billing, database schema, endpoints, license validation, metrics aggregation, and retention.

CI runs the full suite on Python 3.11, 3.12, and 3.13 on every push and pull request.

---

## Contributing

1. Fork the repository and create a feature branch
2. Install dev dependencies: `pip install -e ".[dev]"`
3. Run the tests before and after your change: `AGENTSAVE_TEST_MODE=1 pytest tests/ -q`
4. Open a pull request against `main`

The CI badge at the top of this file must stay green. A failing matrix build blocks merge.

---

## Related Repos

| Repo | Purpose |
|------|---------|
| [aks-builds/agentsave](https://github.com/aks-builds/agentsave) | Python SDK — the core product (`pip install agentsave`) |
| [aks-builds/agentsave-dashboard](https://github.com/aks-builds/agentsave-dashboard) | This repo — self-hosted dashboard backend |
| [aks-builds/agentsave-ui](https://github.com/aks-builds/agentsave-ui) | Frontend UI for the dashboard |
| [aks-builds/agentsave-inferroute](https://github.com/aks-builds/agentsave-inferroute) | Intelligent model routing (Enterprise tier) |

---

## License

MIT — see [LICENSE](LICENSE).
