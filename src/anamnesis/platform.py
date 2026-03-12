"""OS detection and platform-specific utilities."""

import platform
import sys


def detect_platform() -> str:
    """Detect the current operating system.

    Returns one of: "macos", "linux", "windows".
    """
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "linux":
        return "linux"
    if system == "windows":
        return "windows"
    return system


def get_lock_command() -> str:
    """Return the appropriate file-locking command for this platform.

    macOS uses lockf(1), Linux uses flock(1).
    """
    plat = detect_platform()
    if plat == "macos":
        return "lockf"
    if plat == "linux":
        return "flock"
    print(f"Warning: no known lock command for platform '{plat}'; defaulting to flock", file=sys.stderr)
    return "flock"
