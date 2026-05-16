"""
test_local.py — smoke-test the handler without Docker or RunPod.

Usage (from kgrag/runpod/):
    KG_VOLUME=/path/to/local/indices python test_local.py
"""

import os
import sys

# Allow running from the runpod/ directory with local source trees
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set volume path to local repos if not overridden
if "KG_VOLUME" not in os.environ:
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    # Build a temp volume-like dir pointing at the actual repos
    import pathlib
    import tempfile

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="kgrag_vol_"))
    (tmp / "gutenberg_kg").symlink_to(pathlib.Path(base) / "gutenberg_kg")
    (tmp / "metabo_kg").symlink_to(pathlib.Path(base) / "Metabo_kg")
    os.environ["KG_VOLUME"] = str(tmp)
    print(f"[test] Using local volume symlink at {tmp}")

# Import handler (triggers startup bootstrap)
import handler  # noqa: E402

TEST_CASES = [
    {
        "input": {
            "query": "Marcus Aurelius on suffering and stoic virtue",
            "corpus": "gutenberg",
            "k": 4,
        }
    },
    {
        "input": {
            "query": "glycolysis pathway ATP production",
            "corpus": "metabo_hsa",
            "k": 4,
        }
    },
    {
        "input": {
            "query": "redemption and moral transformation",
            "corpus": "all",
            "k": 5,
            "semantic_floor": 0.3,
        }
    },
]

for i, job in enumerate(TEST_CASES, 1):
    print(f"\n{'=' * 60}")
    print(f"Test {i}: {job['input']['query'][:60]}")
    print(f"Corpus: {job['input']['corpus']}")
    result = handler.handler(job)
    if "error" in result:
        print(f"ERROR: {result['error']}")
    else:
        print(f"  kgs_queried={result['kgs_queried']}  total_hits={result['total_hits']}")
        for h in result["hits"]:
            print(f"  [{h['score']:.3f}] {h['kg_name']} | {h['source_path']} | {h['summary'][:80]}")

print("\nAll tests done.")
