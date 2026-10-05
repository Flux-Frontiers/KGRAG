# Fleet versions and pins

*Generated 2026-10-05 by `scripts/versions_snapshot.py` in the fleet's private
coordination repo, with its private repos left out. Do not hand-edit; it is
regenerated there and copied here.*

This snapshot covers the two things that go stale silently: what version each
repo currently declares itself as, and whether every consumer's floor on a fleet
package has caught up to it.

## Current versions

| Repo | Package | Version | License |
|------|---------|---------|---------|
| `KG_utils` | `kgmodule-utils` | 0.26.0 | Elastic-2.0 |
| `Metabo_kg` | `metabo-kg` | 0.17.0 | Elastic-2.0 |
| `agent_kg` | `agent-kg` | 0.12.1 | Elastic-2.0 |
| `connectome_kg` | `connectome-kg` | 0.8.1 | Elastic-2.0 |
| `corpus_pepys` | `corpus-pepys` | 0.6.0 | Elastic-2.0 |
| `diary_kg` | `diary-kg` | 0.100.0 | Elastic-2.0 |
| `doc_kg` | `doc-kg` | 0.27.0 | Elastic-2.0 |
| `ftree_kg` | `ftree-kg` | 0.17.0 | Elastic-2.0 |
| `genealogy_kg` | `genealogy-kg` | 0.2.2 | Elastic-2.0 |
| `gutenberg_kg` | `gutenberg-kg` | 1.26.0 | Elastic-2.0 |
| `kgrag` | `kg-rag` | 0.17.0 | Elastic-2.0 |
| `knowledge_press` | `-` | 1.28.1 | - |
| `memory_kg` | `memory-kg` | 0.12.0 | Elastic-2.0 |
| `proteusPy` | `proteuspy` | 0.100.5 | BSD-3-Clause |
| `pycode_kg` | `pycode-kg` | 0.28.1 | Elastic-2.0 |
| `pypdb2pov` | `pypdb2pov` | 0.1.1 | BSD-3-Clause |
| `quiltwright` | `quiltwright` | 0.16.0 | BSD-3-Clause |
| `satprint` | `satprint` | 0.2.1 | MIT |
| `swift_kg` | `swift-kg` | 0.4.0 | Elastic-2.0 |
| `tscode_kg` | `tscode-kg` | 0.7.0 | Elastic-2.0 |
| `turtlend` | `turtlend` | 0.1.1 | BSD-3-Clause |
| `vault_kg` | `vault-kg` | 0.2.0 | Elastic-2.0 |
| `waverider` | `waverider` | 0.16.1 | Elastic-2.0 |

## Pins on fleet packages

Every declared floor a fleet repo holds on another fleet package, compared against
that package's current version above. `behind` means the floor has not caught up to
a release that already shipped -- not necessarily a bug, but worth a look if it's been
sitting that way a while.

