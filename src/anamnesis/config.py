"""Configuration management for anamnesis.

Reads and writes ~/.anamnesis.yaml.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


CONFIG_PATH = Path.home() / ".anamnesis.yaml"

# Modules that can be enabled
AVAILABLE_MODULES = [
    "memory",   # Core memory system (rules, index, MEMORY.md)
    "tasks",    # Task tracking in .claude/memory/tasks/
    "friday",   # Weekly digest / morning check-in skill
]

# Modules that require other modules to be present
MODULE_DEPENDENCIES: dict[str, list[str]] = {
    "tasks": ["memory"],
    "friday": ["memory"],
}


@dataclass
class Config:
    """Top-level configuration."""

    # Who is the user?
    user_name: str = ""
    user_role: str = ""

    # Which modules are enabled
    modules: list[str] = field(default_factory=lambda: ["memory"])

    # Per-module configuration (arbitrary dict per module)
    module_config: dict[str, dict[str, Any]] = field(default_factory=dict)

    def validate(self) -> list[str]:
        """Return a list of validation errors (empty = valid)."""
        errors: list[str] = []
        if not self.user_name:
            errors.append("user_name is required")
        for mod in self.modules:
            if mod not in AVAILABLE_MODULES:
                errors.append(f"Unknown module: {mod}")
            deps = MODULE_DEPENDENCIES.get(mod, [])
            for dep in deps:
                if dep not in self.modules:
                    errors.append(f"Module '{mod}' requires '{dep}' to be enabled")
        return errors


def load_config(path: Path | None = None) -> Config:
    """Load configuration from disk. Returns defaults if file doesn't exist."""
    path = path or CONFIG_PATH
    if not path.exists():
        return Config()

    with open(path) as f:
        raw = yaml.safe_load(f) or {}

    return Config(
        user_name=raw.get("user_name", ""),
        user_role=raw.get("user_role", ""),
        modules=raw.get("modules", ["memory"]),
        module_config=raw.get("module_config", {}),
    )


def save_config(config: Config, path: Path | None = None) -> None:
    """Write configuration to disk."""
    path = path or CONFIG_PATH
    data: dict[str, Any] = {
        "user_name": config.user_name,
        "user_role": config.user_role,
        "modules": config.modules,
    }
    if config.module_config:
        data["module_config"] = config.module_config

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def collect_config_interactive() -> Config:
    """Prompt the user for configuration values interactively."""
    print("anamnesis setup")
    print("=" * 40)
    print()

    user_name = input("Your name: ").strip()
    user_role = input("Your role (e.g. 'backend engineer', 'data scientist'): ").strip()

    print()
    print("Available modules:")
    for mod in AVAILABLE_MODULES:
        deps = MODULE_DEPENDENCIES.get(mod, [])
        dep_note = f" (requires: {', '.join(deps)})" if deps else ""
        print(f"  - {mod}{dep_note}")

    print()
    print("Which modules do you want? (comma-separated, default: memory)")
    modules_input = input("Modules: ").strip()
    if modules_input:
        modules = [m.strip() for m in modules_input.split(",") if m.strip()]
    else:
        modules = ["memory"]

    config = Config(
        user_name=user_name,
        user_role=user_role,
        modules=modules,
    )

    errors = config.validate()
    if errors:
        print()
        print("Warning — configuration has issues:")
        for err in errors:
            print(f"  - {err}")

    return config
