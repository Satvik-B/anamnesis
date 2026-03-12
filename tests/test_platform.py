"""Tests for platform detection utilities."""

import sys
from unittest import mock

import pytest

from anamnesis.platform import detect_platform, get_lock_command


class TestDetectPlatform:
    """Tests for detect_platform()."""

    def test_detect_platform(self):
        """detect_platform() should return one of the known platform strings."""
        result = detect_platform()
        assert result in ("macos", "linux", "windows"), f"Unexpected platform: {result}"

    def test_detect_macos(self):
        """When platform.system() returns 'Darwin', detect_platform() should return 'macos'."""
        with mock.patch("anamnesis.platform.platform") as mock_plat:
            mock_plat.system.return_value = "Darwin"
            assert detect_platform() == "macos"

    def test_detect_linux(self):
        """When platform.system() returns 'Linux', detect_platform() should return 'linux'."""
        with mock.patch("anamnesis.platform.platform") as mock_plat:
            mock_plat.system.return_value = "Linux"
            assert detect_platform() == "linux"

    def test_detect_windows(self):
        """When platform.system() returns 'Windows', detect_platform() should return 'windows'."""
        with mock.patch("anamnesis.platform.platform") as mock_plat:
            mock_plat.system.return_value = "Windows"
            assert detect_platform() == "windows"


class TestGetLockCommand:
    """Tests for get_lock_command()."""

    def test_get_lock_command(self):
        """get_lock_command() should return a non-empty string."""
        result = get_lock_command()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_macos_uses_lockf(self):
        """On macOS, the lock command should be lockf."""
        with mock.patch("anamnesis.platform.platform") as mock_plat:
            mock_plat.system.return_value = "Darwin"
            assert get_lock_command() == "lockf"

    def test_linux_uses_flock(self):
        """On Linux, the lock command should be flock."""
        with mock.patch("anamnesis.platform.platform") as mock_plat:
            mock_plat.system.return_value = "Linux"
            assert get_lock_command() == "flock"

    def test_unknown_platform_defaults_to_flock(self):
        """An unknown platform should default to flock with a warning."""
        with mock.patch("anamnesis.platform.platform") as mock_plat:
            mock_plat.system.return_value = "FreeBSD"
            assert get_lock_command() == "flock"
