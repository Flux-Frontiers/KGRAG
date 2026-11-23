# Release Notes - v0.19.1

> Released: 2026-11-23

### Security

- **imagewright 0.2.0 is the floor** in `[imagine]`, `[imagine-local]` and
  `[all]`. In imagewright 0.1.0 the `ImageConfig` repr includes `api_key`,
  so printing or logging a resolved config exposes the OpenAI key. 0.2.0
  keeps the key out of the repr.

### Changed

- **`docs/FLEET_VERSIONS.md` is regenerated** for kg-rag 0.19.0,
  kgmodule-utils 0.31.0 and the fleet's new image package, imagewright 0.1.0.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
