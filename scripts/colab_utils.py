"""Google Colab-specific utilities and environment helpers.

Provides GPU detection, memory management, session monitoring, and
Colab-specific optimizations for training workflows.
"""

import os
import shutil
import subprocess  # nosec B404 - subprocess used safely with hardcoded commands
import sys
from pathlib import Path

import torch

# Constants for Colab-specific paths
COLAB_CONTENT_ROOT = "/content"
COLAB_DRIVE_ROOT = "/content/drive/MyDrive"


def is_colab_environment() -> bool:
    """Check if running in Google Colab.

    Returns:
        True if running in Colab
    """
    try:
        import google.colab  # noqa: F401

        return True
    except ImportError:
        return False


# GPU tier mapping: (identifier, tier_name, expected_memory_gb)
_GPU_TIERS: dict[str, tuple[str, int]] = {
    "t4": ("Free/Pro (T4)", 15),
    "p100": ("Pro (P100)", 16),
    "v100": ("Pro (V100)", 16),
    "a100": ("Pro+ (A100)", 40),
}


def _detect_colab_tier(gpu_name: str, fallback_memory: float) -> tuple[str, float]:
    """Detect Colab GPU tier from GPU name.

    Args:
        gpu_name: Name of the GPU (case-insensitive)
        fallback_memory: Memory to use if tier not recognized

    Returns:
        Tuple of (tier_name, expected_memory_gb)
    """
    gpu_name_lower = gpu_name.lower()
    for identifier, (tier_name, memory) in _GPU_TIERS.items():
        if identifier in gpu_name_lower:
            return tier_name, memory
    return "Unknown", fallback_memory


