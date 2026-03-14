# KGRAG Product Model: Framework Licensing with Pluggable KG Modules

*Author: Eric G. Suchanek, PhD — Flux-Frontiers*

---

## Overview

KGRAG is offered as a **licensed framework** — a core orchestration and federation engine that customers acquire once and extend incrementally by plugging in the knowledge graph modules relevant to their domain. The product model separates the durable infrastructure investment (the KGRAG framework) from the domain-specific knowledge capabilities (KG modules), enabling customers to start small and expand without replacing their foundation.

---

## The Two-Layer Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                     KGRAG FRAMEWORK (Licensed)                    │
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │  Registry   │  │ Orchestrator│  │  MCP Server │  │   CLI   │ │
│  │  (SQLite)   │  │  (federated │  │  (agent     │  │ (query, │ │
│  │             │  │   queries)  │  │   tools)    │  │  pack)  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │              Adapter Protocol (KGAdapter)                  │   │
│  │  query() | pack() | stats() | analyze()                   │   │
│  └───────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
                              │  plugs in via adapter
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
 ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
 │   KG MODULE  │   │   KG MODULE  │   │   KG MODULE  │
 │  (CodeKG –   │   │  (DocKG –    │   │  (MetaKG –   │
 │   Python)    │   │  Docs/Text)  │   │   Domain)    │
 │  [licensed   │   │  [licensed   │   │  [licensed   │
 │  separately] │   │  separately] │   │  separately] │
 └──────────────┘   └──────────────┘   └──────────────┘
