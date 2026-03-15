"""cli.py — Command-line entry point for the diary transformer.

Can be invoked as::

    python -m diary_transformer [options] <input> <output>

or via the ``diary_transformer`` console-script entry point if the package
is installed.
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path


def main() -> None:
    """Parse arguments and run the appropriate transformation workflow."""
    warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*")

    parser = argparse.ArgumentParser(
        description="Diary Transformer: convert diary entries into semantic memory chunks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # Positional (optional) + flag alternatives for input / output
    parser.add_argument("input", nargs="?", help="Input diary file (positional)")
    parser.add_argument("output", nargs="?", help="Output file (positional)")
    parser.add_argument("--input", "-i", dest="input_file")
    parser.add_argument("--output", "-o", dest="output_file")

    # Processing knobs
    parser.add_argument("--chunk-size", "-c", type=int, default=512)
    parser.add_argument(
        "--chunking-strategy",
        choices=["semantic", "sentence_group", "hybrid"],
        default="sentence_group",
    )
    parser.add_argument("--sentences-per-chunk", type=int, default=4)
    parser.add_argument("--batch-size", "-b", type=int, default=20)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--max-chunks-per-entry", "-m", type=int, default=3)
    parser.add_argument("--workers", "-w", type=int, default=1)
    parser.add_argument("--topics-file", "-t")

    # Cache management
    parser.add_argument("--clear", action="store_true", help="Clear all caches before running")
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Clear injection state + chunk cache (preserve diversity cache)",
    )

    # Incremental / resume
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--incremental", action="store_true", help="Alias for --resume")
    parser.add_argument("--state-file")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    if args.incremental:
        args.resume = True

    input_arg = args.input_file or args.input
    output_arg = args.output_file or args.output

    if not input_arg:
        print("Error: input file required (positional or --input)")
        sys.exit(1)
    if not output_arg:
        print("Error: output file required (positional or --output)")
        sys.exit(1)

    input_path = Path(input_arg)
    output_path = Path(output_arg)

    if not input_path.exists():
        print(f"Error: input file not found: {input_path}")
        sys.exit(1)

    # Cache / state file paths
    state_file = Path(args.state_file) if args.state_file else output_path.parent / ".diary_state.json"

    # --clear: wipe feature + chunk caches
    if args.clear:
        import shutil
        cache_dir = input_path.parent / ".diary_cache"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            print(f"✓ Cleared feature cache: {cache_dir}")
        for ext in (".pkl", ".json"):
            p = input_path.parent / f"{input_path.stem}_chunks{ext}"
            if p.exists():
                p.unlink()
                print(f"✓ Cleared chunk cache: {p}")

    # --restart: wipe state + chunk cache only
    if args.restart:
        if state_file.exists():
            state_file.unlink()
            print(f"✓ Cleared state: {state_file}")
        for ext in (".pkl", ".json"):
            p = input_path.parent / f"{input_path.stem}_chunks{ext}"
            if p.exists():
                p.unlink()
                print(f"✓ Cleared chunk cache: {p}")

    print("Starting Diary Transformation")
    if args.resume:
        print(f"  Mode: Resume  |  State: {state_file}")
    print(f"  Input: {input_path}  ->  Output: {output_path}")
    print(f"  Strategy: {args.chunking_strategy}  |  Chunk size: {args.chunk_size}  |  Batch: {args.batch_size}")

    try:
        from .transformer import DiaryTransformer

        transformer = DiaryTransformer(
            max_chunk_length=args.chunk_size,
            num_workers=args.workers,
            topics_file=args.topics_file,
            chunking_strategy=args.chunking_strategy,
            sentences_per_chunk=args.sentences_per_chunk,
        )

        if args.resume:
            transformer.transform_file_incremental(
                str(input_path),
                str(output_path),
                str(state_file),
                batch_size=args.batch_size,
                seed=args.seed,
                max_chunks_per_entry=args.max_chunks_per_entry,
                resume_mode=True,
            )
        else:
            transformer.transform_file(
                str(input_path),
                str(output_path),
                batch_size=args.batch_size,
                seed=args.seed,
                max_chunks_per_entry=args.max_chunks_per_entry,
            )

        print(f"\nDone! Output: {output_path}")
        if args.resume:
            print(f"State: {state_file}")

    except KeyboardInterrupt:
        print("\nCancelled")
        sys.exit(1)
    except Exception as exc:
        import traceback
        print(f"\nError: {exc}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
