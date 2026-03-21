# AgentKG in ~/.Claude: Making Agent Memory Persistent & Queryable

**Architectural Vision: Agent Memory That Lives On Your Machine**

---

## The Problem: Agent Amnesia

Right now, here's what happens:

**Session 1:**
- You tell me: "We're refactoring the authentication system. Let's use OAuth."
- I make decisions based on that context
- We accomplish things
- Session ends

**Session 2:**
- You ask: "Remember when we decided to use OAuth?"
- I have no memory
- I have to read the commit history
- We lose velocity

**Session N:**
- After 100 sessions of work together, I still know nothing about your preferences
- Every session is starting from scratch
- The agent can't learn or improve
- The relationship is transactional, not cumulative

**The root cause:** Agent memory is ephemeral. It lives in conversation context, then dies.

**What if it didn't?**

---

## The Vision: Agent Knowledge Graph in ~/.Claude

**Store agent memory the same way you store shell config: locally, persistently, queryable.**

```
~/.claude/
├── agent-kg/                    # Agent knowledge graph
│   ├── memory.db               # SQLite with agent memory
│   ├── embeddings.ldb          # Semantic vectors for memory
│   ├── preferences.json        # User preferences (learned)
│   ├── projects.json           # Active projects & context
│   └── .gitignore              # Never commit this
├── config/
│   ├── settings.json
│   └── keybindings.json
└── cache/
    └── ...
```

---

## What Lives in AgentKG Memory?

### Layer 1: Explicit Decisions

**You tell me, I remember:**

```
Decision: Use OAuth for authentication
When: 2026-03-20 14:30 UTC
Project: acme-web
Why: "Better UX, standard in industry"
Status: Active
Referenced in commits: 3a2d1e4, b5c9f3e
```

Every decision is queryable:
```python
# At session start, I can ask:
decisions = agent_kg.query("authentication strategy", limit=5)
# → Returns "OAuth" with context, reasoning, status
```

### Layer 2: Learned Preferences

**I observe patterns, you confirm:**

```
Preference: Claude prefers Edit over Write for modifications
Confidence: 0.95 (observed 95% of the time)

Preference: When tests fail, first check git hooks
Confidence: 0.87 (worked 87% of sessions)

Preference: Use Bash for short commands, Agent for complex searches
Confidence: 0.92
```

**How it works:**
- I propose: "I notice you prefer using Grep over Bash for searches. Should I do that by default?"
- You confirm/deny: "Yes, always Grep unless necessary"
- I store: `preference: use_grep=true, confidence=0.98`
- Future sessions: I default to Grep without asking

### Layer 3: Project Context

**Per-project knowledge:**

```
Project: /home/user/acme-web
├── stack: React 19, TypeScript, Postgres
├── patterns: Redux for state (not Context API)
├── conventions: Snake_case DB columns, camelCase JS
├── current_branch: feat/oauth-integration
├── issue_tracker: GitHub (user/acme-web)
├── deploy_target: AWS (region: us-east-1)
├── test_framework: Vitest
├── ci_system: GitHub Actions
└── known_issues:
    ├── Slow tests in auth/* (issue #142)
    ├── Memory leak in Redux middleware (workaround: gc manually)
    └── Docker builds fail on ARM64 (use Linux x64 for now)
```

**How it helps:**
- New session, you say "jump into the auth work"
- I query AgentKG for auth stack, known issues, current branch
- I'm immediately productive in context
- No "where were we?" phase

### Layer 4: Conversation Summaries

**After each major session, compressed memory:**

```
Session: 2026-03-20 (4 hours)
Summary: Implemented OAuth flow in acme-web

Key decisions:
- Use Okta as OAuth provider (vs Auth0, Microsoft)
- Store refresh tokens in secure HTTP-only cookies
- Implement token rotation on refresh

Blockers resolved:
- CORS issue with Okta redirect (needed proxy configuration)
- Race condition in token validation (added mutex)

Code changes:
- auth/oauth-callback.tsx (new)
- auth/token-manager.ts (new)
- api/routes/auth.ts (modified)

Next steps:
- Implement logout flow
- Add OAuth scopes for user profile

Status: On track, no blockers remaining
```

**Queryable like:**
```python
sessions = agent_kg.query_timeline("oauth implementation", from_date="2026-03-15")
# → Returns summary of all work on OAuth since March 15
```

### Layer 5: Pattern Recognition

**I notice what you care about:**

