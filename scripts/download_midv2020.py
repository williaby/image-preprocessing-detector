#!/usr/bin/env python3
"""Download MIDV-2020 dataset (photo + scans, no video) via SFTP.

Credentials are read from environment variables — never hardcode them:

    export MIDV2020_SFTP_HOST="l3i-share.univ-lr.fr"
    export MIDV2020_SFTP_USER="<user>"
    export MIDV2020_SFTP_PASSWORD="<password>"

Or put them in a .env file (git-ignored) and load it with:

    set -a && source .env && set +a

Usage:
    # Dry-run: list what would be downloaded
    uv run python scripts/download_midv2020.py --dry-run

    # Download to default location
    uv run python scripts/download_midv2020.py

    # Download and auto-extract
    uv run python scripts/download_midv2020.py --extract

    # Custom output path
    uv run python scripts/download_midv2020.py \\
        --output /mnt/e/image_detection/01_base_data/documents/midv2020

    # Download TIF scans too (large — 28 GB extra)
    uv run python scripts/download_midv2020.py --include-tif

Dependencies:
    paramiko  (installed via uv sync --extra dev)
    tqdm      (optional, for progress bars)

Dataset layout on server (MIDV2020/dataset/):

    photo.tar           [3.8 GB]  — camera stills (1000 JPGs + annotations)
    scan_upright.tar    [1.1 GB]  — flatbed upright JPG (1000 + annotations)
    scan_rotated.tar    [1.1 GB]  — flatbed rotated JPG (1000 + annotations)
    templates.tar       [0.8 GB]  — reference template images + annotations
    scan_upright_tif.tar [24.9 GB] — upright TIF (optional, --include-tif)
    scan_rotated_tif.tar  [3.0 GB] — rotated TIF (optional, --include-tif)
    clips.tar           [9.8 GB]  — video frames (EXCLUDED)
    clips_video.tar    [49.1 GB]  — raw video (EXCLUDED)

MD5 checksums (from server md5.txt):
    e716b2044a0af872cb21c9dc2f51d752  photo.tar
    f6e0aeb6981a89aa2dfc717575fcea28  scan_upright.tar
    3db227b453121b7e0a8c152e79988edf  scan_rotated.tar
    5bf6bd22df4808d4c8df9500e01f4f0a  templates.tar
    03d98443b30a905780277ac566157b30  scan_rotated_tif.tar
    379e7b098166696b6ae28fbee5bc84da  scan_upright_tif.tar

Document types (10 total):
    alb_id, aze_passport, esp_id, est_id, fin_id,
    grc_passport, lva_passport, rus_internalpassport,
    srb_passport, svk_id

Scripts: Latin (7), Cyrillic (2: rus, srb), Greek (1: grc)

Camera capture conditions (100 images per doc type):
    00-09 iPhone / 10-19 Samsung  — projective distortions
    20-24 iPhone / 25-29 Samsung  — text documents background
    30-34 iPhone / 35-39 Samsung  — keyboard background
    40-44 iPhone / 45-49 Samsung  — outdoors natural lighting
    50-54 iPhone / 55-59 Samsung  — table background
    60-64 iPhone / 65-69 Samsung  — highlight present
    70-79 iPhone / 80-89 Samsung  — low lighting
    90-94 iPhone / 95-99 Samsung  — cloth background

License:
    Creative Commons Attribution-ShareAlike 2.5 Generic (CC BY-SA 2.5)
    https://creativecommons.org/licenses/by-sa/2.5/
    Face images courtesy of Generated Photos (attribution required in derivatives).
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import sys
import tarfile
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_SFTP_HOST = "l3i-share.univ-lr.fr"
DEFAULT_SFTP_PORT = 22
REMOTE_BASE = "/MIDV2020/dataset"
DEFAULT_OUTPUT_DIR = Path("/mnt/e/image_detection/01_base_data/documents/midv2020")

# Tar files we always download (camera + flatbed JPG + templates)
REQUIRED_TARS: list[str] = [
    "photo.tar",
    "scan_upright.tar",
    "scan_rotated.tar",
    "templates.tar",
]

# Optional TIF scans (large — only with --include-tif)
OPTIONAL_TIF_TARS: list[str] = [
    "scan_rotated_tif.tar",
    "scan_upright_tif.tar",
]

# MD5 checksums from server md5.txt
KNOWN_MD5: dict[str, str] = {
    "photo.tar": "e716b2044a0af872cb21c9dc2f51d752",
    "scan_upright.tar": "f6e0aeb6981a89aa2dfc717575fcea28",
    "scan_rotated.tar": "3db227b453121b7e0a8c152e79988edf",
    "templates.tar": "5bf6bd22df4808d4c8df9500e01f4f0a",
    "scan_rotated_tif.tar": "03d98443b30a905780277ac566157b30",
    "scan_upright_tif.tar": "379e7b098166696b6ae28fbee5bc84da",
}

# Approximate sizes for progress reporting (bytes)
APPROX_SIZE: dict[str, int] = {
    "photo.tar": 4_003_000_000,
    "scan_upright.tar": 1_149_000_000,
    "scan_rotated.tar": 1_123_000_000,
    "templates.tar": 863_000_000,
    "scan_rotated_tif.tar": 3_153_000_000,
    "scan_upright_tif.tar": 26_123_000_000,
}


# ---------------------------------------------------------------------------
# Credential helpers
# ---------------------------------------------------------------------------


def _read_credentials() -> tuple[str, str, str, int]:
    """Read SFTP credentials from environment variables.

    Returns:
        Tuple of (host, username, password, port).

    Raises:
        SystemExit: If required variables are missing.
    """
    host = os.environ.get("MIDV2020_SFTP_HOST", DEFAULT_SFTP_HOST)
    user = os.environ.get("MIDV2020_SFTP_USER", "")
    password = os.environ.get("MIDV2020_SFTP_PASSWORD", "")
    port = int(os.environ.get("MIDV2020_SFTP_PORT", str(DEFAULT_SFTP_PORT)))

    missing = [
        v
        for v, val in [
            ("MIDV2020_SFTP_USER", user),
            ("MIDV2020_SFTP_PASSWORD", password),
        ]
        if not val
    ]

    if missing:
        log.error(
            "Missing required environment variables: %s\n"
            "  export MIDV2020_SFTP_USER='<username>'\n"
            "  export MIDV2020_SFTP_PASSWORD='<password>'",
            ", ".join(missing),
        )
        sys.exit(1)

    return host, user, password, port


# ---------------------------------------------------------------------------
# SFTP connection
# ---------------------------------------------------------------------------


def _open_connection(
    host: str, user: str, password: str, port: int
) -> tuple[object, object]:
    """Open SSH + SFTP connection using SSHClient (supports keyboard-interactive).

    Args:
        host: SFTP hostname.
        user: Username.
        password: Password.
        port: Port number.

    Returns:
        Tuple of (ssh_client, sftp_client).
    """
    try:
        import paramiko as _p
    except ImportError:
        log.error(
            "paramiko is not installed.\n"
            "  uv add paramiko\n"
            "Or use FileZilla with the credentials from your secure notes."
        )
        sys.exit(1)

    client = _p.SSHClient()
    client.set_missing_host_key_policy(_p.AutoAddPolicy())
    client.connect(
        host,
        port=port,
        username=user,
        password=password,
        timeout=30,
        allow_agent=False,
        look_for_keys=False,
    )
    sftp = client.open_sftp()
    return client, sftp


# ---------------------------------------------------------------------------
# MD5 verification
# ---------------------------------------------------------------------------


def _md5_of_file(path: Path, chunk: int = 1 << 20) -> str:
    """Compute MD5 hex digest of a local file.

    Args:
        path: Path to the file.
        chunk: Read chunk size in bytes.

    Returns:
        Lowercase hex MD5 string.
    """
    h = hashlib.md5()
    with open(path, "rb") as fh:
        while True:
            data = fh.read(chunk)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def _verify_md5(path: Path, tar_name: str) -> bool:
    """Check that a downloaded tar matches its known MD5.

    Args:
        path: Local path of the downloaded file.
        tar_name: Filename key for KNOWN_MD5 lookup.

    Returns:
        True if checksum matches or no checksum is known.
    """
    expected = KNOWN_MD5.get(tar_name)
    if not expected:
        log.warning("No known MD5 for %s — skipping checksum", tar_name)
        return True
    log.info("Verifying MD5 for %s …", tar_name)
    actual = _md5_of_file(path)
    if actual == expected:
        log.info("  ✓ MD5 OK")
        return True
    log.error("  ✗ MD5 MISMATCH: expected %s, got %s", expected, actual)
    return False


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


def _download_tar(
    sftp: object,
    tar_name: str,
    output_dir: Path,
    dry_run: bool,
) -> Path | None:
    """Download a single tar file from the server.

    Args:
        sftp: Paramiko SFTPClient.
        tar_name: Filename of the tar to download.
        output_dir: Local directory to save the tar file.
        dry_run: If True, log action without downloading.

    Returns:
        Path to downloaded file, or None on dry-run/skip.
    """
    remote_path = f"{REMOTE_BASE}/{tar_name}"
    local_path = output_dir / tar_name

    size_mb = APPROX_SIZE.get(tar_name, 0) / 1_048_576
    size_str = f"{size_mb / 1024:.1f} GB" if size_mb > 1024 else f"{size_mb:.0f} MB"

    if local_path.exists():
        log.info("Already exists, skipping: %s", local_path.name)
        return local_path

    if dry_run:
        log.info("[DRY-RUN] Would download: %s  (~%s)", tar_name, size_str)
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    log.info("Downloading %s  (~%s) …", tar_name, size_str)

    try:
        # Use a simple callback for progress if tqdm is available
        try:
            from tqdm import tqdm

            total_bytes = APPROX_SIZE.get(tar_name, 0)
            with tqdm(
                total=total_bytes, unit="B", unit_scale=True, desc=tar_name, leave=True
            ) as pbar:

                def _cb(transferred: int, _total: int) -> None:
                    pbar.n = transferred
                    pbar.refresh()

                sftp.get(remote_path, str(local_path), callback=_cb)  # type: ignore[union-attr]
        except ImportError:
            sftp.get(remote_path, str(local_path))  # type: ignore[union-attr]

        log.info("  Saved to: %s", local_path)
        return local_path

    except OSError as exc:
        log.error("Download failed for %s: %s", tar_name, exc)
        if local_path.exists():
            local_path.unlink()  # Remove partial download
        return None


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def _extract_tar(tar_path: Path, extract_dir: Path) -> bool:
    """Extract a tar archive into a subdirectory named after the tar stem.

    Args:
        tar_path: Path to the .tar file.
        extract_dir: Root extraction directory.

    Returns:
        True on success.
    """
    stem = tar_path.stem  # e.g. "photo" from "photo.tar"
    dest = extract_dir / stem
    dest.mkdir(parents=True, exist_ok=True)

    log.info("Extracting %s -> %s …", tar_path.name, dest)
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            tf.extractall(dest)
        log.info("  Extracted %s", tar_path.name)
        return True
    except (tarfile.TarError, OSError) as exc:
        log.error("Extraction failed for %s: %s", tar_path.name, exc)
        return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    Returns:
        Configured ArgumentParser.
    """
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Local output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be downloaded without downloading",
    )
    p.add_argument(
        "--extract",
        action="store_true",
        help="Extract tar archives after download",
    )
    p.add_argument(
        "--include-tif",
        action="store_true",
        help="Also download TIF scan archives (scan_upright_tif.tar ~25GB + scan_rotated_tif.tar ~3GB)",
    )
    p.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip MD5 checksum verification after download",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging",
    )
    return p


