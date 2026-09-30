from __future__ import annotations

import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "output" / "video-kit"
ASSETS = KIT / "assets"
FRAMES = KIT / "frames"
WIDTH, HEIGHT = 1920, 1080

NAVY = "#123B63"
INK = "#172534"
GREEN = "#138A5B"
SAFFRON = "#F28C28"
WHITE = "#FFFFFF"
MUTED = "#DCE6EF"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    filename = "arialbd.ttf" if bold else "arial.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / filename), size)


def cover(path: Path, dim: float = 0.0, blur: float = 0.0) -> Image.Image:
    image = Image.open(path).convert("RGB")
    scale = max(WIDTH / image.width, HEIGHT / image.height)
    image = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    x = (image.width - WIDTH) // 2
    y = (image.height - HEIGHT) // 2
    image = image.crop((x, y, x + WIDTH, y + HEIGHT))
    if blur:
        image = image.filter(ImageFilter.GaussianBlur(blur))
    if dim:
        image = ImageEnhance.Brightness(image).enhance(1 - dim)
    return image


def contain(path: Path, box: tuple[int, int, int, int], background: str = "#F4F7FA") -> Image.Image:
    x, y, w, h = box
    image = Image.open(path).convert("RGB")
    image.thumbnail((w, h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (w, h), background)
    canvas.paste(image, ((w - image.width) // 2, (h - image.height) // 2))
    return canvas


def rounded_panel(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str, outline: str | None = None) -> None:
    draw.rounded_rectangle(box, radius=28, fill=fill, outline=outline, width=3 if outline else 1)


def wrap(draw: ImageDraw.ImageDraw, text: str, text_font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=text_font)[2] <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_text_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: tuple[int, int],
    text_font: ImageFont.FreeTypeFont,
    fill: str,
    width: int,
    spacing: int = 12,
) -> int:
    x, y = xy
    for line in wrap(draw, text, text_font, width):
        draw.text((x, y), line, font=text_font, fill=fill)
        y += text_font.size + spacing
    return y


def save(image: Image.Image, name: str) -> Path:
    path = FRAMES / name
    image.save(path, quality=95)
    return path


def title_frame() -> Path:
    image = cover(ASSETS / "generated-opening.png", dim=0.12)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle((0, 0, 1040, HEIGHT), fill=(9, 35, 60, 220))
    od.rectangle((0, 0, WIDTH, 14), fill=SAFFRON)
    image = Image.alpha_composite(image.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(image)
    draw.text((110, 125), "SMART INDIA HACKATHON 2026", font=font(34, True), fill="#A9C6DD")
    y = draw_text_block(draw, "AI-Powered Recommendation Engine", (110, 260), font(76, True), WHITE, 800, 8)
    y = draw_text_block(draw, "for Identifying Applicable Indian Standards", (110, y + 15), font(48, True), "#BFEAD5", 820, 10)
    draw.text((110, 760), "Procurement specifications to ranked, explainable standards", font=font(31), fill=WHITE)
    draw.text((110, 835), "Decision support with human review", font=font(27, True), fill="#FFD3A8")
    return save(image.convert("RGB"), "01-title.png")


def problem_frame() -> Path:
    image = cover(ASSETS / "generated-problem-solution.png", dim=0.06)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle((0, 0, WIDTH, 170), fill=(9, 35, 60, 224))
    od.rounded_rectangle((105, 740, 1815, 1000), radius=30, fill=(255, 255, 255, 232))
    image = Image.alpha_composite(image.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(image)
    draw.text((110, 50), "THE PROBLEM", font=font(34, True), fill="#A9C6DD")
    draw.text((110, 96), "Procurement language rarely matches a standard title exactly.", font=font(42, True), fill=WHITE)
    items = [
        ("Manual search", "Slow across large catalogues"),
        ("Different wording", "Product, grade, use and performance terms vary"),
        ("Low traceability", "The reason behind a choice can be hard to audit"),
    ]
    x = 150
    for heading, body in items:
        draw.ellipse((x, 792, x + 24, 816), fill=SAFFRON)
        draw.text((x + 42, 770), heading, font=font(27, True), fill=NAVY)
        draw_text_block(draw, body, (x + 42, 820), font(24), INK, 430, 8)
        x += 555
    return save(image.convert("RGB"), "02-problem.png")


def solution_frame() -> Path:
    image = cover(ASSETS / "generated-explainable-pipeline.png", dim=0.03)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle((0, 0, WIDTH, 180), fill=(255, 255, 255, 236))
    od.rounded_rectangle((80, 820, 1840, 1010), radius=28, fill=(12, 43, 72, 226))
    image = Image.alpha_composite(image.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(image)
    draw.text((95, 45), "THE SOLUTION", font=font(33, True), fill=GREEN)
    draw.text((95, 91), "A procurement-specific, explainable recommendation workflow", font=font(46, True), fill=INK)
    labels = ["TXT / PDF / DOCX", "Clause extraction", "Hybrid retrieval", "Ranked evidence", "Human verification"]
    x = 125
    for index, label in enumerate(labels):
        color = SAFFRON if index == 4 else GREEN
        draw.rounded_rectangle((x, 872, x + 300, 950), radius=18, fill=color)
        bbox = draw.textbbox((0, 0), label, font=font(23, True))
        draw.text((x + (300 - (bbox[2] - bbox[0])) / 2, 896), label, font=font(23, True), fill=WHITE)
        if index < len(labels) - 1:
            draw.polygon([(x + 318, 900), (x + 346, 911), (x + 318, 922)], fill="#BFD0DE")
        x += 345
    return save(image.convert("RGB"), "03-solution.png")


def screenshot_frame(source: str, name: str, eyebrow: str, heading: str, bullets: list[str], accent: str = GREEN) -> Path:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#EEF3F7")
    draw = ImageDraw.Draw(image)
    screenshot = contain(ASSETS / source, (70, 180, 1210, 800), "#FFFFFF")
    image.paste(screenshot, (70, 180))
    draw.rounded_rectangle((65, 175, 1285, 985), radius=28, outline="#9FB3C5", width=3)
    rounded_panel(draw, (1330, 180, 1845, 985), "#FFFFFF", "#C7D5E1")
    draw.text((75, 48), eyebrow, font=font(30, True), fill=accent)
    draw.text((75, 91), heading, font=font(44, True), fill=INK)
    y = 270
    for bullet in bullets:
        draw.ellipse((1380, y + 7, 1400, y + 27), fill=accent)
        y = draw_text_block(draw, bullet, (1425, y), font(27), INK, 360, 10) + 35
    return save(image, name)


def placeholder_frame(number: str, duration: str, heading: str, source: str, actions: list[str], name: str) -> Path:
    image = cover(ASSETS / source, dim=0.5, blur=3)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle((0, 0, WIDTH, HEIGHT), fill=(8, 31, 54, 175))
    od.rounded_rectangle((110, 100, 1810, 980), radius=40, fill=(255, 255, 255, 242))
    image = Image.alpha_composite(image.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((150, 145, 650, 225), radius=20, fill=SAFFRON)
    draw.text((180, 165), f"INSERT RUNTHROUGH {number}", font=font(26, True), fill=WHITE)
    draw.text((1535, 160), duration, font=font(30, True), fill=NAVY)
    draw.text((150, 300), heading, font=font(50, True), fill=INK)
    draw.text((150, 375), "Replace this slate with your screen recording.", font=font(27), fill="#526577")
    y = 485
    for index, action in enumerate(actions, 1):
        draw.ellipse((165, y - 5, 220, y + 50), fill=GREEN)
        draw.text((183, y + 3), str(index), font=font(25, True), fill=WHITE)
        y = draw_text_block(draw, action, (255, y), font(31, True), INK, 1400, 9) + 40
    draw.text((150, 900), "Keep the cursor slow and pause briefly after each result appears.", font=font(25, True), fill=NAVY)
    return save(image.convert("RGB"), name)


def metrics_frame() -> Path:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#F2F6F9")
    draw = ImageDraw.Draw(image)
    screenshot = contain(ASSETS / "admin-dashboard.png", (90, 220, 1050, 590), "#FFFFFF")
    image.paste(screenshot, (90, 220))
    draw.rounded_rectangle((85, 215, 1150, 820), radius=28, outline="#9FB3C5", width=3)
    draw.text((90, 60), "CONTROLLED PROTOTYPE EVALUATION", font=font(32, True), fill=GREEN)
    draw.text((90, 108), "Measured retrieval, stated honestly", font=font(48, True), fill=INK)
    cards = [("91.5%", "Top-1"), ("97.3%", "Top-5"), ("0.943", "MRR")]
    y = 250
    for value, label in cards:
        rounded_panel(draw, (1230, y, 1780, y + 155), "#FFFFFF", "#C7D5E1")
        draw.text((1280, y + 24), value, font=font(50, True), fill=NAVY)
        draw.text((1515, y + 42), label, font=font(28, True), fill=GREEN)
        y += 185
    draw.rounded_rectangle((1230, 815, 1780, 930), radius=20, fill="#FFF2E5", outline="#F4B471", width=2)
    draw.text((1270, 840), "Controlled synthetic held-out split", font=font(23, True), fill="#9B4B18")
    draw.text((1270, 880), "375 test queries", font=font(22), fill="#704B33")
    draw.text((90, 900), "Catalogue: 250 standards   |   Labeled examples: 3,750", font=font(30, True), fill=NAVY)
    draw.text((90, 958), "These results are not a claim of accuracy across all real Indian tenders.", font=font(25), fill="#526577")
    return save(image, "11-metrics.png")


def usp_frame() -> Path:
    image = cover(ASSETS / "generated-opening.png", dim=0.5, blur=2)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle((0, 0, WIDTH, HEIGHT), fill=(8, 31, 54, 168))
    image = Image.alpha_composite(image.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(image)
    draw.text((105, 65), "WHY THIS IS DIFFERENT", font=font(32, True), fill="#BFEAD5")
    draw.text((105, 115), "Not just AI search. A reviewable procurement workflow.", font=font(50, True), fill=WHITE)
    items = [
        ("Explainable", "Matched terms and exact clauses"),
        ("Reviewable", "Accept, reject, note and audit"),
        ("Reproducible", "Saved runs with PDF and CSV reports"),
        ("Local-first", "Sensitive tender text can stay in deployment"),
    ]
    y = 260
    for heading, body in items:
        draw.rounded_rectangle((105, y, 1035, y + 135), radius=24, fill=(255, 255, 255, 232))
        draw.ellipse((145, y + 42, 185, y + 82), fill=GREEN)
        draw.text((220, y + 25), heading, font=font(31, True), fill=NAVY)
        draw.text((220, y + 74), body, font=font(25), fill=INK)
        y += 160
    draw.rounded_rectangle((1110, 290, 1810, 820), radius=30, fill=(255, 244, 232, 238), outline="#F4B471", width=3)
    draw.text((1160, 345), "CURRENT BOUNDARY", font=font(30, True), fill="#A64B15")
    boundaries = [
        "Decision support, not a legal ruling",
        "Official BIS verification is still required",
        "Real-tender benchmarking is the next step",
        "Scanned PDFs need an OCR integration",
    ]
    y = 430
    for item in boundaries:
        draw.rectangle((1160, y + 8, 1182, y + 30), fill=SAFFRON)
        y = draw_text_block(draw, item, (1210, y), font(27), INK, 520, 9) + 35
    return save(image.convert("RGB"), "12-usp-boundary.png")


def closing_frame() -> Path:
    image = cover(ASSETS / "generated-explainable-pipeline.png", dim=0.45, blur=2)
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle((0, 0, WIDTH, HEIGHT), fill=(8, 31, 54, 185))
    image = Image.alpha_composite(image.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(image)
    draw.text((140, 250), "INDIAN STANDARDS FINDER", font=font(34, True), fill="#BFEAD5")
    draw.text((140, 320), "From procurement language", font=font(68, True), fill=WHITE)
    draw.text((140, 410), "to evidence-backed standards.", font=font(68, True), fill=WHITE)
    draw.rounded_rectangle((140, 590, 865, 695), radius=24, fill=GREEN)
    draw.text((195, 620), "Rank. Explain. Review. Verify.", font=font(34, True), fill=WHITE)
    draw.text((140, 805), "Smart India Hackathon 2026", font=font(31), fill="#DCE6EF")
    draw.text((140, 860), "Thank you", font=font(39, True), fill="#FFD3A8")
    return save(image.convert("RGB"), "13-closing.png")


def build() -> None:
    FRAMES.mkdir(parents=True, exist_ok=True)
    scenes: list[tuple[Path, int]] = [
        (title_frame(), 18),
        (problem_frame(), 27),
        (solution_frame(), 27),
        (
            screenshot_frame(
                "search-workspace.png",
                "04-how-it-works.png",
                "WHY IT WORKS",
                "Exact terms and semantic similarity work together",
                [
                    "Keyword evidence keeps matches understandable.",
                    "Similarity handles different procurement wording.",
                    "Clause analysis avoids treating a long tender as one vague query.",
                ],
            ),
            26,
        ),
        (
            placeholder_frame(
                "A",
                "00:55",
                "Text search and ranked evidence",
                "search-workspace.png",
                [
                    "Open Search and keep Hybrid mode selected.",
                    "Choose TMT bars or type: TMT bars for RCC work.",
                    "Run the search and pause on IS 1786:2008.",
                    "Show score, confidence, matched terms, source and applicability note.",
                ],
                "05-runthrough-a.png",
            ),
            55,
        ),
        (
            screenshot_frame(
                "search-results.png",
                "06-result-meaning.png",
                "READING A RESULT",
                "The recommendation includes its evidence, not only a code",
                [
                    "Rank and confidence support prioritisation.",
                    "Matched terms explain why the result appeared.",
                    "Verification state and source keep the reviewer in control.",
                ],
                SAFFRON,
            ),
            27,
        ),
        (
            placeholder_frame(
                "B",
                "01:15",
                "Document upload and clause-level evidence",
                "document-analysis.png",
                [
                    "Select the supplied demo procurement PDF.",
                    "Click Extract & Recommend and mention the 27 analyzed clauses.",
                    "Show steel, LED lighting, drinking water and fire-safety matches.",
                    "Open one matching-clause section, then point to PDF and CSV export.",
                ],
                "07-runthrough-b.png",
            ),
            75,
        ),
        (
            screenshot_frame(
                "standards-library.png",
                "08-library.png",
                "CATALOGUE EXPLORATION",
                "Browse, filter and compare 250 standards",
                [
                    "Search by code, title or category.",
                    "See scope, source and verification state.",
                    "Compare selected records side by side.",
                ],
            ),
            27,
        ),
        (
            placeholder_frame(
                "C",
                "00:55",
                "Human review, history and governance",
                "admin-dashboard.png",
                [
                    "Open Recent Runs and reopen the saved document analysis.",
                    "Add a reviewer note and show Accept or Reject.",
                    "Open Admin Review and show activity, quality and verification queue.",
                    "Pause on the controlled held-out evaluation metrics.",
                ],
                "09-runthrough-c.png",
            ),
            55,
        ),
        (
            screenshot_frame(
                "admin-dashboard.png",
                "10-technical.png",
                "TECHNICAL FOUNDATION",
                "A compact local stack with production-shaped controls",
                [
                    "FastAPI backend and static browser interface.",
                    "SQLite stores users, searches, feedback and audit history.",
                    "Authentication, roles, health checks, backups, Docker and CI are included.",
                ],
                NAVY,
            ),
            35,
        ),
        (metrics_frame(), 33),
        (usp_frame(), 35),
        (closing_frame(), 18),
    ]

    concat = KIT / "video-concat.txt"
    lines: list[str] = []
    for frame_path, duration in scenes:
        lines.append(f"file '{frame_path.as_posix()}'")
        lines.append(f"duration {duration}")
    lines.append(f"file '{scenes[-1][0].as_posix()}'")
    concat.write_text("\n".join(lines) + "\n", encoding="utf-8")

    total_duration = sum(duration for _, duration in scenes)
    output = KIT / "SIH2026_YouTube_Storyboard_Guide.mp4"
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg,
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
    build()
