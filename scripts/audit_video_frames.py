"""
Helper script to extract timestamped frames from video for visual timing audit.
"""

import subprocess  # nosec B404
from pathlib import Path

import imageio_ffmpeg  # type: ignore[import-untyped]


def extract_frames(video_file: Path, output_dir: Path) -> None:
    """Extracts 1 frame per second from a video file for inspection."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(video_file),
        "-vf",
        "fps=1",
        str(output_dir / "frame_%03d.png"),
    ]
    subprocess.run(cmd, check=True, capture_output=True)  # nosec B603
    print(f"[+] Extracted frames to {output_dir}")


if __name__ == "__main__":
    extract_frames(
        Path("docs/videos/immich-virtual-pi-deployment.mp4"),
        Path("docs/images/frame_audit"),
    )
