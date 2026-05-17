# Release Notes - v0.7.4

> Released: 2026-05-17

## Added

- **`HANDLER_SECRET` auth** (`runpod/handler.py`) - optional shared secret;
  requests must include `{"secret": "<value>"}` or receive `{"error": "unauthorized"}`.
  Exposed as a Hub env var UI field in `.runpod/hub.json`.

## Changed

- **`SentenceTransformerEmbedder`** (`src/kg_rag/_embedders.py`) - pass
  `show_progress_bar=False` to all `encode()` calls, eliminating tqdm batch
  progress bars from logs.
- **`runpod/handler.py`** - replace Unicode ellipsis and em-dash chars with
  plain ASCII; remove tqdm monkeypatch (no longer needed).
- **`runpod/.env.example`** - document `HANDLER_SECRET` variable.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
