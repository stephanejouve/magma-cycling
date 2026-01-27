#!/usr/bin/env python3
"""
Split large JSONL session files into manageable chunks.

Purpose:
- Break down massive session logs (10K+ lines, 30MB+) into smaller files
- Improve readability and Git performance
- Generate navigation index for chunk browsing

Usage:
    python split_session_logs.py <input.jsonl> [--chunk-size 1500] [--compress]
    python split_session_logs.py project-docs/sessions/SESSION_R9E_PHASE1_25JAN2026.jsonl

Output:
    input_chunk001.jsonl, input_chunk002.jsonl, ...
    input_INDEX.md (navigation guide)
"""

import argparse
import gzip
import json
import sys
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any


def parse_jsonl_entry(line: str) -> dict[str, Any] | None:
    """Parse a single JSONL line, return dict or None if invalid."""
    try:
        return json.loads(line.strip())
    except json.JSONDecodeError:
        return None


def extract_metadata(entry: dict[str, Any]) -> dict[str, Any]:
    """Extract useful metadata from a JSONL entry."""
    return {
        "timestamp": entry.get("timestamp", "unknown"),
        "type": entry.get("type", "unknown"),
        "role": entry.get("message", {}).get("role") if "message" in entry else None,
        "uuid": entry.get("uuid", ""),
    }