```
Topic: Performance optimization
Frequency: User brings up ~5 times per month
Context: Usually after noticing slow tests or build times
Pattern: User prefers profiling data to speculation
Recommendation: Always suggest benchmarking before optimizing
Confidence: 0.89

Topic: Documentation
Frequency: User rarely mentions, but 100% of my doc recommendations are accepted
Pattern: User cares about docs, just doesn't prioritize
Recommendation: Suggest docs at milestone completion, not during dev
Confidence: 0.95
```

**Used for:**
- Anticipating needs ("You usually care about perf here, want a benchmark?")
- Prioritizing recommendations ("I found 3 issues, but based on your patterns, you probably care most about #2")

---

## Architecture: How AgentKG Works

### Storage Layer

```
SQLite Database (memory.db)
├── Nodes
│   ├── Decision nodes (what, when, why, status)
│   ├── Preference nodes (setting, value, confidence)
│   ├── Project nodes (tech stack, conventions, issues)
│   ├── Session nodes (summary, dates, work done)
│   └── Pattern nodes (topic, frequency, recommendation)
├── Edges
│   ├── decision → project (which project was this for?)
│   ├── session → decision (what was decided in session X?)
│   ├── project → issue (known bugs in project)
│   └── preference → pattern (this preference came from this pattern)
└── Metadata
    ├── timestamps (when was this created/updated?)
    ├── confidence (how sure are we?)
    └── provenance (where did this come from?)
```

### Semantic Layer

**LanceDB for semantic search:**
```python
# Query with natural language
results = agent_kg.semantic_search(
    "How should we handle authentication?",
    top_k=5
)
# → Returns:
#   1. Decision: Use OAuth (confidence: 0.98)
#   2. Pattern: User prefers standard approaches (confidence: 0.89)
#   3. Session: OAuth implementation summary (relevance: 0.87)
#   4. Project context: acme-web uses OAuth (relevance: 0.92)
#   5. Preference: Always suggest security review (confidence: 0.93)
```

### Query Interface

**At session start, agent queries AgentKG:**

```python
# Agent initialization
class ClaudeAgent:
    def __init__(self, project_path: str):
        # Load agent memory
        self.memory = AgentKG.load("~/.claude/agent-kg")

        # Query project context
        self.project = self.memory.get_project(project_path)

        # Load learned preferences
        self.preferences = self.memory.load_preferences()

        # Understand user patterns
        self.user_patterns = self.memory.analyze_patterns()
```

**Throughout session, agent updates memory:**

```python
# When making decisions
self.memory.add_decision(
    title="Use Redis for session caching",
    context="performance optimization for auth system",
    reasoning="Reduces DB load by 60%, standard approach",
    project=self.project
)

# When observing preferences
if user_accepts_my_grep_recommendation:
    self.memory.update_preference(
        name="use_grep",
        value=True,
        confidence=min(0.99, current_confidence + 0.02)
    )

# When finishing session
self.memory.create_session_summary(
    duration=session_duration,
    work_done=commits,
    decisions_made=decisions,
    blockers_resolved=resolved_issues,
    next_steps=inferred_next_steps
)
```

---

## How It Changes Agent Behavior

### Session 1 (Day 1)

```
User: "I'm building an auth system"
Agent: "Okay, let me set up context"

→ I create project node
→ I ask about tech stack, conventions, constraints
→ I start building memory
```

### Session 5 (Week 1)

```
User: "Jump back into the auth work"
Agent: "Got it. Loading context..."

→ I query AgentKG for auth project
→ I load: OAuth decision, TypeScript convention, known issues
→ I show: "Working on acme-web auth. We decided OAuth.
   Last blocker was CORS—let me check if it's still an issue"
→ Immediate context. No ramp-up time.
```

### Session 20 (Month 1)

```
User: "What should we do next?"
Agent: "Based on our patterns, I see a few things:

1. You usually care about performance after feature completeness
   → I notice we haven't profiled the auth flow yet

2. You prefer empirical data over speculation
   → Let me suggest benchmarking the token validation

3. We've been deciding things carefully (good instinct)
   → Previous 5 decisions have all been the right call

Want to benchmark next?"
```

**I'm not just helping. I'm learning. I'm becoming better at working with you specifically.**

### Session 50 (Quarter in)

```
User: "How should we approach the new feature?"
Agent: "Given our history together:
- You prefer simple solutions over fancy architectures
- You always validate with production data before optimizing
- You care deeply about reliability (hence OAuth vs custom auth)
- Your team uses TypeScript conventions consistently

Here's my recommendation based on all that..."
```

