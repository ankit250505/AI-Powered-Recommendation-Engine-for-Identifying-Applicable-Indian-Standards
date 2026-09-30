from __future__ import annotations

import subprocess

import imageio_ffmpeg

from build_youtube_video_kit import ASSETS, KIT, closing_frame, placeholder_frame, title_frame


def build_short_video() -> None:
    scenes = [
        (title_frame(), 5),
        (
            placeholder_frame(
                "A",
                "00:30",
                "Search a procurement requirement",
                "search-results.png",
                [
                    "Enter: TMT bars for RCC work.",
                    "Keep Hybrid mode selected and run the search.",
                    "Pause on IS 1786:2008.",
                    "Show confidence, matched terms, source and verification status.",
                ],
                "21-short-search.png",
            ),
            30,
        ),
        (
            placeholder_frame(
                "B",
                "00:45",
                "Upload and analyze the demo PDF",
                "search-results.png",
                [
                    "Choose demo_procurement_specification.pdf.",
                    "Click Extract & Recommend.",
                    "Mention 27 clauses analyzed.",
                    "Show steel, LED, water and fire-safety results with matching clauses.",
                ],
                "22-short-document.png",
            ),
            45,
        ),
        (
            placeholder_frame(
                "C",
                "00:20",
                "Browse standards and export evidence",
                "standards-library.png",
                [
                    "Open Standards Library and show the 250-record catalogue.",
                    "Search or filter briefly, then show Compare.",
                    "Return to the run and point to PDF Report and CSV Data.",
                ],
                "23-short-library.png",
            ),
            20,
        ),
        (
            placeholder_frame(
                "D",
                "00:13",
                "Show review controls and measured quality",
                "admin-dashboard.png",
                [
                    "Open Admin Review.",
                    "Show feedback, verification queue and audit history.",
                    "Pause on Top-1, Top-5 and MRR metrics.",
                ],
                "24-short-admin.png",
            ),
            13,
        ),
        (closing_frame(), 5),
    ]

    concat = KIT / "short-video-concat.txt"
    lines: list[str] = []
    for frame_path, duration in scenes:
        lines.append(f"file '{frame_path.as_posix()}'")
        lines.append(f"duration {duration}")
    lines.append(f"file '{scenes[-1][0].as_posix()}'")
    concat.write_text("\n".join(lines) + "\n", encoding="utf-8")

    total_duration = sum(duration for _, duration in scenes)
    output = KIT / "SIH2026_Prototype_Runthrough_Guide_1m58s.mp4"
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat),
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-t",
        str(total_duration),
        "-vf",
        "fps=30,format=yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(output),
    ]
    subprocess.run(command, check=True)
    print(f"Created {output} ({total_duration} seconds)")


if __name__ == "__main__":
    build_short_video()
