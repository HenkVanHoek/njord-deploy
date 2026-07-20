# .agents/skills/screenshot-converter/scripts/convert.py
import sys
from pathlib import Path

from PIL import Image


def main():
    if len(sys.argv) < 2:
        print("Usage: python convert.py <path_to_image>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"Error: {input_path} does not exist.")
        sys.exit(1)

    output_path = input_path.with_suffix(".png")
    try:
        with Image.open(input_path) as img:
            img.save(output_path, "PNG")
        print(f"Successfully converted {input_path.name} to {output_path.name}")
    except Exception as e:
        print(f"Failed to convert: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
