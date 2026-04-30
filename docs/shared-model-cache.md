# Shared Model Cache — Downstream Integration Guide

KGRAG's `ModelCoordinator` downloads embedding models once to `~/.kgrag/models/` and
sets environment variables so downstream KG libraries reuse that cache instead of
downloading independently. **No adaptor interfaces change.**

## How It Works

1. `kgrag models download` (or `ModelCoordinator.ensure()`) downloads a model to
   `~/.kgrag/models/<org>/<model>/` via `huggingface_hub.snapshot_download()`.
2. Before any adaptor loads, `ModelCoordinator.apply_env()` sets:
   ```
   KGRAG_MODEL_DIR  = ~/.kgrag/models/
   CODEKG_MODEL_DIR = ~/.kgrag/models/
   DOCKG_MODEL_DIR  = ~/.kgrag/models/
   DIARYKG_MODEL_DIR = ~/.kgrag/models/
   METABOKG_MODEL_DIR = ~/.kgrag/models/
   ```
3. Each downstream library checks for its env var and uses it as the model cache
   root. If the env var is unset (standalone usage), the library falls back to its
   own default path.

## Changes Per Repo

### pycode-kg

Wherever the model is downloaded/loaded (e.g. `embeddings.py`, `model.py`), replace
the hardcoded cache path with an env-var-aware helper:

```python
import os
from pathlib import Path

_DEFAULT_MODEL_DIR = Path.home() / ".codekg" / "models"


def _model_dir() -> Path:
    env = os.environ.get("CODEKG_MODEL_DIR")
    return Path(env) if env else _DEFAULT_MODEL_DIR
```

Then use `_model_dir()` when computing the local path:

```python
model_path = _model_dir() / repo_id.replace("/", os.sep)
if not model_path.exists():
    snapshot_download(repo_id, local_dir=str(model_path),
                      local_dir_use_symlinks=False)
embedder = SentenceTransformer(str(model_path), trust_remote_code=True)
```

~5 lines changed. No API changes, no new dependencies.

### doc-kg

Identical pattern, different env var:

```python
_DEFAULT_MODEL_DIR = Path.home() / ".dockg" / "models"


def _model_dir() -> Path:
    env = os.environ.get("DOCKG_MODEL_DIR")
    return Path(env) if env else _DEFAULT_MODEL_DIR
```

### diary-kg

```python
_DEFAULT_MODEL_DIR = Path.home() / ".diarykg" / "models"


def _model_dir() -> Path:
    env = os.environ.get("DIARYKG_MODEL_DIR")
    return Path(env) if env else _DEFAULT_MODEL_DIR
```

### metabo-kg

```python
_DEFAULT_MODEL_DIR = Path.home() / ".metabokg" / "models"


def _model_dir() -> Path:
    env = os.environ.get("METABOKG_MODEL_DIR")
    return Path(env) if env else _DEFAULT_MODEL_DIR
```

## Changes in KGRAG

Add `DIARYKG_MODEL_DIR` and `METABOKG_MODEL_DIR` to `ModelCoordinator.export_env()`
in `src/kg_rag/model_coordinator.py`:

```python
def export_env(self) -> dict[str, str]:
    return {
        "KGRAG_MODEL_DIR": str(self._model_dir),
        "CODEKG_MODEL_DIR": str(self._model_dir),
        "DOCKG_MODEL_DIR": str(self._model_dir),
        "DIARYKG_MODEL_DIR": str(self._model_dir),
        "METABOKG_MODEL_DIR": str(self._model_dir),
    }
```

## Summary

| Repo | Env Var | Change Size |
|------|---------|-------------|
| pycode-kg | `CODEKG_MODEL_DIR` | ~5 lines |
| doc-kg | `DOCKG_MODEL_DIR` | ~5 lines |
| diary-kg | `DIARYKG_MODEL_DIR` | ~5 lines |
| metabo-kg | `METABOKG_MODEL_DIR` | ~5 lines |
| KGRAG | `export_env()` | 2 lines |

## Behavior

- **With KGRAG**: env vars are set, all libraries share `~/.kgrag/models/`. Model
  downloaded once, used everywhere.
- **Standalone**: env vars are unset, each library uses its own default cache path
  and downloads independently. Zero breakage.