```

**The KGRAG Framework** is the durable asset: the registry, orchestrator, federation engine, MCP server, CLI, and Streamlit dashboard. Customers license this once. It never needs to be replaced — only extended.

**KG Modules** are independently licensed plugins that add domain-specific knowledge graph capabilities. Customers license only the modules they need. New modules become available as the ecosystem grows, and customers can adopt them without migrating infrastructure.

---

## KG Module Catalog

### Currently Available

| Module | Domain | Key Capability |
|--------|--------|---------------|
| **CodeKG-Python** | Python source code | AST-level call graphs, class hierarchies, semantic function search |
| **DocKG** | Markdown / text documentation | Semantic chunking, section-level retrieval, cross-reference graphs |
| **MetaKG** | Metabolic / biochemical pathways | Enzyme networks, pathway traversal, reaction graph queries |

### Roadmap Modules

| Module | Domain | Status |
|--------|--------|--------|
| **CodeKG-TypeScript** | TypeScript / JavaScript | In development |
| **CodeKG-Cpp** | C++ / C | Planned |
| **CodeKG-Java** | Java / Kotlin | Planned |
| **CodeKG-Rust** | Rust | Planned |
| **SchemaKG** | SQL schemas, OpenAPI, GraphQL | Planned |
| **InfraKG** | Terraform, Kubernetes, Helm | Planned |
| **LegalKG** | Contracts, statutes, regulatory filings | Planned |
| **GenomicsKG** | Gene ontologies, variant databases | Planned |
| **FinanceKG** | Financial models, SEC filings | Planned |
| **CustomKG SDK** | Any domain | Available to Enterprise tier |

---

## Licensing Tiers

### Tier 1 — Developer

**Target:** Individual developers, open-source contributors, academic researchers

**Includes:**
- KGRAG Framework (full CLI, MCP server, Python API, Streamlit dashboard)
- 2 KG Modules of choice
- Single-user deployment
- Community support (GitHub Issues)

**Pricing:** $49/month or $490/year per seat

**Restrictions:**
- Not for production deployment to end-users
- Not for embedding in commercial products or services
- Not for team/organizational deployment

---

### Tier 2 — Team

**Target:** Engineering teams, research groups, small-to-mid organizations

**Includes:**
- KGRAG Framework — full capabilities
- Up to 5 KG Modules
- Up to 25 users
- Shared registry deployment (file-system or hosted)
- Priority support (email, 48h response SLA)
- Quarterly update briefings
- Access to pre-release module previews

**Pricing:** $499/month or $4,990/year (covers the team seat count)

**Add-ons:**
- Additional KG Modules: $99/module/month
- Additional user blocks (25-seat): $199/month

---

### Tier 3 — Enterprise

**Target:** Large organizations, platform teams, ISVs embedding KGRAG

**Includes:**
- KGRAG Framework — all capabilities including advanced configuration
- Unlimited KG Modules
- Unlimited users within licensed organization
- On-premise deployment support
- Custom adapter development assistance (CustomKG SDK + professional services)
- Dedicated Slack channel, named support engineer
- 4h response SLA for critical issues
- Custom training and onboarding sessions
- Access to roadmap steering (feature request prioritization)
- OEM/embedding rights (for ISV use cases — see OEM license)

**Pricing:** Custom — contact sales@flux-frontiers.com

**Typical range:** $2,500–$25,000/month depending on deployment scope and modules

---

### Tier 4 — OEM / Embedded

**Target:** Software vendors embedding KGRAG as part of a commercial product or SaaS offering

**Includes:**
- All Enterprise capabilities
- Right to embed KGRAG and KG Modules in a commercial product
- Right to offer KGRAG-powered capabilities to end customers (subject to attribution)
- White-label rights (remove Flux-Frontiers branding — additional fee)
- Revenue share model or flat OEM fee depending on product structure

**Pricing:** Custom — negotiated based on product type, distribution scale, and module usage

---

## KG Module Licensing

KG Modules are licensed as add-ons to the KGRAG Framework. Each module may be licensed:

| License Type | Description | Best For |
|-------------|-------------|----------|
| **Per-seat** | Charged per named user accessing the module | Small, fixed teams |
| **Per-deployment** | Charged per production deployment instance | DevOps/platform teams |
| **Enterprise-wide** | Flat fee for unlimited internal use | Large organizations |
| **OEM-bundled** | Module included in OEM license | ISVs and product vendors |

### Module Pricing Reference (Developer / Team / Enterprise)

| Module | Developer | Team | Enterprise |
|--------|-----------|------|------------|
| CodeKG-Python | Included (1 of 2) | $99/mo | Included |
| DocKG | Included (1 of 2) | $99/mo | Included |
| MetaKG | $29/mo | $99/mo | Included |
| CodeKG-TypeScript | $29/mo | $99/mo | Included |
| CodeKG-Cpp | $29/mo | $99/mo | Included |
| CodeKG-Java | $29/mo | $99/mo | Included |
| SchemaKG | $29/mo | $99/mo | Included |
| InfraKG | $29/mo | $99/mo | Included |
| LegalKG | $49/mo | $149/mo | Custom |
| GenomicsKG | $49/mo | $149/mo | Custom |
| CustomKG SDK | Not available | Not available | Included |

---

## The CustomKG SDK (Enterprise)

Enterprise customers receive access to the **CustomKG SDK**, a development kit for building proprietary KG Modules that plug into the KGRAG framework. The SDK provides:

- The `KGAdapter` base protocol and type definitions
- Reference implementations (CodeKGAdapter, DocKGAdapter, MetaKGAdapter)
- Testing harness for validating new adapters
- Integration test suite for verifying federation behavior
- Documentation and examples for common patterns
- Optional professional services engagement for guided development

This enables organizations with highly specialized knowledge domains to build first-class KG Modules that participate fully in the KGRAG federation — without forking the framework or maintaining a separate codebase.

---

## Deployment Models

### Self-Hosted (All Tiers)

Customers deploy KGRAG on their own infrastructure — developer laptops, internal servers, or private cloud VMs. The registry is a local SQLite file (`~/.kgrag/registry.sqlite` by default); KG databases are file-system artifacts (`.codekg/`, `.dockg/`, `.metakg/`).

- Full data sovereignty: no data leaves the customer's environment
- No dependency on Flux-Frontiers infrastructure
- Customer manages updates and backups

### Flux-Frontiers Hosted Registry (Team / Enterprise)

Flux-Frontiers operates a hosted registry service that replaces the local SQLite file with a centralized, multi-user registry. Team members share a single registry view; KG database artifacts remain on the customer's infrastructure.

- Centralized registry for team coordination
- No file-system sharing required between team members
- Access control: per-user registry visibility and write permissions
- Audit log: who registered/queried/modified KG entries and when

### Full SaaS (Future — Enterprise)

A fully hosted option where both the registry and KG database artifacts are managed by Flux-Frontiers infrastructure. Available under enterprise agreements with appropriate data processing addenda.

---

## Procurement and Licensing Workflow

```
1. Customer evaluates KGRAG
   └─▶ Free 30-day trial (Developer tier, 2 modules)

2. Customer selects tier and modules
   └─▶ License agreement signed (click-through for Developer/Team, MSA for Enterprise)

3. License key issued
   └─▶ Installed in KGRAG config: KGRAG_LICENSE_KEY env var or pyproject.toml [tool.kgrag] section

4. KG Module licenses activated
   └─▶ Per-module activation keys or enterprise blanket key

5. Customer builds and registers KGs
   └─▶ Standard kgrag init / kgrag register workflow

6. Usage telemetry (optional, for Team/Enterprise)
   └─▶ Anonymized query counts, module usage, KG sizes — used for capacity planning
   └─▶ Opt-out available; no query content or data transmitted
