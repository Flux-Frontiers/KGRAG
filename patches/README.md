# KGRAG Patches

Canonical directory for customizations to vendored dependencies (doc_kg, diary_transformer, etc.).

**Why patches?** When dependencies are installed into `.venv/src/`, they should be customized *once* and the patches tracked in version control. This way:
- Patches survive `rm -rf .venv && poetry install`
- Changes are visible in git history
- Multiple developers apply the same patches consistently

---

## Structure

```
patches/
├── README.md              ← This file
├── doc_kg/
│   ├── PATCH_MANIFEST.md  ← Doc_KG patch registry
│   ├── embedder-nomic.patch
│   └── ...
└── diary_transformer/     ← Future patches
```

---

## Quick Apply

After `poetry install`, apply all patches:

```bash
cd /home/user/KGRAG

# Dry run (safe):
for patch in patches/*/*.patch; do
  echo "=== $patch ==="
  patch -p0 --dry-run < "$patch"
done

# Actually apply:
for patch in patches/*/*.patch; do
  echo "Applying $patch ..."
  patch -p0 < "$patch" || echo "FAILED: $patch"
done
```

Or use `apply-patches.sh` (if created):

```bash
./scripts/apply-patches.sh
```

---

## Patch Workflow

### Creating a Patch

1. **Make the change** in `.venv/src/PACKAGE/...`
2. **Backup original:**
   ```bash
   cp .venv/src/doc_kg/src/doc_kg/dockg.py .venv/src/doc_kg/src/doc_kg/dockg.py.orig
   ```
3. **Generate patch:**
   ```bash
   diff -u .venv/src/doc_kg/src/doc_kg/dockg.py.orig \
           .venv/src/doc_kg/src/doc_kg/dockg.py > patches/doc_kg/feature-name.patch
   ```
4. **Test patch:**
   ```bash
   patch -p0 --dry-run < patches/doc_kg/feature-name.patch
   ```
5. **Document** in `patches/doc_kg/PATCH_MANIFEST.md`
6. **Commit:**
   ```bash
   git add patches/doc_kg/
   git commit -m "Add doc_kg patch: feature-name (reason)"
   ```

### Reverting a Patch

```bash
patch -p0 -R < patches/doc_kg/feature-name.patch
```

### Testing a Patch on Fresh Venv

```bash
poetry install
for patch in patches/*/*.patch; do
  patch -p0 < "$patch" || exit 1
done
# Verify patches applied correctly
```

---

## Current Patches

| Package | Patch | Purpose | Status |
|---------|-------|---------|--------|
| **doc_kg** | `embedder-nomic.patch` | Switch to nomic-embed-text for document search | Ready |
| — | — | — | — |

---

## Rationale: Embedder Strategy (2026-03-20)

All KGs should use domain-optimized embedders:

- **CodeKG:** `BAAI/bge-small-en-v1.5` (384-dim) — Code is dense, structured, identifier-heavy
- **DocKG:** `nomic-embed-text` (768-dim) — Documents are prose, narrative, flowing text
- **DiaryKG:** `nomic-embed-text` (768-dim) — Diary entries are narrative (inherits DocKG)
- **AgentKG:** `BAAI/bge-small-en-v1.5` (384-dim) — Conversation turns are structured + concise

This divergence from "one embedder for all" is intentional: embeddings are only comparable *within* the same model/space, and domain-specific models perform better on their intended domain.

---

## Notes

- Patches use unified diff format (`patch -p0`)
- Always test with `--dry-run` before applying
- Document every patch in the relevant `PATCH_MANIFEST.md`
- Commit patches alongside any documentation updates
- If a patch fails to apply to a new venv version, it means that code changed upstream — review the new code and create a new patch

