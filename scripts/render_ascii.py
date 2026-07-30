#!/usr/bin/env python3
from __future__ import annotations

import argparse
from html import escape
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps
from rembg import remove

RAMP = " .,:;irsXA253hMHGS#9B&@"
COLS = 92
ROW_ASPECT = 0.49
FONT_SIZE = 12.5
CHAR_WIDTH = 7.5
LINE_HEIGHT = 14.4
ROW_DELAY = 0.045

LIGHT = "#57606a"
DARK = "#c9d1d9"
CURSOR_LIGHT = "#24292f"
CURSOR_DARK = "#f0f6fc"

def detect_face_crop(image: Image.Image) -> Image.Image:
    rgb = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(str(cascade_path))
    faces = cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=5, minSize=(48, 48))

    w, h = image.size
    if len(faces):
        x, y, fw, fh = max(faces, key=lambda r: r[2] * r[3])
        cx = x + fw / 2
        cy = y + fh / 2 - fh * 0.08
        side = max(fw, fh) * 2.35

        left = int(max(0, cx - side / 2))
        top = int(max(0, cy - side * 0.43))
        right = int(min(w, left + side))
        bottom = int(min(h, top + side))

        actual = int(min(right - left, bottom - top))
        left = max(0, min(left, w - actual))
        top = max(0, min(top, h - actual))
        return image.crop((left, top, left + actual, top + actual))

    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    return image.crop((left, top, left + side, top + side))

def prepare(path: Path) -> Image.Image:
    src = Image.open(path).convert("RGBA")
    src = detect_face_crop(src)
    cut = remove(src)

    alpha = np.asarray(cut.getchannel("A"))
    white = Image.new("RGBA", cut.size, (255, 255, 255, 255))
    gray = np.asarray(Image.alpha_composite(white, cut).convert("L"))

    gray = cv2.bilateralFilter(gray, 9, 45, 45)
    gray = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(gray)

    normalized = gray.astype(np.float32) / 255.0
    gray = np.clip(255.0 * np.power(normalized, 1.55), 0, 255).astype(np.uint8)
    gray[alpha < 24] = 255

    return Image.fromarray(gray)

def image_to_lines(image: Image.Image, cols: int) -> list[str]:
    w, h = image.size
    rows = max(1, int(cols * (h / w) * ROW_ASPECT))
    image = ImageOps.autocontrast(image)
    image = image.resize((cols, rows), Image.Resampling.LANCZOS)
    px = np.asarray(image, dtype=np.uint8)

    last = len(RAMP) - 1
    lines = []
    for row in px:
        chars = []
        for value in row:
            darkness = 1.0 - int(value) / 255.0
            index = min(last, round((darkness ** 0.90) * last))
            chars.append(RAMP[index])
        lines.append("".join(chars).rstrip())

    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines or [""]

def build_svg(lines: list[str], cols: int) -> str:
    pad_x = 18
    pad_y = 16
    width = int(cols * CHAR_WIDTH + pad_x * 2)
    height = int(len(lines) * LINE_HEIGHT + pad_y * 2)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="ASCII portrait">',
        "<style>",
        f".txt{{fill:{LIGHT};font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"
        "'Liberation Mono','Courier New',monospace}}",
        f".cur{{fill:{CURSOR_LIGHT}}}",
        "@media(prefers-color-scheme:dark){"
        f".txt{{fill:{DARK}}}.cur{{fill:{CURSOR_DARK}}}"
        "}",
        "</style>",
    ]

    for i, line in enumerate(lines):
        y = pad_y + i * LINE_HEIGHT
        start = i * ROW_DELAY
        duration = max(ROW_DELAY, min(0.45, 0.12 + len(line) * 0.002))
        width_px = max(1.0, len(line) * CHAR_WIDTH)
        clip_id = f"clip{i}"
        safe = escape(line)

        parts.append(
            f'<clipPath id="{clip_id}"><rect x="{pad_x}" y="{y:.1f}" '
            f'height="{LINE_HEIGHT:.1f}" width="0">'
            f'<animate attributeName="width" from="0" to="{width_px:.1f}" '
            f'begin="{start:.3f}s" dur="{duration:.3f}s" fill="freeze"/>'
            f'</rect></clipPath>'
        )
        parts.append(
            f'<text class="txt" xml:space="preserve" x="{pad_x}" '
            f'y="{y + FONT_SIZE:.1f}" font-size="{FONT_SIZE}" '
            f'clip-path="url(#{clip_id})">{safe}</text>'
        )
        parts.append(
            f'<rect class="cur" y="{y + 1:.1f}" width="5.5" height="{FONT_SIZE:.1f}" opacity="0">'
            f'<set attributeName="opacity" to="0.82" begin="{start:.3f}s"/>'
            f'<animate attributeName="x" from="{pad_x}" to="{pad_x + width_px:.1f}" '
            f'begin="{start:.3f}s" dur="{duration:.3f}s" fill="freeze"/>'
            f'<set attributeName="opacity" to="0" begin="{start + duration:.3f}s"/>'
            f'</rect>'
        )

    parts.append("</svg>")
    return "".join(parts)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--cols", type=int, default=COLS)
    args = parser.parse_args()

    if not 40 <= args.cols <= 160:
        raise SystemExit("--cols must be between 40 and 160")

    lines = image_to_lines(prepare(args.input), args.cols)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_svg(lines, args.cols), encoding="utf-8")
    print(f"Wrote {args.output}: {len(lines)} rows x {args.cols} columns")

if __name__ == "__main__":
    main()
