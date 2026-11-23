# Fleet versions and pins

*Generated 2026-11-23 by `scripts/versions_snapshot.py` in the fleet's private
coordination repo, with its private repos left out. Do not hand-edit; it is
regenerated there and copied here.*

This snapshot covers the two things that go stale silently: what version each
repo currently declares itself as, and whether every consumer's floor on a fleet
package has caught up to it.

## Current versions

| Repo | Package | Version | License |
|------|---------|---------|---------|
| `KG_utils` | `kgmodule-utils` | 0.31.0 | Elastic-2.0 |
| `Metabo_kg` | `metabo-kg` | 0.18.0 | Elastic-2.0 |
| `agent_kg` | `agent-kg` | 0.14.1 | Elastic-2.0 |
| `connectome_kg` | `connectome-kg` | 0.10.1 | Elastic-2.0 |
| `corpus_pepys` | `corpus-pepys` | 0.7.2 | Elastic-2.0 |
| `diary_kg` | `diary-kg` | 0.101.0 | Elastic-2.0 |
| `doc_kg` | `doc-kg` | 0.30.0 | Elastic-2.0 |
| `ftree_kg` | `ftree-kg` | 0.18.1 | Elastic-2.0 |
| `genealogy_kg` | `genealogy-kg` | 0.6.0 | Elastic-2.0 |
| `gutenberg_kg` | `gutenberg-kg` | 1.40.1 | Elastic-2.0 |
| `imagewright` | `imagewright` | 0.1.0 | Elastic-2.0 |
| `kgrag` | `kg-rag` | 0.19.0 | Elastic-2.0 |
| `knowledge_press` | `-` | 1.51.1 | - |
| `kpress_disulfide` | `-` | 0.2.2 | - |
| `kpress_family` | `-` | 0.2.0 | - |
| `memory_kg` | `memory-kg` | 0.13.1 | Elastic-2.0 |
| `proteusPy` | `proteuspy` | 0.101.1 | BSD-3-Clause |
| `pycode_kg` | `pycode-kg` | 0.29.3 | Elastic-2.0 |
| `pypdb2pov` | `pypdb2pov` | 0.1.1 | BSD-3-Clause |
| `quiltwright` | `quiltwright` | 0.17.0 | BSD-3-Clause |
| `satprint` | `satprint` | 0.5.1 | MIT |
| `swift_kg` | `swift-kg` | 0.5.1 | Elastic-2.0 |
| `tscode_kg` | `tscode-kg` | 0.8.2 | Elastic-2.0 |
| `turtlend` | `turtlend` | 0.1.2 | BSD-3-Clause |
| `vault_kg` | `vault-kg` | 0.6.1 | Elastic-2.0 |
| `waverider` | `waverider` | 0.16.3 | Elastic-2.0 |

## Pins on fleet packages

Every declared floor a fleet repo holds on another fleet package, compared against
that package's current version above. `behind` means the floor has not caught up to
a release that already shipped -- not necessarily a bug, but worth a look if it's been
sitting that way a while.

