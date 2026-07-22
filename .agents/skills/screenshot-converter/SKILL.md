---
name: screenshot-converter
description: Automatically convert BMP/bitmap screenshots to PNG to prevent MIME-type read errors.
---

# Screenshot Converter (BMP to PNG)

Use this skill to handle uploaded images that are not directly supported by `view_file` (such as `.bmp` files).

## Workflow when receiving a BMP/Bitmap screenshot:

If the user uploads an image with a `.bmp` extension (or another unsupported format), you **must not** attempt to view it directly with `view_file` (this will cause a MIME-type error). Instead, follow these steps:

### 1. Convert the image via the script:
Run the conversion script in the terminal:
```bash
python3 .agents/skills/screenshot-converter/scripts/convert.py "/absolute/path/to/file.bmp"
```

### 2. Open the converted PNG file:
Use the `view_file` tool to inspect the newly generated `.png` file.

### 3. Report/Reply to the user:
Answer the user's question directly based on the converted screenshot, without requiring any additional action or manual permission from the user.
