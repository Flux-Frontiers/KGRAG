# CodeKG Thorough Repository Analysis Skill

## Overview

Performs comprehensive architectural analysis of any Python repository using CodeKG's graph traversal capabilities. Extracts metrics like:
- **Complexity hotspots** (highest fan-in/fan-out functions)
- **Architectural patterns** (core modules, integration points, bottlenecks)
- **Dependency analysis** (cyclic deps, tight coupling, layering violations)
- **Code quality signals** (dead code, orphaned functions, call depth)

## Trigger Phrases

- "analyze this repository thoroughly"
- "give me a complete codekg analysis"
- "codekg deep dive"
- "repository architecture report"
- "find hotspots in this codebase"

## Strategy

### Phase 1: Graph Statistics & Baseline
```
1. Get overall codebase metrics: graph_stats()
   - Total nodes/edges by kind
   - Edge density (CALLS, CONTAINS, IMPORTS, INHERITS)

2. Identify entry points & analysis targets
   - Functions/classes with 0 callers (dead code candidates)
   - Functions/classes with highest callers (core functionality)
```

### Phase 2: High Fan-In Analysis (Most Called)
```
For top 15 functions by caller count:
1. Use callers(node_id) to get all callers
2. Rank by call frequency across the codebase
3. Identify **core modules** and **integration points**
4. Flag functions that are bottlenecks
```

### Phase 3: High Fan-Out Analysis (Most Calling)
```
For functions that call many others:
1. Query each function's dependencies
2. Identify **coordination hubs** (orchestrators)
3. Find potential **tight coupling** (many internal calls)
4. Detect **god objects** or **god functions**
```

### Phase 4: Dependency Analysis
```
1. Analyze IMPORTS edges
   - Module dependency graph
   - Identify circular imports (if any)
   - Find isolated modules

2. Analyze CONTAINS relationships
   - Module structure & cohesion
   - Classes per module (avg/max)
   - Deep nesting indicators
```

### Phase 5: Architectural Pattern Detection
```
1. Layering analysis
   - Which modules import from which (layer violations?)
   - Top-level vs internal dependencies

2. Design pattern recognition
   - Singleton patterns (static methods, class vars)
   - Manager/Coordinator classes (high fan-out)
   - Service layers (grouped by responsibility)

3. Risk indicators
   - Unexpectedly large files (>2K lines)
   - Functions with very high cyclomatic complexity indicators
   - Orphaned test classes
```

### Phase 6: Actionable Insights
```
Compile findings into:
1. **Hotspots** — Functions/modules requiring careful review
2. **Critical Paths** — Core functionality chains
3. **Risks** — Potential maintenance issues
4. **Opportunities** — Refactoring candidates
5. **Strengths** — Well-designed patterns observed
```

## Implementation Steps

### 1. Run the analyzer — it does the heavy lifting
```bash
# Runs all 8 analysis phases and writes both outputs automatically:
#   Markdown report → <repo>_analysis_<YYYYMMDD>.md  (cwd)
#   JSON snapshot   → ~/.claude/codekg_analysis_latest.json
codekg analyze /path/to/repo
```

### 2. Read the JSON snapshot
The JSON at `~/.claude/codekg_analysis_latest.json` contains all pre-computed metrics — no need to manually chain MCP calls. Schema:

```json
{
  "timestamp": "2026-03-01T12:00:00Z",
  "statistics": {
    "total_nodes": 1234,
    "total_edges": 5678,
    "node_counts": {"function": 400, "class": 80, "method": 300, "module": 45},
    "edge_counts": {"CALLS": 2000, "CONTAINS": 1500, "IMPORTS": 800, "INHERITS": 50}
  },
  "function_metrics": {
    "<node_id>": {"name": "...", "module": "...", "kind": "function",
                  "fan_in": 42, "fan_out": 7, "lines": 30, "risk_level": "medium"}
  },
  "module_metrics": {
    "<path>": {"path": "...", "functions": 12, "classes": 3, "methods": 20,
               "incoming_deps": [...], "outgoing_deps": [...],
               "total_fan_in": 150, "cohesion_score": 0.72}
  },
  "orphaned_functions": [{"name": "...", "module": "...", "fan_in": 0, ...}],
  "high_fanout_functions": [{"name": "...", "fan_out": 89, "risk_level": "high", ...}],
  "critical_paths": [{"chain": ["fn_a", "fn_b", "fn_c"], "depth": 3, "total_callers": 47}],
  "public_apis": [{"name": "...", "fan_in": 15, "kind": "function", ...}],
  "issues": ["⚠️  3 orphaned functions found", "⚠️  2 functions with high fan-out"],
  "strengths": ["✓ Well-structured with 15 core functions identified"]
}
```

### 3. Generate Markdown Report

