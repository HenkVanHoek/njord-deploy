import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# The new single source of truth
DESIGN_SYSTEM_REPO = "HenkVanHoek/njorddeploy-design-system"
BRANCH = "main"

# The destination for the assets in our Flask app
STATIC_DIR = Path("src/configurator_app/static")
IMAGES_DIR = STATIC_DIR / "images"
LOGO_FILENAME = "njorddeploy-icon192x192.png"


def fetch_assets() -> None:
    """
    Downloads the latest CSS and image assets from the design system repository.
    """
    print("--- Fetching Design System Assets ---")

    token = os.getenv("GITHUB_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    # Ensure target directories exist
    STATIC_DIR.mkdir(exist_ok=True)
    (STATIC_DIR / "css").mkdir(exist_ok=True)
    IMAGES_DIR.mkdir(exist_ok=True)

    # 1. Fetch the master CSS file
    css_url = (
        f"https://raw.githubusercontent.com/"
        f"{DESIGN_SYSTEM_REPO}/{BRANCH}/css/njorddeploy-style.css"
    )
    print(f"Downloading CSS from {css_url}")
    response = requests.get(css_url, headers=headers, timeout=10)  # nosec
    response.raise_for_status()
    (STATIC_DIR / "css" / "njorddeploy-style.css").write_text(response.text)
    editor_css_dir = Path("src/editor_app/static/css")
    editor_css_dir.mkdir(parents=True, exist_ok=True)
    (editor_css_dir / "njorddeploy-style.css").write_text(response.text)
    print("✅ CSS updated successfully.")

    # 2. Fetch the logo
    logo_url = (
        f"https://raw.githubusercontent.com/"
        f"{DESIGN_SYSTEM_REPO}/{BRANCH}/images/{LOGO_FILENAME}"
    )
    print(f"Downloading logo from {logo_url}")
    response = requests.get(logo_url, headers=headers, timeout=10)  # nosec
    response.raise_for_status()
    (IMAGES_DIR / LOGO_FILENAME).write_bytes(response.content)
    print("✅ Logo updated successfully.")

    print("\n--- Asset fetch complete ---")


if __name__ == "__main__":
    fetch_assets()