def read_jsonl_chunks(
    file_path: Path, chunk_size: int = 1500
) -> Iterator[tuple[list[str], list[dict[str, Any]]]]:
    """
    Read JSONL file and yield chunks of lines with their metadata.

    Args:
        file_path: Path to JSONL file
        chunk_size: Number of lines per chunk

    Yields:
        (lines, metadata_list) tuples
    """
    chunk_lines = []
    chunk_metadata = []

    with open(file_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            chunk_lines.append(line)
            entry = parse_jsonl_entry(line)
            if entry:
                chunk_metadata.append(extract_metadata(entry))

            if len(chunk_lines) >= chunk_size:
                yield chunk_lines, chunk_metadata
                chunk_lines = []
                chunk_metadata = []

        # Yield remaining lines
        if chunk_lines:
            yield chunk_lines, chunk_metadata


def write_chunk(output_path: Path, lines: list[str], compress: bool = False) -> Path:
    """Write chunk to file, optionally compressed."""
    if compress:
        output_path = output_path.with_suffix(output_path.suffix + ".gz")
        with gzip.open(output_path, "wt", encoding="utf-8") as f:
            f.writelines(lines)
    else:
        with open(output_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    return output_path


def generate_index(
    base_name: str,
    chunks_info: list[dict[str, Any]],
    output_dir: Path,
) -> Path:
    """Generate navigation index for chunks."""
    index_path = output_dir / f"{base_name}_INDEX.md"

    total_lines = sum(c["line_count"] for c in chunks_info)
    total_size = sum(c["size_bytes"] for c in chunks_info)

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(f"# Session Log Index: {base_name}\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Total chunks:** {len(chunks_info)}\n")
        f.write(f"**Total lines:** {total_lines:,}\n")
        f.write(f"**Total size:** {total_size / 1024 / 1024:.1f} MB\n\n")
        f.write("---\n\n")
        f.write("## Chunks\n\n")

        for i, chunk in enumerate(chunks_info, 1):
            f.write(f"### Chunk {i:03d}\n\n")
            f.write(f"**File:** `{chunk['filename']}`\n")
            f.write(f"**Lines:** {chunk['line_count']:,}\n")
            f.write(f"**Size:** {chunk['size_bytes'] / 1024:.1f} KB\n")

            if chunk.get("first_timestamp"):
                f.write(f"**Start:** {chunk['first_timestamp']}\n")
            if chunk.get("last_timestamp"):
                f.write(f"**End:** {chunk['last_timestamp']}\n")

            f.write(f"**Messages:** {chunk['message_count']}\n")
            f.write("\n")

        f.write("---\n\n")
        f.write("## Navigation\n\n")
        f.write("Use `grep` to find specific content:\n")
        f.write("```bash\n")
        f.write(f"grep -n 'pattern' {base_name}_chunk*.jsonl\n")
        f.write("```\n\n")
        f.write("Read specific chunk:\n")
        f.write("```bash\n")
        f.write(f"less {base_name}_chunk001.jsonl\n")
        f.write("```\n")

    return index_path


def split_session_log(
    input_path: Path,
    chunk_size: int = 1500,
    compress: bool = False,
    output_dir: Path | None = None,
) -> tuple[list[Path], Path]:
    """
    Split large JSONL session file into chunks.

    Args:
        input_path: Path to input JSONL file
        chunk_size: Lines per chunk
        compress: Whether to gzip chunks
        output_dir: Output directory (default: same as input)

    Returns:
        (chunk_paths, index_path) tuple
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if output_dir is None:
        output_dir = input_path.parent

    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = input_path.stem
    chunk_paths = []
    chunks_info = []

    print(f"Splitting {input_path.name}...")
    print(f"Chunk size: {chunk_size} lines")
    print(f"Output dir: {output_dir}")
    print()

    for chunk_num, (lines, metadata) in enumerate(
        read_jsonl_chunks(input_path, chunk_size), start=1
    ):
        chunk_filename = f"{base_name}_chunk{chunk_num:03d}.jsonl"
        chunk_path = output_dir / chunk_filename

        written_path = write_chunk(chunk_path, lines, compress)
        chunk_paths.append(written_path)

        # Extract timestamps
        timestamps = [m["timestamp"] for m in metadata if m["timestamp"] != "unknown"]
        message_count = sum(1 for m in metadata if m["type"] == "assistant" or m["type"] == "user")

        chunk_info = {
            "filename": written_path.name,
            "line_count": len(lines),
            "size_bytes": written_path.stat().st_size,
            "first_timestamp": timestamps[0] if timestamps else None,
            "last_timestamp": timestamps[-1] if timestamps else None,
            "message_count": message_count,
        }
        chunks_info.append(chunk_info)

        print(f"✓ Chunk {chunk_num:03d}: {len(lines):,} lines → {written_path.name}")

    print()
    print(f"Generated {len(chunk_paths)} chunks")

    # Generate index
    index_path = generate_index(base_name, chunks_info, output_dir)
    print(f"✓ Index: {index_path.name}")

    return chunk_paths, index_path


def main():
    """Main entry point for session log splitting CLI."""
    parser = argparse.ArgumentParser(
        description="Split large JSONL session logs into manageable chunks"
    )
    parser.add_argument("input", type=Path, help="Input JSONL file path")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1500,
        help="Lines per chunk (default: 1500)",
    )
    parser.add_argument(
        "--compress",
        action="store_true",
        help="Compress chunks with gzip",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory (default: same as input)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without writing files",
    )
    parser.add_argument(
        "--summarize",
        action="store_true",
        help="Generate automatic summary after splitting",
    )

    args = parser.parse_args()

    if args.dry_run:
        print("[DRY RUN MODE]")
        print(f"Would split: {args.input}")
        print(f"Chunk size: {args.chunk_size}")
        print(f"Compress: {args.compress}")
        print(f"Output dir: {args.output_dir or args.input.parent}")
        sys.exit(0)

    try:
        chunk_paths, index_path = split_session_log(
            args.input,
            chunk_size=args.chunk_size,
            compress=args.compress,
            output_dir=args.output_dir,
        )

        print()
        print("✅ Split completed successfully!")
        print(f"📁 Chunks: {len(chunk_paths)}")
        print(f"📋 Index: {index_path}")

        # Generate summary if requested
        if args.summarize:
            print()
            print("Generating summary...")
            try:
                # Import summarizer
                sys.path.insert(0, str(args.input.parent.parent.parent / "scripts" / "maintenance"))
                from session_summarizer import summarize_session

                summary_text, summary_path = summarize_session(args.input)
                print(f"✅ Summary: {summary_path}")
            except Exception as e:
                print(f"⚠️  Summary generation failed: {e}")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
