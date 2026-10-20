# Release Notes -- v0.17.2

> Released: 2026-10-20

### Changed

- **The memory, diary, filetree and connectome adapters are tested against
  the real upstream classes.** Their `_load()` had only mocked tests, which
  accept any constructor arguments, so a signature change upstream could
  ship unseen. Four tests in `tests/test_adapters.py` now build a real
  `MemoryKG`, `DiaryKG`, `FileTreeKG` and `ConnectomeKG`; a stale argument
  added to the memory adapter fails the new test and leaves the 16 mocked
  ones green. `memory-kg`, `diary-kg`, `ftree-kg` and `connectome-kg` join
  the dev group, at their extras' floors, so CI has them.
- **Every backed adapter is now tested against its real class.** The
  genealogy, metabo, agent, swift, typescript and vault adapters join the
  four above. `metabo-kg` is not on PyPI and comes from git at tag
  `v0.17.0`; the rest come from PyPI. The metakg test fails on the stale
  `lancedb_dir=` argument that once shipped as a `TypeError`. The agent
  test points `agent_kg.graph._PROFILE_BASE` at a temporary directory, so
  nothing touches `~/.kgrag/profiles`, and a mocked agent test now blocks
  `agent_kg.graph` as well as `agent_kg`, which it needs once the package
  is installed.
- Relocked onto `doc-kg` 0.28.0, `pycode-kg` 0.28.2 and `vault-kg` 0.5.0.
  Floors are unchanged.
- Dependencies refreshed to clear 22 Dependabot alerts (#63): pyjwt 2.15.1,
  urllib3 2.8.0, mcp 1.30.0 and virtualenv 21.14.11 (dev), all transitive.

### Fixed

- **PDF support in `[all]` and `[ingest]` on a fresh install.** pymupdf4llm
  2.0 (2026-10-16) is an empty placeholder: its code now ships inside the
  pymupdf 2.0 wheel. `[all]` named `pymupdf4llm>=1.28.2` directly, and
  `[ingest]` floored `kgmodule-utils[ingest]>=0.27.0`, whose own extra
  declared the same; both resolved to no PDF code. `[all]` now declares
  `pymupdf>=2.0` and `[ingest]` floors `kgmodule-utils[ingest]>=0.27.1`.
  The lock moves to kgmodule-utils 0.27.1, doc-kg 0.28.1, diary-kg 0.100.1
  and pymupdf 2.0.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
