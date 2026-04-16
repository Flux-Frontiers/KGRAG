# MetaboKG — Stack Reference
**Domain:** Metabolic pathways
**Package:** `metabo-kg` | `Flux-Frontiers/metabo_kg`
**CLI binary:** `metabokg`
**MCP server:** `metabokg mcp --db <path> --lancedb <path>`
**Index location:** `<repo>/.metabokg/`

## What It Does
Builds a semantic knowledge graph of metabolic pathways: reactions, compounds,
enzymes, kinetic parameters. Supports flux balance analysis (FBA), ODE kinetic
simulation, and perturbation (what-if) analysis. Sister project to the KGRAG
stack via Flux Frontiers.

## Node Types
`reaction`, `compound` (metabolite), `pathway`, `enzyme`, `kinetic_param`

## MCP Tools (11)
| Tool | Use When |
|---|---|
| `query_pathway(q)` | Find pathways by description |
| `get_compound(id)` | Metabolite details |
| `get_reaction(id)` | Reaction details |
| `find_path(from, to)` | Trace biochemical route between compounds |
| `get_kinetic_params(reaction_id)` | Km/Vmax/kcat values |
| `seed_kinetics()` | Populate kinetic parameters (call before simulation) |
| `simulate_fba()` | Steady-state flux balance analysis |
| `simulate_ode()` | Kinetic time-course simulation |
| `simulate_whatif(...)` | Perturbation: knockouts, activity changes, overrides |
| `snapshot_list()` | List metric snapshots |
| `snapshot_show(key)` | Metrics for a snapshot |

## Active Corpus
- **DB:** `/Users/egs/repos/Metabo_kg/.metabokg/meta.sqlite`
- **LanceDB:** `/Users/egs/repos/Metabo_kg/.metabokg/lancedb`
- No snapshots recorded yet — run `metabokg snapshot save` for baseline

## MCP Launch
```json
{
  "command": "/Users/egs/repos/kgrag/.venv/bin/metabokg",
  "args": [
    "mcp",
    "--db", "/Users/egs/repos/Metabo_kg/.metabokg/meta.sqlite",
    "--lancedb", "/Users/egs/repos/Metabo_kg/.metabokg/lancedb"
  ]
}
```

## Key Commands
```bash
metabokg query "glycolysis pathway"
metabokg simulate fba
metabokg snapshot save
metabokg snapshot list
metabokg analyze
```

## Usage Rules
- Call `seed_kinetics()` before any simulation
- `simulate_fba()` for steady-state; `simulate_ode()` for time-course
- `find_path(from, to)` for biochemical route tracing
