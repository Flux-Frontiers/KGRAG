#!/usr/bin/env python3
"""
Diary Transformer Example

Demonstrates how to use the DiaryTransformer for various diary formats.

Run with:
    poetry run python pepys/diary_transformer_example.py
"""

from pathlib import Path

from personal_agent.tools.diary_transformer import DiaryTransformer


def example_basic_usage():
    """Basic usage example with default settings."""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)

    transformer = DiaryTransformer(
        max_chunk_length=512,
        num_workers=1,
    )

    transformer.transform_file(
        input_path="my_diary.txt",
        output_path="transformed_diary.txt",
        batch_size=20,
        seed=42,
    )


def example_parallel_processing():
    """Example with parallel processing for large diaries."""
    print("=" * 60)
    print("Example 2: Parallel Processing")
    print("=" * 60)

    transformer = DiaryTransformer(
        max_chunk_length=512,
        num_workers=4,
    )

    transformer.transform_file(
        input_path="large_diary.txt",
        output_path="transformed_large.txt",
        batch_size=50,
        max_chunks_per_entry=3,
    )


def example_custom_topics():
    """Example with custom topic classification."""
    print("=" * 60)
    print("Example 3: Custom Topics")
    print("=" * 60)

    transformer = DiaryTransformer(
        max_chunk_length=512,
        num_workers=2,
        topics_file="custom_topics.yaml",
    )

    transformer.transform_file(
        input_path="specialized_diary.txt",
        output_path="transformed_specialized.txt",
        batch_size=20,
        seed=12345,
    )


def example_pepys_diary():
    """Example with Pepys historical diary (17th-century)."""
    print("=" * 60)
    print("Example 4: Pepys Historical Diary")
    print("=" * 60)

    # Option 1: Use default topics (includes both general + pepys categories)
    print("\nOption 1: Default topics (general + pepys)")
    _transformer_default = DiaryTransformer(num_workers=4)

    # Option 2: Use pepys-only topics (17th-century vocabulary only)
    print("\nOption 2: Pepys-only topics (historical)")
    _transformer_pepys = DiaryTransformer(
        topics_file="pepys/pepys_topics.yaml",
        num_workers=4,
    )

    print("\n✓ Both configurations support Pepys diary processing")
    print("  - Default: Works with any diary type (general + specialized)")
    print("  - Pepys-only: Optimized for 17th-century historical text")


def example_create_sample_diary():
    """Create a sample diary file for testing."""
    print("=" * 60)
    print("Creating Sample Diary")
    print("=" * 60)

    sample_entries = [
        "2024-01-15T09:00 | raw | DiaryEntry | Today I woke up early and went for a morning run. The weather was perfect.",
        "2024-01-15T12:30 | raw | DiaryEntry | Had lunch with my colleague Sarah. We discussed the new project deadline.",
        "2024-01-15T18:00 | raw | DiaryEntry | Finished work and spent the evening reading a book about machine learning.",
        "2024-01-16T10:00 | raw | DiaryEntry | Started working on the quarterly report. Need to finish by Friday.",
        "2024-01-16T14:30 | raw | DiaryEntry | Attended team meeting. Discussed budget concerns for next quarter.",
        "2024-01-16T19:00 | raw | DiaryEntry | Cooked dinner and watched a movie. Feeling relaxed.",
        "2024-01-17T08:30 | raw | DiaryEntry | Morning coffee with John. He told me about his vacation plans.",
        "2024-01-17T13:00 | raw | DiaryEntry | Worked on code review for the authentication module.",
        "2024-01-17T17:30 | raw | DiaryEntry | Gym session after work. Did strength training.",
        "2024-01-18T09:30 | raw | DiaryEntry | Meeting with the product team about new features.",
    ]

    output_path = Path("sample_diary.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sample_entries))

    print(f"✓ Created sample diary: {output_path}")
    print(f"  Entries: {len(sample_entries)}")
    return str(output_path)


def example_transform_sample():
    """Complete example: create sample diary and transform it."""
    print("=" * 60)
    print("Complete Example: Sample Diary Transformation")
    print("=" * 60)

    input_path = example_create_sample_diary()

    print("\nInitializing DiaryTransformer...")
    transformer = DiaryTransformer(
        max_chunk_length=512,
        num_workers=1,
    )

    print("\nTransforming diary...")
    output_path = "sample_transformed.txt"
    transformer.transform_file(
        input_path=input_path,
        output_path=output_path,
        batch_size=5,
        seed=42,
        max_chunks_per_entry=2,
    )

    print("\n✓ Transformation complete!")
    print(f"  Input: {input_path}")
    print(f"  Output: {output_path}")
    print(f"\nView output with: cat {output_path}")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("DIARY TRANSFORMER EXAMPLES")
    print("=" * 60 + "\n")

    example_transform_sample()

    print("\n" + "=" * 60)
    print("OTHER USAGE PATTERNS")
    print("=" * 60)
    print("\n1. Basic usage:")
    print("   transformer = DiaryTransformer()")
    print('   transformer.transform_file("diary.txt", "output.txt")')

    print("\n2. Parallel processing:")
    print("   transformer = DiaryTransformer(num_workers=4)")
    print("   transformer.transform_file(...)")

    print("\n3. Custom topics:")
    print('   transformer = DiaryTransformer(topics_file="custom.yaml")')
    print("   transformer.transform_file(...)")

    print("\n4. Pepys historical diary:")
    print("   # Option A: Default (includes general + pepys topics)")
    print("   transformer = DiaryTransformer()")
    print("   # Option B: Pepys-only (17th-century vocabulary)")
    print('   transformer = DiaryTransformer(topics_file="pepys/pepys_topics.yaml")')

    print("\n5. CLI usage:")
    print("   poetry run python -m personal_agent.tools.diary_transformer \\")
    print("       input.txt output.txt --workers 4 --batch-size 20")
    print("   # With pepys topics:")
    print("   poetry run python -m personal_agent.tools.diary_transformer \\")
    print("       pepys_diary.txt output.txt --topics-file pepys/pepys_topics.yaml")


if __name__ == "__main__":
    main()
