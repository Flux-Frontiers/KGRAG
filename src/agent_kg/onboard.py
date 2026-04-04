"""onboard.py — Structured onboarding interview for AgentKG UserProfile.

Conducts a four-phase interview to populate the UserProfile tree on first use.
Also handles implicit updates from conversation turns (when user says
"always do X" or "I prefer Y", the profile is updated without a full interview).

Usage:
  Run ``agent_kg onboard`` from the CLI, or call :func:`run_onboard_interview`
  from code. Answers are parsed by the NLP pipeline and stored as typed nodes.

Re-runnable: ``agent_kg onboard --update`` to refine preferences.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent_kg.profile import UserProfileStore

# Interview phases and questions
_PHASES: list[dict[str, Any]] = [
    {
        "name": "Identity & Context",
        "questions": [
            {"key": "name", "prompt": "What's your name?", "kind": "context"},
            {"key": "role", "prompt": "What's your primary role? (e.g. 'Python developer', 'ML engineer')", "kind": "context"},
            {"key": "projects", "prompt": "What projects are you mainly working in?", "kind": "context"},
            {"key": "machine", "prompt": "What machine/OS are you on? (e.g. 'macOS M3', 'Ubuntu 24.04')", "kind": "context"},
        ],
    },
    {
        "name": "Coding Style",
        "questions": [
            {"key": "language", "prompt": "Preferred language(s) and style conventions?", "kind": "preference"},
            {"key": "docstrings", "prompt": "Docstring format? (Google / NumPy / Sphinx / none)", "kind": "style"},
            {"key": "verbosity", "prompt": "How verbose do you want my responses? (concise / detailed / adaptive)", "kind": "preference"},
            {"key": "rules", "prompt": "Any standing rules I should always follow? (one per line, blank to skip)", "kind": "commitment"},
        ],
    },
    {
        "name": "Domain Expertise",
        "questions": [
            {"key": "strong_domains", "prompt": "What are your strongest technical domains?", "kind": "expertise"},
            {"key": "learning", "prompt": "What are you currently learning or exploring?", "kind": "interest"},
        ],
    },
    {
        "name": "Personal (optional)",
        "optional": True,
        "questions": [
            {"key": "hobbies", "prompt": "Any hobbies or interests you'd like me to know about? (blank to skip)", "kind": "interest"},
            {"key": "collaboration", "prompt": "Anything that helps us work better together? (blank to skip)", "kind": "preference"},
        ],
    },
]


def run_onboard_interview(
    profile: "UserProfileStore",
    input_fn=None,
    print_fn=None,
    skip_optional: bool = False,
) -> dict[str, Any]:
    """Conduct the structured onboarding interview.

    :param profile: :class:`~agent_kg.profile.UserProfileStore` to populate.
    :param input_fn: Callable for getting user input (default: builtin ``input``).
    :param print_fn: Callable for output (default: builtin ``print``).
    :param skip_optional: If True, skip the optional Personal phase.
    :return: Dict of ``{phase_name: {question_key: answer}}`` for all answers.
    """
    from agent_kg.schema import NodeKind  # noqa: PLC0415

    _input = input_fn or input
    _print = print_fn or print

    _KIND_MAP = {
        "context": NodeKind.CONTEXT,
        "preference": NodeKind.PREFERENCE,
        "style": NodeKind.STYLE,
        "commitment": NodeKind.COMMITMENT,
        "expertise": NodeKind.EXPERTISE,
        "interest": NodeKind.INTEREST,
    }

    all_answers: dict[str, Any] = {}

    _print("\n=== AgentKG Onboarding ===")
    _print("Let me learn a bit about you so I can work better with you.\n")

    for phase in _PHASES:
        if phase.get("optional") and skip_optional:
            continue

        _print(f"\n--- Phase: {phase['name']} ---")

        phase_answers: dict[str, str] = {}
        for q in phase["questions"]:
            prompt = q["prompt"]
            kind_str = q["kind"]
            node_kind = _KIND_MAP.get(kind_str, NodeKind.PREFERENCE)
            key = q["key"]

            try:
                answer = _input(f"{prompt}\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                answer = ""

            if not answer:
                continue

            phase_answers[key] = answer

            # Handle multi-line inputs (rules, hobbies)
            if "\n" in answer:
                for line in answer.splitlines():
                    line = line.strip()
                    if line:
                        profile.upsert(kind=node_kind, label=line[:80], text=line)
            else:
                profile.upsert(kind=node_kind, label=answer[:80], text=answer)

        all_answers[phase["name"]] = phase_answers

    _print("\n=== Onboarding complete! ===")
    stats = profile.stats()
    _print(f"Stored {stats['total']} profile facts across {len(stats['by_kind'])} categories.\n")

    return all_answers


def apply_implicit_update(
    profile: "UserProfileStore",
    updates: list[dict[str, Any]],
) -> int:
    """Apply NLP-extracted preference/commitment/expertise updates to the profile.

    Called automatically after each user turn by :func:`~agent_kg.ingest.ingest_turn`.

    :param profile: The UserProfile store to update.
    :param updates: List of ``{"kind", "label", "text"}`` dicts from the NLP pipeline.
    :return: Number of nodes upserted.
    """
    nodes = profile.apply_updates(updates)
    return len(nodes)