Structure:
```markdown
# CodeKG Repository Analysis Report

## Quick Stats
- Total functions/classes
- Modules analyzed
- Total relationships

## Complexity Hotspots
### Most Called Functions (Fan-In)
| Function | Callers | Module | Risk Level |
|----------|---------|--------|-----------|

### Most Calling Functions (Fan-Out)
| Function | Calls | Modules | Type |
|----------|-------|---------|------|

## Architectural Patterns
### Core Modules
- Most heavily depended-upon modules
- Why they're core

### Integration Points
- Functions bridging subsystems
- Potential bottlenecks

### Layering Analysis
- Layer violations detected
- Module dependency chains

## Code Quality Signals
### Orphaned Code
- Functions with zero callers
- Potential dead code candidates

### Tight Coupling
- High fan-out functions
- Inter-module dependencies

### Risk Areas
- Large files
- Complex call hierarchies
- Dependency cycles

## Opportunities
### Refactoring Candidates
- Functions that could be split
- Consolidation opportunities

### Reusable Patterns
- Well-designed abstractions to extend
- Patterns to apply elsewhere

## Recommendations
1. ...
2. ...
3. ...
```

## Output Format

**Terminal Output:**
- Beautiful Rich tables with metrics
- Color-coded risk levels (green/yellow/red)
- Progress indicators for long queries

**File Output (always written):**
- Markdown report — `<repo>_analysis_<YYYYMMDD>.md` in cwd (override with `--output`)
- JSON snapshot — `~/.claude/codekg_analysis_latest.json` (override with `--json`)

## Example Invocations

```bash
# Analyze current directory (writes .md + .json automatically)
codekg analyze .

# Analyze specific path
codekg analyze /path/to/repo

# Custom Markdown report path
codekg analyze /path/to/repo --output /tmp/analysis.md

# Custom JSON snapshot path
codekg analyze /path/to/repo --json /tmp/analysis.json

# Both custom paths
codekg analyze /path/to/repo -o /tmp/report.md -j /tmp/metrics.json

# Non-default SQLite / LanceDB paths
codekg analyze /path/to/repo --db /path/to/graph.sqlite --lancedb /path/to/lancedb

# Suppress Rich console table (CI / pipe use)
codekg analyze /path/to/repo --quiet
```

## Skill Output Example

For a repository like **personal_agent**:

```
📊 CodeKG Repository Analysis
═══════════════════════════════

Baseline Metrics:
  • 71,391 nodes (585 classes, 2,036 functions, 3,155 methods)
  • 58,524 edges (24.7K calls, 23.6K attr access, 5.7K imports)
  • 535 modules analyzed

🔥 Complexity Hotspots:

Most Called (Fan-In):
  1. UserManager.__init__          [1,247 callers] 🟥 CRITICAL
  2. PersonalAgentConfig.get_instance() [956 callers] 🟥 CRITICAL
  3. AgentMemoryManager.recall()   [634 callers] 🟡 HIGH
  ... (12 more)

Most Calling (Fan-Out):
  1. AgentMemoryManager.store_memory()   [89 calls] → Orchestrator
  2. KnowledgeCoordinator.route_query()  [76 calls] → Router
  3. UserManager.create()                [71 calls] → Complex init
  ... (12 more)

🏗️  Architectural Patterns:

Core Modules:
  ✓ personal_agent/core/
    └─ 234 incoming edges (most depended-upon)

Integration Points:
  • hindsight_client.py — Bridges agent ↔ Hindsight
  • knowledge_coordinator.py — Bridges semantic ↔ graph

Layering Issues:
  ✗ commands/shell/session.py imports from tools/
    (expected: tools imports from commands, not reverse)

⚠️  Risk Areas:

Orphaned Code:
  • old/run_agent.py (0 callers) — Remove?
  • analysis/run_tests.py (1 caller) — Dead code?

Tight Coupling:
  • AgentMemoryManager has 89 outgoing calls
    → Consider breaking into sub-managers

Call Depth:
  • Deepest chain: UserManager → Config → Runtime
    → 7 levels deep, potential bottleneck

✅ Strengths:

Well-Designed:
  ✓ HindsightSimpleClient — Clean, minimal interface
  ✓ ConfigStateTransaction — Atomic operations
  ✓ AntiDuplicateMemory — Focused responsibility

Reusable Patterns:
  ✓ Singleton + locking (PersonalAgentConfig)
  ✓ Per-request HTTP (HindsightSimpleClient)

💡 Recommendations:

1. Refactor AgentMemoryManager
   → Split into store_manager + recall_manager
   → Reduce fan-out from 89 → ~45

2. Move orphaned files to archive/
   → Reduces confusion for new contributors

3. Add test coverage for call chain analysis
   → Validate that orchestrators don't have circular deps

4. Document integration points
   → Explain why hindsight_client bridges layers
```

## Key Features

✅ **Comprehensive** — Analyzes all relationship types
✅ **Actionable** — Identifies specific functions/modules to review
✅ **Visual** — Color-coded risk levels, ASCII diagrams
✅ **Fast** — Caches results, progresses through queries
✅ **Reusable** — Works on any Python codebase with CodeKG
✅ **Extensible** — Easy to add custom analysis dimensions

## Edge Cases

- **Large repos (100K+ nodes)** → Use sampling for fan-in/fan-out
- **Circular imports** → Detect and flag at top of report
- **Mixed codebases** → Filter by file pattern if needed
- **Deprecated code** → Flag by analyzing comment patterns

## Future Enhancements

1. **Graph visualization** — Export to Graphviz/D3.js
2. **Trend analysis** — Compare two snapshots over time
3. **Custom queries** — Allow users to define their own hotspot criteria
4. **Machine learning** — Predict refactoring ROI based on metrics
5. **Multi-language** — Extend beyond Python (JavaScript, Go, Rust)