def _get_nvidia_smi_info() -> dict[str, str]:
    """Get detailed GPU info from nvidia-smi.

    Returns:
        Dictionary with gpu_name_detailed and gpu_memory_detailed, or empty dict on failure
    """
    nvidia_smi_path = shutil.which("nvidia-smi")
    if nvidia_smi_path is None:
        return {}

    result = subprocess.run(  # nosec B603 - nvidia-smi path resolved via shutil.which
        [nvidia_smi_path, "--query-gpu=name,memory.total", "--format=csv,noheader"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return {}

    try:
        gpu_name, gpu_memory = result.stdout.strip().split(", ")
        return {"gpu_name_detailed": gpu_name, "gpu_memory_detailed": gpu_memory}
    except ValueError:
        return {}


def get_gpu_info() -> dict[str, any]:
    """Get GPU information in Colab.

    Returns:
        Dictionary with GPU type, memory, CUDA version, etc.
    """
    info = {
        "gpu_available": torch.cuda.is_available(),
        "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "cuda_version": torch.version.cuda if torch.cuda.is_available() else None,
    }

    if not info["gpu_available"]:
        return info

    info["gpu_name"] = torch.cuda.get_device_name(0)
    info["gpu_memory_total_gb"] = round(
        torch.cuda.get_device_properties(0).total_memory / (1024**3), 2
    )

    # Try to get more detailed info from nvidia-smi
    info.update(_get_nvidia_smi_info())

    # Detect GPU tier for Colab
    tier, memory = _detect_colab_tier(
        info["gpu_name"], info.get("gpu_memory_total_gb", 0)
    )
    info["colab_tier"] = tier
    info["expected_memory_gb"] = memory

    return info


def print_environment_info() -> None:
    """Print comprehensive environment information."""
    print("=" * 60)
    print("🖥️  ENVIRONMENT INFORMATION")
    print("=" * 60)

    # Colab check
    print(f"Running in Colab: {is_colab_environment()}")

    # Python version
    print(f"Python version: {sys.version.split()[0]}")

    # PyTorch info
    print(f"PyTorch version: {torch.__version__}")

    # GPU info
    gpu_info = get_gpu_info()
    print("\n🎮 GPU Information:")
    print(f"   GPU Available: {gpu_info['gpu_available']}")
    if gpu_info["gpu_available"]:
        print(f"   GPU Name: {gpu_info['gpu_name']}")
        print(f"   GPU Memory: {gpu_info['gpu_memory_total_gb']} GB")
        print(f"   CUDA Version: {gpu_info['cuda_version']}")
        print(f"   Colab Tier: {gpu_info.get('colab_tier', 'Unknown')}")
    else:
        print("   ⚠️  No GPU detected! Training will be VERY slow on CPU.")

    # Disk space
    print("\n💾 Disk Space:")
    total, _, free = get_disk_space(COLAB_CONTENT_ROOT)
    print(f"   {COLAB_CONTENT_ROOT}: {free:.1f} GB free (Total: {total:.1f} GB)")

    if is_colab_environment():
        drive_total, _, drive_free = get_disk_space(COLAB_DRIVE_ROOT)
        if drive_total > 0:
            print(
                f"   Google Drive: {drive_free:.1f} GB free (Total: {drive_total:.1f} GB)"
            )

    print("=" * 60)


def get_disk_space(path: str = COLAB_CONTENT_ROOT) -> tuple[float, float, float]:
    """Get disk space information.

    Args:
        path: Path to check disk space for

    Returns:
        Tuple of (total_gb, used_gb, free_gb)
    """
    try:
        stat = shutil.disk_usage(path)
        total_gb = stat.total / (1024**3)
        used_gb = stat.used / (1024**3)
        free_gb = stat.free / (1024**3)
        return total_gb, used_gb, free_gb
    except Exception:
        return 0.0, 0.0, 0.0


def optimize_colab_environment() -> None:
    """Apply Colab-specific optimizations for training.

    Sets environment variables and PyTorch settings for optimal performance.
    """
    print("⚙️  Applying Colab optimizations...")

    # PyTorch optimizations
    if torch.cuda.is_available():
        # Enable TF32 for faster training on Ampere GPUs (A100)
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        print("   ✅ Enabled TF32 precision (Ampere GPUs)")

        # Enable cuDNN autotuner
        torch.backends.cudnn.benchmark = True
        print("   ✅ Enabled cuDNN autotuner")

        # Set memory allocator settings
        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"
        print("   ✅ Configured CUDA memory allocator")

    # Set number of threads for CPU operations
    if "OMP_NUM_THREADS" not in os.environ:
        os.environ["OMP_NUM_THREADS"] = "2"
        torch.set_num_threads(2)
        print("   ✅ Set CPU thread count to 2")

    print("✅ Optimizations applied!")


def clear_gpu_memory() -> None:
    """Clear GPU memory cache."""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        print("🗑️  GPU memory cache cleared")


def get_gpu_memory_usage() -> dict[str, float]:
    """Get current GPU memory usage.

    Returns:
        Dictionary with allocated, reserved, and free memory in GB
    """
    if not torch.cuda.is_available():
        return {"error": "No GPU available"}

    allocated = torch.cuda.memory_allocated(0) / (1024**3)
    reserved = torch.cuda.memory_reserved(0) / (1024**3)
    total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    free = total - reserved

    return {
        "allocated_gb": round(allocated, 2),
        "reserved_gb": round(reserved, 2),
        "free_gb": round(free, 2),
        "total_gb": round(total, 2),
        "usage_percent": round((reserved / total) * 100, 1),
    }


def print_gpu_memory_usage() -> None:
    """Print current GPU memory usage."""
    usage = get_gpu_memory_usage()

    if "error" in usage:
        print(f"⚠️  {usage['error']}")
        return

    print("📊 GPU Memory Usage:")
    print(f"   Allocated: {usage['allocated_gb']:.2f} GB")
    print(f"   Reserved: {usage['reserved_gb']:.2f} GB")
    print(f"   Free: {usage['free_gb']:.2f} GB")
    print(f"   Total: {usage['total_gb']:.2f} GB")
    print(f"   Usage: {usage['usage_percent']:.1f}%")


def install_packages(packages: list, quiet: bool = True) -> None:
    """Install Python packages using pip.

    Args:
        packages: List of package names to install
        quiet: If True, suppress output
    """
    print(f"📦 Installing packages: {', '.join(packages)}")

    for package in packages:
        cmd = [sys.executable, "-m", "pip", "install", package]
        if quiet:
            cmd.append("-q")

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)  # nosec B603
        if result.returncode == 0:
            print(f"   ✅ {package}")
        else:
            print(f"   ❌ {package} (error: {result.stderr[:100]})")


def download_from_url(url: str, output_path: str) -> Path:
    """Download file from URL with progress bar.

    Args:
        url: URL to download from (must be http or https)
        output_path: Local path to save file

    Returns:
        Path to downloaded file

    Raises:
        ValueError: If URL scheme is not http/https
    """
    from urllib.parse import urlparse

    import requests

    # Validate URL scheme to prevent file:// access
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        msg = f"Invalid URL scheme: {parsed.scheme}. Only http/https allowed."
        raise ValueError(msg)

    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    print(f"⬇️  Downloading from {url}")

    # Use requests library for safer download with streaming
    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    block_size = 8192
    downloaded = 0

    with open(output_path_obj, "wb") as f:
        for chunk in response.iter_content(chunk_size=block_size):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = int(downloaded * 100 / total_size)
                    sys.stdout.write(f"\r   Progress: {percent}%")
                    sys.stdout.flush()

    print(f"\n✅ Downloaded to: {output_path_obj}")

    return output_path_obj


def check_session_health() -> dict[str, any]:
    """Check Colab session health and resource availability.

    Returns:
        Dictionary with session status information
    """
    health = {
        "gpu_available": torch.cuda.is_available(),
        "colab_environment": is_colab_environment(),
    }

    if health["gpu_available"]:
        gpu_usage = get_gpu_memory_usage()
        health["gpu_memory_ok"] = gpu_usage["usage_percent"] < 90
        health["gpu_memory_usage"] = gpu_usage["usage_percent"]

    # Check disk space
    _, _, free_gb = get_disk_space(COLAB_CONTENT_ROOT)
    health["disk_space_ok"] = free_gb > 5  # At least 5GB free
    health["disk_free_gb"] = round(free_gb, 1)

    # Overall health
    health["healthy"] = all(
        [
            health["gpu_available"],
            health.get("gpu_memory_ok", True),
            health["disk_space_ok"],
        ]
    )

    return health


def print_session_health() -> None:
    """Print session health status."""
    health = check_session_health()

    print("\n🏥 SESSION HEALTH CHECK")
    print("=" * 60)

    status_icon = "✅" if health["healthy"] else "⚠️"
    print(
        f"{status_icon} Overall Status: {'Healthy' if health['healthy'] else 'Issues Detected'}"
    )

    print(f"\n   GPU Available: {'✅' if health['gpu_available'] else '❌'}")
    if "gpu_memory_usage" in health:
        mem_icon = "✅" if health["gpu_memory_ok"] else "⚠️"
        print(f"   {mem_icon} GPU Memory: {health['gpu_memory_usage']:.1f}% used")

    disk_icon = "✅" if health["disk_space_ok"] else "⚠️"
    print(f"   {disk_icon} Disk Space: {health['disk_free_gb']:.1f} GB free")

    print("=" * 60)


def setup_colab_training_environment(
    project_name: str = "image-preprocessing-detector",
    drive_mount: bool = True,
) -> dict[str, str]:
    """Complete Colab environment setup for training.

    Args:
        project_name: Name of the project
        drive_mount: Whether to mount Google Drive

    Returns:
        Dictionary with important paths
    """
    print("\n" + "=" * 60)
    print(f"🚀 Setting up Colab environment for {project_name}")
    print("=" * 60 + "\n")

    paths = {
        "content_root": COLAB_CONTENT_ROOT,
        "project_root": f"{COLAB_CONTENT_ROOT}/{project_name}",
    }

    # Mount Google Drive if requested
    if drive_mount and is_colab_environment():
        from scripts.gdrive_sync import mount_google_drive

        mount_google_drive()
        paths["drive_root"] = COLAB_DRIVE_ROOT
        paths["drive_project"] = f"{COLAB_DRIVE_ROOT}/{project_name}"

    # Print environment info
    print_environment_info()

    # Apply optimizations
    optimize_colab_environment()

    # Check session health
    print_session_health()

    print("\n✅ Environment setup complete!")
    print("\nImportant paths:")
    for key, value in paths.items():
        print(f"   {key}: {value}")

    return paths