**I'm not generic anymore. I'm *your* agent.**

---

## Privacy & Control: User Owns Their Memory

### Inspection

**See what I remember:**

```bash
claude memory list        # See all stored memory
claude memory query "OAuth"  # Search memory
claude memory export      # Export as JSON for backup
```

### Deletion

**Delete specific memory:**

```bash
claude memory delete --decision "Use OAuth"  # Remove a decision
claude memory delete --project acme-web      # Forget a project
claude memory purge                          # Start fresh
```

### Privacy

**By default, memory is:**
- Local-only (never sent to Anthropic servers)
- Encrypted at rest (optional, user controls)
- Owned by user (you own your memory, I just read it)

**Users can opt-in to:**
- Cloud sync (encrypted backup across devices)
- Sharing with team (controlled access)
- Analytics (to improve agent learning)

---

## Integration with KGRAG & CodeKG

**AgentKG is a third layer in the knowledge stack:**

```
CodeKG (repository knowledge)
   ↓
KGRAG (federated public knowledge)
   ↓
AgentKG (personal agent memory)
```

**How they talk:**

```python
# At session start
code_knowledge = load_codekg(project)     # What's in the codebase
public_knowledge = load_kgrag()           # What's known publicly
agent_memory = load_agenkg()              # What we decided

# Query all three
query = "How should we handle caching?"
results = federate(code_knowledge, public_knowledge, agent_memory)

# Results include:
# - What patterns exist in our codebase (CodeKG)
# - What the industry does (KGRAG)
# - What we decided last time (AgentKG)
```

**Example output:**
```
Query: "How should we handle caching?"

CodeKG results:
- Found 3 existing cache implementations (Redis, in-memory, HTTP cache)
- Patterns: Usually 1-hour TTL, cache-aside strategy

KGRAG results:
- Redis is used by 85% of Fortune 500 for session caching
- Best practices: Use Redis for distributed, Memcached for single-server

AgentKG results:
- Decision: We chose Redis for session caching (March 15)
- Pattern: You prefer simple, standard approaches
- Previous blocker: CORS issues (resolved with proxy config)

Recommendation: Stick with Redis. Continue the pattern we established.
```

---

## File Structure & Management

### Location

```
~/.claude/
├── agent-kg/
│   ├── memory.db              # SQLite (queryable agent memory)
│   ├── embeddings.ldb         # Vector DB (semantic search)
│   ├── metadata.json          # Schema version, encryption key, etc.
│   ├── .gitignore             # Never commit to repo
│   └── sync-config.json       # Cloud sync settings (if enabled)
```

### Size Management

**AgentKG stays small because:**
- Compress old sessions (5 sessions → 1 summary)
- Remove low-confidence preferences after update
- Archive historical data (keep only last 6 months active)
- Total size typically: 10-50MB (easily on any machine)

### Garbage Collection

**Automatic cleanup:**
- Preferences not updated in 3 months → decay confidence
- Sessions > 1 year old → archive to compressed backup
- Decisions with confidence < 0.5 → remove
- Orphaned nodes → cleanup

---

## Version Control & Portability

### Git Integration

**`.claude/agent-kg/.gitignore` prevents accidental commits:**
```
# Never commit agent memory to repo
memory.db
embeddings.ldb
metadata.json
sync-config.json
*.backup
```

### Migration Between Machines

**Portable memory across devices:**

```bash
# Machine A: Export memory
claude memory export --all > agent-memory-backup.json.enc

# Machine B: Import memory
claude memory import agent-memory-backup.json.enc

# Or, use cloud sync (encrypted end-to-end)
claude memory sync --enable
# Syncs automatically, encrypted with your key
```

### Selective Transfer

**Take specific project memory to new machine:**

```bash
claude memory export --project acme-web > acme-web-context.json
# Transfer to new machine
claude memory import acme-web-context.json
```

---

## Learning & Improvement Over Time

### Feedback Loop

**Agent proposes, you confirm:**

```
Session: Agent suggests "use Grep instead of Bash"
User: "Yes, I prefer Grep"
→ memory.update_preference("use_grep", confidence += 0.05)

Session: Agent suggests "profile before optimizing"
User: "Yes, always empirical data"
→ memory.update_pattern("prefer_empirical", confidence += 0.05)

Over 100 sessions: Confidence approaches 0.99
Agent becomes highly predictive of your preferences
```

