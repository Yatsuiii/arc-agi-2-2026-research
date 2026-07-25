"""Ingest RUN-001's Kaggle kernel outputs: status, download, checksum, validate.

Read-only towards Kaggle: this module only ever queries kernel status and
downloads outputs. It never pushes, versions, cancels, or otherwise mutates
the kernel. Downloaded files are written exactly as the Kaggle CLI produces
them; nothing here parses or rewrites their bytes before checksumming.

Refuses to download while the kernel is still `RUNNING` or `QUEUED` (pass
`--force` to override, e.g. to snapshot a stuck run's partial output).

Run: `python -m src.run001.download_outputs [--kernel REF] [--dest DIR]`
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.run001.validate_outputs import NONTERMINAL_KERNEL_STATUSES, validate

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KERNEL = "redlotusthepotus/run001-nvarc-t4x2-baseline"
DEFAULT_DEST = ROOT / "artifacts" / "run001"
TERMINAL_STATUSES = {"COMPLETE", "ERROR", "CANCELLED"}


class KernelNotFinished(RuntimeError):
    """Raised when a download is attempted before the kernel reaches a terminal state."""


def kernel_status(kernel_ref: str, kaggle_bin: str = "kaggle") -> str:
    """Query the kernel's current status via the Kaggle CLI. Read-only.

    Parses the bare status token (e.g. "COMPLETE") out of the CLI's
    `has status "KernelWorkerStatus.X"` sentence.
    """
    result = subprocess.run(
        [kaggle_bin, "kernels", "status", kernel_ref],
        capture_output=True,
        text=True,
        check=True,
    )
    text = result.stdout.strip()
    marker = "KernelWorkerStatus."
    if marker not in text:
        raise RuntimeError(f"unrecognised kaggle status output: {text!r}")
    return text.split(marker, 1)[1].rstrip('"').strip()


def download_outputs(kernel_ref: str, dest_dir: Path, kaggle_bin: str = "kaggle") -> None:
    """Pull every kernel output file into `dest_dir`, byte-for-byte.

    `kaggle kernels output` writes files as Kaggle produced them; this
    function does not touch their contents.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [kaggle_bin, "kernels", "output", kernel_ref, "-p", str(dest_dir)],
        check=True,
    )


def checksum_files(dest_dir: Path) -> dict[str, str]:
    """sha256 of every regular file under `dest_dir`, excluding our own bookkeeping files."""
    exclude = {"checksums.json", "ingestion_manifest.json"}
    checksums: dict[str, str] = {}
    for path in sorted(dest_dir.rglob("*")):
        if not path.is_file() or path.name in exclude:
            continue
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        checksums[str(path.relative_to(dest_dir))] = digest.hexdigest()
    return checksums


def write_checksums(dest_dir: Path, checksums: dict[str, str]) -> Path:
    path = dest_dir / "checksums.json"
    path.write_text(json.dumps(checksums, indent=2, sort_keys=True) + "\n")
    return path


def update_ingestion_manifest(dest_dir: Path, **fields) -> Path:
    """Record ingestion-time facts alongside, not inside, the run's own manifest.

    A separate file: `run_manifest*.json` is the solver's own record of what
    it did, and ingestion (which happens after the fact, on a different
    machine) must not alter it.
    """
    path = dest_dir / "ingestion_manifest.json"
    existing = json.loads(path.read_text()) if path.exists() else {}
    existing.update(fields)
    existing["ingested_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n")
    return path


def ingest(
    kernel_ref: str = DEFAULT_KERNEL,
    dest_dir: Path = DEFAULT_DEST,
    kaggle_bin: str = "kaggle",
    force: bool = False,
) -> dict:
    """Status -> download -> checksum -> validate -> classify -> manifest.

    Each stage's output feeds the next; this is the one entry point the
    checklist and any caller should use rather than composing the pieces
    themselves.
    """
    status = kernel_status(kernel_ref, kaggle_bin)
    if status in NONTERMINAL_KERNEL_STATUSES and not force:
        raise KernelNotFinished(
            f"kernel status is {status!r}, not terminal; refusing to download "
            "(pass force=True to override)"
        )

    download_outputs(kernel_ref, dest_dir, kaggle_bin)
    checksums = checksum_files(dest_dir)
    write_checksums(dest_dir, checksums)

    report = validate(dest_dir, kernel_status=status)

    manifest_path = update_ingestion_manifest(
        dest_dir,
        kernel_ref=kernel_ref,
        kernel_status=status,
        classification=report["classification"],
        n_files_downloaded=len(checksums),
        validation_ok=report["ok"],
    )
    return {
        "kernel_status": status,
        "classification": report["classification"],
        "manifest_path": str(manifest_path),
        "report": report,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel", default=DEFAULT_KERNEL)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--kaggle-bin", default="kaggle")
    parser.add_argument(
        "--force",
        action="store_true",
        help="download even if the kernel has not reached a terminal state",
    )
    args = parser.parse_args()

    try:
        result = ingest(args.kernel, args.dest, args.kaggle_bin, args.force)
    except KernelNotFinished as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 2

    summary = {k: v for k, v in result.items() if k != "report"}
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(result["report"], indent=2, sort_keys=True))
    return 0 if result["report"]["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
