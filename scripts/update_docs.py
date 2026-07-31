# scripts/update_docs.py
import subprocess  # nosec B404
import sys
from pathlib import Path


def main():
    project_root = Path(__file__).resolve().parent.parent

    print("🔄 Updating Supported Services Documentation...")
    try:
        subprocess.run(  # nosec B603
            [
                sys.executable,
                str(project_root / "scripts" / "generate_services_doc.py"),
            ],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to generate services doc: {e}")
        sys.exit(1)

    print("🔄 Generating Codebase Context...")
    try:
        subprocess.run(  # nosec B603
            [sys.executable, str(project_root / "context_generator.py")],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to generate codebase context: {e}")
        sys.exit(1)

    print("\n✅ Automated document generation complete!")
    print("⚠️  Please manually review and update the following files if necessary:")
    print("   - ROADMAP.md (mark completed tasks, add new planned phases)")
    print("   - CHANGELOG.md (document changes under the correct version)")
    print("   - README.md (update feature descriptions, CLI options, versions)")
    print(
        "   - docs/ARCHITECTURE.md, docs/DATA_CONTRACTS.md "
        "(if code contracts or structures changed)"
    )


if __name__ == "__main__":
    main()