```

---

## Value Proposition by Buyer Persona

### The Platform Engineer

"I need to give our AI agents grounded context about our entire codebase — 12 repositories in Python and TypeScript, plus our API documentation."

- License KGRAG Framework (Team tier)
- Add CodeKG-Python, CodeKG-TypeScript (when available), DocKG modules
- Register all repositories and docs with `kgrag init`
- Configure MCP server for all AI tooling (Claude, Copilot, Cursor)
- Result: every AI tool in the organization has federated, grounded context

### The Research Scientist

"I work in computational biology. I need to search across our analysis code, our curated pathway databases, and our published research simultaneously."

- License KGRAG Framework (Developer or Team tier)
- Add CodeKG-Python, MetaKG, DocKG modules
- Index Python analysis scripts, metabolic pathway data, and published papers
- Result: a query like "NADH electron transport chain kinetics" returns relevant code, pathway nodes, and paper sections together

### The Enterprise Architect

"We are building an internal developer platform. We need KGRAG to power the knowledge layer for 500 engineers across 200 repositories."

- License KGRAG Framework (Enterprise tier)
- Adopt full module catalog including SchemaKG and InfraKG
- Deploy hosted registry for centralized team coordination
- Use CustomKG SDK to build proprietary adapters for internal knowledge systems
- Result: a unified knowledge infrastructure across the organization's entire technical corpus

### The ISV / Product Vendor

"We are building a code intelligence product. We want KGRAG's federation engine as the knowledge layer without building it ourselves."

- License KGRAG Framework (OEM tier)
- License specific KG Modules for the domains covered by the product
- Embed KGRAG as a library; expose its capabilities through the product's own interface
- Result: a production-grade, maintained knowledge graph federation engine ships with the product — without the build cost

---

## Competitive Differentiation

| Dimension | KGRAG | General RAG Platforms | Code Search Tools | GraphRAG (Microsoft) |
|-----------|-------|----------------------|-------------------|----------------------|
| Structural + semantic fusion | Yes | Semantic only | Structural only | Semantic only |
| Multi-domain federation | Yes | Limited | No | No |
| Deterministic, verifiable results | Yes | No | Partial | No |
| Pluggable domain modules | Yes | No | No | No |
| MCP / AI agent native | Yes | Partial | Rarely | No |
| Self-hosted, data sovereign | Yes | Sometimes | Sometimes | No (cloud) |
| Language-agnostic architecture | Yes | N/A | Usually single-lang | N/A |

---

## Trial and Evaluation

All prospective customers receive a **30-day free trial** of the Developer tier with access to CodeKG-Python and DocKG modules. No credit card required.

To start a trial:

```bash
pip install 'kg-rag @ git+https://github.com/Flux-Frontiers/KGRAG.git'
kgrag trial activate --email your@email.com
```

The trial period provides full Developer tier capabilities. At the end of the trial, the installation transitions to a read-only mode that allows querying existing KGs but disallows registering new ones until a license is activated.

Enterprise evaluations can be arranged as 90-day pilots with dedicated support. Contact sales@flux-frontiers.com.

---

## Roadmap Investment

Licensing revenue funds the development of new KG Modules, improvements to the federation engine, and the hosted registry infrastructure. Customers directly benefit from this investment through automatic access to new modules (under their license tier) and a continuously improving framework.

The roadmap is governed in part by customer input. Enterprise and OEM customers participate in quarterly roadmap reviews where they can prioritize features and modules.

---

## Frequently Asked Questions

**Can I use KGRAG in an air-gapped environment?**
Yes. All tiers support fully offline, self-hosted deployment. License validation can be configured for periodic offline check-in.

**What happens if a KG Module library is not installed?**
KGRAG degrades gracefully. If a module's underlying library (e.g., `code-kg`) is not installed, that module's KGs are skipped during federated queries. Other modules continue to operate normally. Strict mode (for production environments) raises an error if a licensed module is unavailable.

**Can I build my own KG Module without the Enterprise tier?**
The adapter protocol is open. Any developer can implement `KGAdapter` against a custom data source. The CustomKG SDK (structured support, reference implementations, testing harness) is an Enterprise feature. The protocol itself is not gated.

**Is query content sent to Flux-Frontiers?**
No. Queries, results, and KG content remain entirely within the customer's environment. Optional telemetry is limited to anonymized usage metrics (query counts, module activation) and is opt-in.

**What is the upgrade path from Developer to Enterprise?**
Licenses are additive. Developer licenses are credited toward Team/Enterprise pricing when upgrading within 12 months of original purchase.

**How are KG Modules versioned and updated?**
KG Modules follow semantic versioning. The KGRAG framework specifies minimum compatible module versions. Updates are distributed as package releases; customers update on their own schedule. Breaking changes are communicated 90 days in advance with migration guides.

---

## Contact

| Purpose | Contact |
|---------|---------|
| Trial and purchase | sales@flux-frontiers.com |
| Technical support | support@flux-frontiers.com |
| Partnership and OEM | partners@flux-frontiers.com |
| Security vulnerabilities | security@flux-frontiers.com |

**Web:** https://flux-frontiers.com/kgrag
**GitHub:** https://github.com/Flux-Frontiers/KGRAG

---

*For the technical vision and impact analysis, see [IMPACT.md](IMPACT.md).*
*For architecture details, see [VISION.md](VISION.md).*
*For installation and setup, see [INSTALLATION.md](INSTALLATION.md).*
