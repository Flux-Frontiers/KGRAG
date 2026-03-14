# MetaKG Naming Refactoring Plan

## Current State

Currently named: **MetaKG** in the codebase
Actual purpose: **Metabolic pathway knowledge graph** for biochemistry

## The Problem

"MetaKG" is a poor naming choice because it suggests:
- A generic "meta" KG (metadata about other KGs)
- A framework for ANY domain-specific KG
- Abstract/general purpose

When in reality it's:
- A **specific, specialized KG for metabolic pathways**
- Domain-specific to biochemistry
- The first exemplar of semantic + structural KG applied to biochemistry

## Future Refactoring

**Plan:** Rename MetaKG → MetaboKG to clarify its domain-specific purpose

This makes the naming unambiguous:
- **CodeKG** — Python code semantics + structure
- **DocKG** — Documentation semantics + structure
- **MetaboKG** — Metabolic pathway semantics + structure

**Future:** When a true generic meta-KG framework is created, it will have a different name or architecture.

## MetaboKG: Groundbreaking Application

The current MetaKG (to be renamed MetaboKG) is **the first of its kind** — a demonstration of the power of the semantic + structural KG approach applied to biochemistry:

✨ **Unprecedented capability:** Semantic search + structural reasoning over metabolic pathways
✨ **Domain-specific:** Encodes metabolic biochemistry with precision
✨ **Same framework as code/docs:** Uses the identical 2-layer KG architecture
✨ **Exemplary:** Proves this approach scales beyond software to any complex knowledge domain

### What MetaboKG Enables

With MetaboKG, researchers can:
- Semantically search metabolic pathways ("ATP synthesis pathways")
- Navigate structural relationships (enzyme → substrate → product)
- Discover cross-domain patterns (code ↔ documentation ↔ biochemistry)
- Integrate biological knowledge into computational workflows

## Implications for KGRAG

KGRAG's true power becomes clear with the metabolic pathway KG (currently MetaKG, to be renamed MetaboKG):

> **KGRAG is not just for code and docs. It's a unified orchestration framework for ANY domain knowledge represented as hybrid semantic + structural KGs.**

The architecture proves that this 2-layer approach works across:
1. **Software engineering** (CodeKG) — code analysis
2. **Technical documentation** (DocKG) — doc analysis
3. **Biochemistry** (MetaboKG) — metabolic pathway analysis
4. **Future domains** (extensible) — any structured knowledge

This validates the universal applicability of the semantic + structural approach.

## Naming Strategy

### Current Implementation
- **CodeKG** — Code analysis
- **DocKG** — Documentation analysis
- **MetaKG** (current, to be renamed to **MetaboKG**) — Metabolic pathway analysis

### Future Roadmap
- **MetaboKG** — Metabolic pathway analysis (renamed from current MetaKG)
- **MetaKG** (new, TBD) — If/when a true generic meta-KG framework is created
  - OR renamed to something more descriptive
  - OR architectural refactoring as needed

### Naming Guidelines
✅ **Do:**
- Use domain-specific names (CodeKG, DocKG, MetaboKG)
- Be explicit about what each KG analyzes
- Avoid ambiguous "meta" terminology

❌ **Avoid:**
- "Meta KG" (suggests metadata or generic)
- Naming that implies broader scope than actual
- Names that cause confusion about purpose

## Implementation Timeline

### Phase 1: Current (No changes yet)
- MetaKG remains as-is in codebase
- Documentation uses "MetaKG" term
- This note captures the intention for future refactoring

### Phase 2: Refactoring (Future)
When ready to implement:
1. Rename MetaKG → MetaboKG in codebase
2. Update all code references (imports, class names, etc.)
3. Update documentation:
   - VISION.md
   - INSTALLATION.md
   - USAGE.md
   - Skill references
   - README files
4. Update tests and examples
5. Release with changelog entry

### Phase 3: Future MetaKG (TBD)
- When/if true generic meta-KG framework is created
- Decide on naming and architecture
- Integrate with KGRAG following established patterns

---

## Key Insight

The current metabolic pathway KG (MetaKG) is exceptional because it proves the semantic + structural KG approach works across domains — not just software. This groundbreaking achievement deserves clarity in naming.

**MetaboKG: The first domain-specific semantic + structural KG outside software engineering.**

---

## See Also

- This note (future refactoring plan)
- VISION.md (current KGRAG architecture)
- INSTALLATION.md (setup guides)
- USAGE.md (usage patterns)
- Skill documentation (agent knowledge)