def main() -> int:
    """Entry point.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    args = _build_parser().parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    host, user, password, port = _read_credentials()
    log.info("Connecting to %s:%d as %s", host, port, user)

    ssh_client, sftp = _open_connection(host, user, password, port)

    tars_to_download = list(REQUIRED_TARS)
    if args.include_tif:
        tars_to_download.extend(OPTIONAL_TIF_TARS)
        log.info("TIF archives included")

    total_gb = sum(APPROX_SIZE.get(t, 0) for t in tars_to_download) / 1_073_741_824
    log.info("Tars to download: %s", ", ".join(tars_to_download))
    log.info("Approximate total download: %.1f GB", total_gb)

    if args.dry_run:
        log.info("DRY-RUN mode — no files will be written")

    downloaded: list[Path] = []
    failed: list[str] = []

    try:
        for tar_name in tars_to_download:
            path = _download_tar(sftp, tar_name, args.output, args.dry_run)
            if path and not args.dry_run:
                if not args.skip_verify and not _verify_md5(path, tar_name):
                    failed.append(tar_name)
                    continue
                downloaded.append(path)
    finally:
        sftp.close()  # type: ignore[union-attr]
        ssh_client.close()  # type: ignore[union-attr]

    if args.dry_run:
        log.info("Dry run complete.")
        return 0

    log.info(
        "Download complete. Success: %d / %d",
        len(downloaded),
        len(tars_to_download),
    )

    if failed:
        log.error("Failed tars (checksum mismatch or error): %s", failed)

    if args.extract and downloaded:
        log.info("Extracting %d archives …", len(downloaded))
        extract_root = args.output / "extracted"
        for path in downloaded:
            _extract_tar(path, extract_root)
        log.info("Extraction complete. Files in: %s", extract_root)

    if downloaded and not args.extract:
        log.info(
            "Tar files saved to: %s\n"
            "Run with --extract to unpack them, or extract manually:\n"
            "  tar xf %s/photo.tar -C /path/to/dest/",
            args.output,
            args.output,
        )

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
