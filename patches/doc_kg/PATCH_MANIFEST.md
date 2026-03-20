# Doc_KG Patches

Canonical location for doc_kg customizations. Apply these when doc_kg is installed into `.venv/src/doc_kg/`.

## Patches

### 1. `embedder-nomic.patch`

**Purpose:** Switch doc_kg's default embedding model from `all-mpnet-base-v2` to `nomic-embed-text`

**Why:**
- `nomic-embed-text` is document-optimized (prose, narrative)
- 768 dims provides "strong rich embedding"
- Better semantic capture than `all-mpnet-base-v2`
- Symmetry with CodeKG choice (BGE-small for code, nomic for text)

**Files affected:** `src/doc_kg/dockg.py` (line 58)

**Apply:**
```bash
cd /home/user/KGRAG
patch -p0 < patches/doc_kg/embedder-nomic.patch
```

**Revert:**
```bash
patch -p0 -R < patches/doc_kg/embedder-nomic.patch
```

**After applying:**
1. Delete `.dockg/lancedb/` to force re-embedding
2. Rebuild: `dockg build --repo . --wipe`
3. Verify: `export DOCKG_MODEL && env | grep DOCKG` should show `nomic-embed-text`

---

## Architecture

**Embedder Strategy (2026-03-20):**

| KG | Model | Dims | Rationale |
|----|----|----|----|
| **CodeKG** | `BAAI/bge-small-en-v1.5` | 384 | Code-optimized (identifiers, structure) |
| **DocKG** | `nomic-embed-text` | 768 | Document-optimized (prose, narrative) |
| **DiaryKG** | `nomic-embed-text` | 768 | Inherits from DocKG (diary prose) |
| **AgentKG** | `BAAI/bge-small-en-v1.5` | 384 | Conversation turns (structure + meaning) |

---

## Applying Patches to Venv

After `poetry install`, before first use:

```bash
cd /home/user/KGRAG
# Apply all pending patches
for patch in patches/doc_kg/*.patch; do
  patch -p0 < "$patch" && echo "✓ Applied $(basename $patch)"
done
```

Or manually (if patch tool unavailable):

```bash
# Apply embedder-nomic.patch manually:
# Edit .venv/src/doc_kg/src/doc_kg/dockg.py line 58
# Change: DEFAULT_MODEL: str = os.environ.get("DOCKG_MODEL", "all-mpnet-base-v2")
# To:     DEFAULT_MODEL: str = os.environ.get("DOCKG_MODEL", "nomic-embed-text")
```

---

## Adding New Patches

When making changes to installed packages:

1. **Create patch file:**
   ```bash
   cd /home/user/KGRAG
   diff -u .venv/src/doc_kg/src/doc_kg/dockg.py.orig \
           .venv/src/doc_kg/src/doc_kg/dockg.py > patches/doc_kg/my-feature.patch
   ```

2. **Document in PATCH_MANIFEST.md** (this file)

3. **Commit:**
   ```bash
   git add patches/doc_kg/
   git commit -m "Add doc_kg patch: my-feature"
   ```

4. **Test:** Verify `patch -p0 --dry-run < patches/doc_kg/my-feature.patch` applies cleanly

---

## Status

| Patch | Status | Date Applied | Notes |
|-------|--------|--------------|-------|
| `embedder-nomic.patch` | Ready to apply | — | Awaiting dockg rebuild |

