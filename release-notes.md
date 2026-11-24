# Release Notes - v0.19.2

> Released: 2026-11-23

### Security

- **kgmodule-utils 0.30.2 is the floor** for the base install and
  `[ingest]` (was 0.30.0). In kgmodule-utils 0.30.0 and 0.30.1 the default
  `omlx` synthesis backend sent `OPENAI_API_KEY` to the oMLX server
  whenever `VLLM_API_KEY` was unset, so `kgrag synthesize` could pass the
  OpenAI key to it. 0.30.2 sends each backend only its own key.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