| Consumer | Pinned package | Floor | Current | Status |
|----------|-----------------|-------|---------|--------|
| `KG_utils` | `quiltwright` | 0.17.0 | 0.17.0 | current |
| `KG_utils` | `doc-kg` | 0.30.0 | 0.30.0 | current |
| `Metabo_kg` | `kgmodule-utils` | 0.29.0 | 0.31.0 | **behind** |
| `agent_kg` | `kgmodule-utils` | 0.30.2 | 0.31.0 | **behind** |
| `connectome_kg` | `kgmodule-utils` | 0.29.0 | 0.31.0 | **behind** |
| `connectome_kg` | `quiltwright` | 0.17.0 | 0.17.0 | current |
| `corpus_pepys` | `kgmodule-utils` | 0.29.2 | 0.31.0 | **behind** |
| `corpus_pepys` | `diary-kg` | 0.101.0 | 0.101.0 | current |
| `corpus_pepys` | `doc-kg` | 0.30.0 | 0.30.0 | current |
| `diary_kg` | `doc-kg` | 0.29.0 | 0.30.0 | **behind** |
| `diary_kg` | `kgmodule-utils` | 0.29.0 | 0.31.0 | **behind** |
| `doc_kg` | `kgmodule-utils` | 0.29.0 | 0.31.0 | **behind** |
| `ftree_kg` | `kgmodule-utils` | 0.29.0 | 0.31.0 | **behind** |
| `ftree_kg` | `kg-rag` | 0.16.0 | 0.19.0 | **behind** |
| `genealogy_kg` | `kgmodule-utils` | 0.29.0 | 0.31.0 | **behind** |
| `genealogy_kg` | `kg-rag` | 0.17.0 | 0.19.0 | **behind** |
| `genealogy_kg` | `quiltwright` | 0.17.0 | 0.17.0 | current |
| `gutenberg_kg` | `kgmodule-utils` | 0.30.2 | 0.31.0 | **behind** |
| `gutenberg_kg` | `doc-kg` | 0.30.0 | 0.30.0 | current |
| `gutenberg_kg` | `diary-kg` | 0.101.0 | 0.101.0 | current |
| `gutenberg_kg` | `kg-rag` | 0.18.2 | 0.19.0 | **behind** |
| `gutenberg_kg` | `quiltwright` | 0.17.0 | 0.17.0 | current |
| `kgrag` | `kgmodule-utils` | 0.31.0 | 0.31.0 | current |
| `kgrag` | `doc-kg` | 0.30.0 | 0.30.0 | current |
| `kgrag` | `memory-kg` | 0.13.0 | 0.13.1 | **behind** |
| `kgrag` | `pycode-kg` | 0.29.3 | 0.29.3 | current |
| `kgrag` | `diary-kg` | 0.101.0 | 0.101.0 | current |
| `kgrag` | `ftree-kg` | 0.18.1 | 0.18.1 | current |
| `kgrag` | `connectome-kg` | 0.10.1 | 0.10.1 | current |
| `kgrag` | `vault-kg` | 0.6.1 | 0.6.1 | current |
| `kgrag` | `imagewright` | 0.1.0 | 0.1.0 | current |
| `kgrag` | `agent-kg` | 0.14.0 | 0.14.1 | **behind** |
| `kgrag` | `genealogy-kg` | 0.6.0 | 0.6.0 | current |
| `kgrag` | `swift-kg` | 0.5.1 | 0.5.1 | current |
| `kgrag` | `tscode-kg` | 0.8.1 | 0.8.2 | **behind** |
| `memory_kg` | `kgmodule-utils` | 0.29.0 | 0.31.0 | **behind** |
| `proteusPy` | `turtlend` | 0.1.1 | 0.1.2 | **behind** |
| `pycode_kg` | `kgmodule-utils` | 0.29.1 | 0.31.0 | **behind** |
| `pycode_kg` | `quiltwright` | 0.17.0 | 0.17.0 | current |
| `quiltwright` | `pypdb2pov` | 0.1.1 | 0.1.1 | current |
| `swift_kg` | `kgmodule-utils` | 0.29.1 | 0.31.0 | **behind** |
| `tscode_kg` | `kgmodule-utils` | 0.29.0 | 0.31.0 | **behind** |
| `vault_kg` | `kgmodule-utils` | 0.29.0 | 0.31.0 | **behind** |
| `vault_kg` | `quiltwright` | 0.17.0 | 0.17.0 | current |
| `waverider` | `turtlend` | 0.1.1 | 0.1.2 | **behind** |
| `waverider` | `quiltwright` | 0.17.0 | 0.17.0 | current |
| `waverider` | `proteuspy` | 0.100.6 | 0.101.1 | **behind** |

## Behind, at a glance

- `Metabo_kg` pins `kgmodule-utils` at 0.29.0, current is 0.31.0
- `agent_kg` pins `kgmodule-utils` at 0.30.2, current is 0.31.0
- `connectome_kg` pins `kgmodule-utils` at 0.29.0, current is 0.31.0
- `corpus_pepys` pins `kgmodule-utils` at 0.29.2, current is 0.31.0
- `diary_kg` pins `doc-kg` at 0.29.0, current is 0.30.0
- `diary_kg` pins `kgmodule-utils` at 0.29.0, current is 0.31.0
- `doc_kg` pins `kgmodule-utils` at 0.29.0, current is 0.31.0
- `ftree_kg` pins `kgmodule-utils` at 0.29.0, current is 0.31.0
- `ftree_kg` pins `kg-rag` at 0.16.0, current is 0.19.0
- `genealogy_kg` pins `kgmodule-utils` at 0.29.0, current is 0.31.0
- `genealogy_kg` pins `kg-rag` at 0.17.0, current is 0.19.0
- `gutenberg_kg` pins `kgmodule-utils` at 0.30.2, current is 0.31.0
- `gutenberg_kg` pins `kg-rag` at 0.18.2, current is 0.19.0
- `kgrag` pins `memory-kg` at 0.13.0, current is 0.13.1
- `kgrag` pins `agent-kg` at 0.14.0, current is 0.14.1
- `kgrag` pins `tscode-kg` at 0.8.1, current is 0.8.2
- `memory_kg` pins `kgmodule-utils` at 0.29.0, current is 0.31.0
- `proteusPy` pins `turtlend` at 0.1.1, current is 0.1.2
- `pycode_kg` pins `kgmodule-utils` at 0.29.1, current is 0.31.0
- `swift_kg` pins `kgmodule-utils` at 0.29.1, current is 0.31.0
- `tscode_kg` pins `kgmodule-utils` at 0.29.0, current is 0.31.0
- `vault_kg` pins `kgmodule-utils` at 0.29.0, current is 0.31.0
- `waverider` pins `turtlend` at 0.1.1, current is 0.1.2
- `waverider` pins `proteuspy` at 0.100.6, current is 0.101.1