| Consumer | Pinned package | Floor | Current | Status |
|----------|-----------------|-------|---------|--------|
| `KG_utils` | `quiltwright` | 0.15.0 | 0.16.0 | **behind** |
| `Metabo_kg` | `kgmodule-utils` | 0.24.0 | 0.26.0 | **behind** |
| `agent_kg` | `kgmodule-utils` | 0.23.0 | 0.26.0 | **behind** |
| `connectome_kg` | `kgmodule-utils` | 0.26.0 | 0.26.0 | current |
| `connectome_kg` | `quiltwright` | 0.16.0 | 0.16.0 | current |
| `corpus_pepys` | `kgmodule-utils` | 0.24.0 | 0.26.0 | **behind** |
| `corpus_pepys` | `diary-kg` | 0.100.0 | 0.100.0 | current |
| `corpus_pepys` | `doc-kg` | 0.27.0 | 0.27.0 | current |
| `diary_kg` | `doc-kg` | 0.27.0 | 0.27.0 | current |
| `diary_kg` | `kgmodule-utils` | 0.23.0 | 0.26.0 | **behind** |
| `doc_kg` | `kgmodule-utils` | 0.23.0 | 0.26.0 | **behind** |
| `ftree_kg` | `kgmodule-utils` | 0.23.0 | 0.26.0 | **behind** |
| `ftree_kg` | `kg-rag` | 0.16.0 | 0.17.0 | **behind** |
| `genealogy_kg` | `kgmodule-utils` | 0.26.0 | 0.26.0 | current |
| `genealogy_kg` | `kg-rag` | 0.17.0 | 0.17.0 | current |
| `genealogy_kg` | `quiltwright` | 0.16.0 | 0.16.0 | current |
| `gutenberg_kg` | `kgmodule-utils` | 0.26.0 | 0.26.0 | current |
| `gutenberg_kg` | `doc-kg` | 0.27.0 | 0.27.0 | current |
| `gutenberg_kg` | `diary-kg` | 0.100.0 | 0.100.0 | current |
| `gutenberg_kg` | `kg-rag` | 0.17.0 | 0.17.0 | current |
| `gutenberg_kg` | `quiltwright` | 0.16.0 | 0.16.0 | current |
| `kgrag` | `kgmodule-utils` | 0.26.0 | 0.26.0 | current |
| `kgrag` | `doc-kg` | 0.27.0 | 0.27.0 | current |
| `kgrag` | `memory-kg` | 0.12.0 | 0.12.0 | current |
| `kgrag` | `pycode-kg` | 0.28.1 | 0.28.1 | current |
| `kgrag` | `diary-kg` | 0.100.0 | 0.100.0 | current |
| `kgrag` | `ftree-kg` | 0.17.0 | 0.17.0 | current |
| `kgrag` | `connectome-kg` | 0.8.1 | 0.8.1 | current |
| `kgrag` | `vault-kg` | 0.2.0 | 0.2.0 | current |
| `memory_kg` | `kgmodule-utils` | 0.23.0 | 0.26.0 | **behind** |
| `proteusPy` | `turtlend` | 0.1.1 | 0.1.1 | current |
| `pycode_kg` | `kgmodule-utils` | 0.23.0 | 0.26.0 | **behind** |
| `pycode_kg` | `quiltwright` | 0.15.0 | 0.16.0 | **behind** |
| `quiltwright` | `pypdb2pov` | 0.1.1 | 0.1.1 | current |
| `swift_kg` | `kgmodule-utils` | 0.26.0 | 0.26.0 | current |
| `tscode_kg` | `kgmodule-utils` | 0.23.0 | 0.26.0 | **behind** |
| `vault_kg` | `kgmodule-utils` | 0.24.0 | 0.26.0 | **behind** |
| `vault_kg` | `quiltwright` | 0.15.0 | 0.16.0 | **behind** |
| `waverider` | `turtlend` | 0.1.1 | 0.1.1 | current |
| `waverider` | `quiltwright` | 0.16.0 | 0.16.0 | current |
| `waverider` | `proteuspy` | 0.100.5 | 0.100.5 | current |

## Behind, at a glance

- `KG_utils` pins `quiltwright` at 0.15.0, current is 0.16.0
- `Metabo_kg` pins `kgmodule-utils` at 0.24.0, current is 0.26.0
- `agent_kg` pins `kgmodule-utils` at 0.23.0, current is 0.26.0
- `corpus_pepys` pins `kgmodule-utils` at 0.24.0, current is 0.26.0
- `diary_kg` pins `kgmodule-utils` at 0.23.0, current is 0.26.0
- `doc_kg` pins `kgmodule-utils` at 0.23.0, current is 0.26.0
- `ftree_kg` pins `kgmodule-utils` at 0.23.0, current is 0.26.0
- `ftree_kg` pins `kg-rag` at 0.16.0, current is 0.17.0
- `memory_kg` pins `kgmodule-utils` at 0.23.0, current is 0.26.0
- `pycode_kg` pins `kgmodule-utils` at 0.23.0, current is 0.26.0
- `pycode_kg` pins `quiltwright` at 0.15.0, current is 0.16.0
- `tscode_kg` pins `kgmodule-utils` at 0.23.0, current is 0.26.0
- `vault_kg` pins `kgmodule-utils` at 0.24.0, current is 0.26.0
- `vault_kg` pins `quiltwright` at 0.15.0, current is 0.16.0
