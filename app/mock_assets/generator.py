import re
from pathlib import Path
from typing import Iterable, List, Optional

from PIL import Image, ImageDraw, ImageFont

CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 720
BG_COLOR = (245, 248, 252)
PANEL_COLOR = (255, 255, 255)
TITLE_COLOR = (20, 35, 64)
ACCENT_COLOR = (42, 91, 170)
SOFT_ACCENT = (221, 232, 247)
TEXT_COLOR = (67, 77, 93)
MUTED_TEXT = (111, 123, 145)
LINE_COLOR = (163, 186, 218)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return slug.strip("_") or "asset"


class MockAssetGenerator:
    """Generate lightweight placeholder PNGs for the presentation.

    These assets make the deck demo-ready today, and can later be replaced by
    real renders simply by passing a concrete `image_path` in slide payloads.
    """

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def ensure_asset(
        self,
        kind: str,
        title: str,
        subtitle: str = "",
        labels: Optional[Iterable[str]] = None,
        filename_hint: Optional[str] = None,
    ) -> str:
        safe_name = _slugify(filename_hint or title)
        asset_path = self.output_dir / "{0}_{1}.png".format(kind, safe_name)
        if not asset_path.exists():
            self._create_asset(
                asset_path=asset_path,
                kind=kind,
                title=title,
                subtitle=subtitle,
                labels=list(labels or []),
            )
        return str(asset_path.resolve())

    def _create_asset(
        self,
        asset_path: Path,
        kind: str,
        title: str,
        subtitle: str,
        labels: List[str],
    ) -> None:
        image = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(image)
        self._draw_background(draw)
        self._draw_header(draw, title, subtitle or "Mock generated asset")

        if kind == "workflow":
            self._draw_workflow(draw, labels)
        elif kind == "software_architecture":
            self._draw_architecture(draw, labels)
        elif kind == "module":
            self._draw_module(draw, labels)
        else:
            self._draw_overview(draw, labels)

        self._draw_footer(draw)
        image.save(asset_path, format="PNG")

    def _draw_background(self, draw: ImageDraw.ImageDraw) -> None:
        draw.rounded_rectangle((40, 40, 1240, 680), radius=28, fill=PANEL_COLOR, outline=LINE_COLOR, width=3)
        draw.rectangle((40, 40, 1240, 130), fill=SOFT_ACCENT)
        draw.ellipse((980, 470, 1180, 670), fill=(234, 242, 252))
        draw.ellipse((1080, 500, 1240, 660), fill=(226, 236, 249))

    def _draw_header(self, draw: ImageDraw.ImageDraw, title: str, subtitle: str) -> None:
        title_font = self._font(34, bold=True)
        subtitle_font = self._font(18)
        draw.text((85, 68), title, fill=TITLE_COLOR, font=title_font)
        draw.text((85, 105), subtitle, fill=MUTED_TEXT, font=subtitle_font)
        draw.rounded_rectangle((1040, 62, 1185, 104), radius=16, fill=ACCENT_COLOR)
        draw.text((1074, 74), "MOCK", fill=(255, 255, 255), font=self._font(18, bold=True))

    def _draw_footer(self, draw: ImageDraw.ImageDraw) -> None:
        draw.line((85, 628, 1195, 628), fill=LINE_COLOR, width=2)
        draw.text(
            (85, 642),
            "Placeholder visual generated in-app. Replace with real CAD or architecture exports later.",
            fill=MUTED_TEXT,
            font=self._font(15),
        )

    def _draw_overview(self, draw: ImageDraw.ImageDraw, labels: List[str]) -> None:
        labels = labels[:5] or ["Assembly", "Motion", "Process", "Control", "Safety"]
        draw.rounded_rectangle((465, 190, 815, 285), radius=22, fill=(229, 237, 248), outline=ACCENT_COLOR, width=3)
        draw.text((545, 225), "System Overview", fill=TITLE_COLOR, font=self._font(28, bold=True))

        x_positions = [85, 315, 545, 775, 1005]
        for index, label in enumerate(labels):
            left = x_positions[index]
            draw.rounded_rectangle(
                (left, 390, left + 180, 505),
                radius=20,
                fill=(246, 249, 253),
                outline=LINE_COLOR,
                width=3,
            )
            draw.line((640, 285, left + 90, 390), fill=ACCENT_COLOR, width=5)
            draw.text((left + 28, 430), label[:16], fill=TEXT_COLOR, font=self._font(21, bold=True))

    def _draw_workflow(self, draw: ImageDraw.ImageDraw, labels: List[str]) -> None:
        steps = labels[:5] or ["STEP Input", "BOM Import", "Tagging", "Planning", "PPT Export"]
        left = 95
        for index, step in enumerate(steps):
            draw.rounded_rectangle(
                (left, 290, left + 185, 400),
                radius=24,
                fill=(244, 248, 252),
                outline=ACCENT_COLOR if index in (0, len(steps) - 1) else LINE_COLOR,
                width=4,
            )
            draw.text((left + 28, 335), step[:18], fill=TITLE_COLOR, font=self._font(20, bold=True))
            if index < len(steps) - 1:
                draw.line((left + 186, 345, left + 225, 345), fill=ACCENT_COLOR, width=5)
                draw.polygon(
                    [(left + 225, 345), (left + 210, 336), (left + 210, 354)],
                    fill=ACCENT_COLOR,
                )
            left += 225

    def _draw_module(self, draw: ImageDraw.ImageDraw, labels: List[str]) -> None:
        modules = labels[:4] or ["Frame", "Axis", "Tooling", "Controls"]
        draw.rounded_rectangle((105, 190, 540, 545), radius=24, fill=(241, 246, 252), outline=LINE_COLOR, width=3)
        draw.text((160, 222), "Module Mockup", fill=TITLE_COLOR, font=self._font(28, bold=True))
        box_top = 285
        for label in modules:
            draw.rounded_rectangle((150, box_top, 495, box_top + 58), radius=18, fill=PANEL_COLOR, outline=LINE_COLOR, width=2)
            draw.text((180, box_top + 18), label[:24], fill=TEXT_COLOR, font=self._font(20, bold=True))
            box_top += 72

        draw.rounded_rectangle((655, 190, 1160, 545), radius=24, fill=(247, 250, 254), outline=LINE_COLOR, width=3)
        draw.text((705, 225), "DFM Focus Areas", fill=TITLE_COLOR, font=self._font(28, bold=True))
        bullets = [
            "Assembly interfaces",
            "Supplier readiness",
            "Tolerance stack-up",
            "Maintenance access",
        ]
        bullet_top = 300
        for bullet in bullets:
            draw.ellipse((712, bullet_top + 6, 728, bullet_top + 22), fill=ACCENT_COLOR)
            draw.text((745, bullet_top), bullet, fill=TEXT_COLOR, font=self._font(20))
            bullet_top += 60

    def _draw_architecture(self, draw: ImageDraw.ImageDraw, labels: List[str]) -> None:
        layers = labels[:4] or [
            "FastAPI API Layer",
            "cad_parser -> tagging -> planner -> ppt_builder",
            "Input Adapters",
            "PPT Output",
        ]
        top = 195
        for layer in layers:
            draw.rounded_rectangle((205, top, 1070, top + 76), radius=20, fill=(245, 249, 253), outline=LINE_COLOR, width=3)
            draw.text((265, top + 24), layer[:54], fill=TITLE_COLOR, font=self._font(23, bold=True))
            if top < 465:
                draw.line((640, top + 77, 640, top + 112), fill=ACCENT_COLOR, width=5)
                draw.polygon([(640, top + 112), (631, top + 98), (649, top + 98)], fill=ACCENT_COLOR)
            top += 110

    def _font(self, size: int, bold: bool = False):
        font_candidates = []
        if bold:
            font_candidates.extend(
                [
                    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                    "/Library/Fonts/Arial Bold.ttf",
                    "DejaVuSans-Bold.ttf",
                ]
            )
        else:
            font_candidates.extend(
                [
                    "/System/Library/Fonts/Supplemental/Arial.ttf",
                    "/Library/Fonts/Arial.ttf",
                    "DejaVuSans.ttf",
                ]
            )

        for candidate in font_candidates:
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
        return ImageFont.load_default()
