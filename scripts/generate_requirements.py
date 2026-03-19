#!/usr/bin/env python3
"""
Generate requirements.txt files from pyproject.toml.

This script ensures that requirements.txt and requirements-dev.txt stay in sync
with pyproject.toml, preventing dependency drift.

Usage:
    python scripts/generate_requirements.py

Output:
    - requirements.txt (production dependencies)
    - requirements-dev.txt (development dependencies)
"""

import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    # Python < 3.11 compatibility
    import tomli as tomllib


def parse_version_spec(spec: str) -> str:
    """Parse a dependency spec and return pip-compatible version string."""
    # Handle compound specs like ">=1.0.0,<2.0.0"
    return spec


def format_dependency(dep: str) -> str:
    """Format a dependency string for requirements.txt."""
    # Dependencies in pyproject.toml are already in the right format
    return dep.strip()


def generate_requirements_files():
    """Generate requirements.txt files from pyproject.toml."""
    root_dir = Path(__file__).parent.parent
    pyproject_path = root_dir / "pyproject.toml"
    requirements_path = root_dir / "requirements.txt"
    requirements_dev_path = root_dir / "requirements-dev.txt"

    if not pyproject_path.exists():
        print(f"Error: {pyproject_path} not found")
        sys.exit(1)

    # Read pyproject.toml
    with open(pyproject_path, "rb") as f:
        try:
            pyproject = tomllib.load(f)
        except Exception as e:
            print(f"Error parsing pyproject.toml: {e}")
            sys.exit(1)

    project = pyproject.get("project", {})
    dependencies = project.get("dependencies", [])
    optional_dependencies = project.get("optional-dependencies", {})

    # Generate requirements.txt (production dependencies)
    prod_deps = []
    prod_deps.append("# Auto-generated from pyproject.toml")
    prod_deps.append(
        "# DO NOT EDIT MANUALLY - run: python scripts/generate_requirements.py"
    )
    prod_deps.append("")
    for dep in dependencies:
        # Skip comment lines
        if dep.strip().startswith("#"):
            prod_deps.append(dep)
        else:
            prod_deps.append(format_dependency(dep))

    with open(requirements_path, "w") as f:
        f.write("\n".join(prod_deps) + "\n")

    print(f"✓ Generated {requirements_path}")

    # Generate requirements-dev.txt (development dependencies)
    dev_deps = []
    dev_deps.append("# Auto-generated from pyproject.toml")
    dev_deps.append(
        "# DO NOT EDIT MANUALLY - run: python scripts/generate_requirements.py"
    )
    dev_deps.append("")
    dev_deps.append("# Testing")

    dev_optional = optional_dependencies.get("dev", [])
    for dep in dev_optional:
        if dep.strip().startswith("#"):
            dev_deps.append(dep)
        else:
            dev_deps.append(format_dependency(dep))

    # Add all optional dependencies for complete dev environment
    dev_deps.append("")
    dev_deps.append("# All optional dependencies (for complete dev environment)")
    all_optional = optional_dependencies.get("all", [])
    for dep in all_optional:
        if dep.strip().startswith("#"):
            dev_deps.append(dep)
        else:
            dev_deps.append(f"# {dep}")

    with open(requirements_dev_path, "w") as f:
        f.write("\n".join(dev_deps) + "\n")

    print(f"✓ Generated {requirements_dev_path}")

    # Print summary
    print("\n📊 Summary:")
    print(
        f"  Production dependencies: {len([d for d in dependencies if not d.strip().startswith('#')])}"
    )
    print(
        f"  Dev dependencies: {len([d for d in dev_optional if not d.strip().startswith('#')])}"
    )

    # Check for optional dependency groups
    if optional_dependencies:
        print("\n📦 Optional dependency groups:")
        for group, deps in optional_dependencies.items():
            count = len([d for d in deps if not d.strip().startswith("#")])
            print(f"  - {group}: {count} packages")


if __name__ == "__main__":
    generate_requirements_files()