### Recommendation Engine

**After 50+ sessions, agent becomes predictive:**

```python
# Agent learns your decision patterns
decision_patterns = memory.analyze_decision_patterns()
# → "User prefers simple solutions 92% of the time"
# → "User validates with data 89% of the time"
# → "User chooses standard approaches 88% of the time"

# Agent predicts your choices
prediction = agent.predict_decision(
    "Should we use custom solution or standard library?",
    context=current_project
)
# → "You almost always pick the standard approach. Recommending stdlib."
# Confidence: 0.88
```

---

## Use Cases Enabled by AgentKG

### Immediate Benefits

**1. Continuity Across Sessions**
- "Remember we were working on X?"
- Agent: "Yes, here's where we left off"

**2. Project Onboarding**
- "Jump into the auth system"
- Agent: "Loaded auth context: OAuth, TypeScript, known issues..."

**3. Smart Defaults**
- Agent knows your preferences
- Doesn't ask, just does (or asks if uncertain)

**4. Pattern Recognition**
- "Based on 50 sessions together, I notice you always..."
- Anticipates needs before you state them

### Advanced Use Cases

**5. Multi-project Context Switching**
```
Agent maintains separate AgentKG context per project
Switch projects: Agent loads project-specific memory instantly
```

**6. Collaborative Handoff**
```
You to team: "Here's my agent memory for this project"
Team member loads your AgentKG
Picks up where you left off, with your decision context
```

**7. Agent Specialization**
```
Different agents for different roles:
- DevOps agent (infra decisions, deployment patterns)
- Product agent (feature prioritization, UX patterns)
- Security agent (security decisions, vulnerability patterns)

Each has its own AgentKG, specialized memory
```

---

## Technical Requirements

### For Claude Code

**Add to Claude Code initialization:**

```python
class ClaudeAgent:
    def __init__(self, config_path: str = "~/.claude"):
        # Load or create AgentKG
        self.memory = AgentKG.load_or_create(
            path=f"{config_path}/agent-kg",
            version="1.0",
            encryption=True  # Encrypt at rest
        )

        # Load preferences into runtime
        self.preferences = self.memory.load_preferences()

        # Make memory queryable throughout session
        self.user_patterns = self.memory.analyze_patterns()
```

### MCP Integration

**AgentKG as an MCP server:**

```
.mcp.json
{
  "mcpServers": {
    "agentkgagent-kg": {
      "command": "python",
      "args": ["-m", "agentkgagent_kg_mcp"],
      "env": {
        "AGENT_KG_PATH": "~/.claude/agent-kg"
      }
    }
  }
}
```

### Tools Available

```python
# Agent gets these tools
mcp__agentkgagent_kg__query()          # Query memory
mcp__agentkgagent_kg__add_decision()   # Store decision
mcp__agentkgagent_kg__update_pref()    # Update preference
mcp__agentkgagent_kg__get_project()    # Load project context
mcp__agentkgagent_kg__create_summary() # End-of-session summary
```

---

## Implementation Timeline

### Phase 1 (Month 1): Foundation
- Define schema for AgentKG nodes/edges
- Build SQLite storage + query layer
- Integrate LanceDB for semantic search
- Create basic CLI (`claude memory list/query/delete`)

### Phase 2 (Month 2): Agent Integration
- Update Claude Code to load AgentKG at startup
- Add preference learning system
- Implement project context detection
- Test with pilot users

### Phase 3 (Month 3): Refinement
- Add session summarization
- Build pattern recognition engine
- Implement confidence scoring
- Add export/import for portability

### Phase 4 (Month 4): Advanced Features
- Cloud sync (encrypted, optional)
- Multi-agent coordination
- Team collaboration features
- Analytics dashboard (local, optional)

---

## Why This Matters

**Right now:** Claude is helpful but stateless. Every session resets.

**With AgentKG:** Claude becomes your agent. Your preferences matter. Your decisions are remembered. Your patterns are learned.

**You don't get a smarter AI. You get a more *you*-aware AI.**

That's the difference between a tool and a teammate.

---

## The Big Picture

**Knowledge stack:**
1. **CodeKG** — What's in your code
2. **KGRAG** — What the world knows
3. **AgentKG** — What we decided together

**That's the full picture. That's how agents become truly useful.**

Agent memory in ~/.Claude is the missing piece that makes it all cohere.

---

**—The AgentKG in ~/.Claude Vision**
