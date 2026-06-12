#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from collections import deque
from pathlib import Path

import fitz
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PDFS = [
    ROOT / "凯迪拉克初级.pdf",
    ROOT / "凯迪拉克中高级.pdf",
    ROOT / "a塑身机初级扫描.pdf",
    ROOT / "a_普拉提塑身机中级.pdf",
]
VISION_SCRIPT = ROOT / "wiki" / "tools" / "vision_ocr_boxes.swift"

fitz.TOOLS.mupdf_display_errors(False)


def pdf_slug(path: Path) -> str:
    return path.stem.replace(" ", "_").replace("/", "_")


def is_colored_ink(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    mx = max(rgb)
    mn = min(rgb)
    if mx < 35 or mx > 245:
        return False
    return (mx - mn) >= 12


def component_boxes(mask: bytearray, width: int, height: int) -> list[tuple[int, int, int, int, int]]:
    seen = bytearray(width * height)
    boxes: list[tuple[int, int, int, int, int]] = []
    for y in range(height):
        for x in range(width):
            index = y * width + x
            if not mask[index] or seen[index]:
                continue
            queue = deque([(x, y)])
            seen[index] = 1
            x0 = x1 = x
            y0 = y1 = y
            area = 0
            while queue:
                cx, cy = queue.pop()
                area += 1
                x0 = min(x0, cx)
                x1 = max(x1, cx)
                y0 = min(y0, cy)
                y1 = max(y1, cy)
                for ny in range(max(0, cy - 1), min(height, cy + 2)):
                    for nx in range(max(0, cx - 1), min(width, cx + 2)):
                        ni = ny * width + nx
                        if mask[ni] and not seen[ni]:
                            seen[ni] = 1
                            queue.append((nx, ny))
            boxes.append((x0, y0, x1, y1, area))
    return boxes


def colored_segments_for_line(
    image: Image.Image,
    line: dict,
    min_segment_width: int = 5,
) -> list[tuple[int, int, int, int]]:
    image_width, image_height = image.size
    x0 = max(0, int(line["x"] * image_width) - 4)
    y0 = max(0, int((1 - line["y"] - line["height"]) * image_height) - 4)
    x1 = min(image_width, int((line["x"] + line["width"]) * image_width) + 4)
    y1 = min(image_height, int((1 - line["y"]) * image_height) + 4)
    if x1 <= x0 or y1 <= y0:
        return []

    crop = image.crop((x0, y0, x1, y1)).convert("RGB")
    width, height = crop.size
    pixels = crop.load()
    mask = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            if is_colored_ink(pixels[x, y]):
                mask[y * width + x] = 1

    char_boxes = []
    for bx0, by0, bx1, by1, area in component_boxes(mask, width, height):
        box_width = bx1 - bx0 + 1
        box_height = by1 - by0 + 1
        if area < 3 or area > 1200:
            continue
        if box_height < 2 or box_height > max(46, height * 0.9):
            continue
        if box_width > max(90, width * 0.7):
            continue
        char_boxes.append((bx0 + x0, by0 + y0, bx1 + x0, by1 + y0, area))

    if not char_boxes:
        return []

    char_boxes.sort(key=lambda box: box[0])
    average_height = sum(box[3] - box[1] + 1 for box in char_boxes) / len(char_boxes)
    max_gap = max(18, int(average_height * 1.8))

    groups: list[list[tuple[int, int, int, int, int]]] = []
    current: list[tuple[int, int, int, int, int]] = []
    last_x1: int | None = None
    for box in char_boxes:
        if last_x1 is not None and box[0] - last_x1 > max_gap:
            groups.append(current)
            current = []
        current.append(box)
        last_x1 = box[2]
    if current:
        groups.append(current)

    segments = []
    for group in groups:
        gx0 = min(box[0] for box in group)
        gy0 = min(box[1] for box in group)
        gx1 = max(box[2] for box in group)
        gy1 = max(box[3] for box in group)
        if gx1 - gx0 + 1 < min_segment_width:
            continue
        segments.append((gx0 - 2, gy0 - 2, gx1 + 2, gy1 + 2))
    return segments


def colored_segments_for_ocr_line(image: Image.Image, line: dict) -> list[tuple[int, int, int, int]]:
    boxes = line.get("boxes") or []
    if not boxes:
        return colored_segments_for_line(image, line)

    image_width, image_height = image.size
    segments = []
    for box in boxes:
        box_width = box["width"] * image_width
        box_height = box["height"] * image_height
        if box_width > max(120, image_width * 0.09) or box_height > max(96, image_height * 0.055):
            continue
        segments.extend(colored_segments_for_line(image, box, min_segment_width=2))
    return segments


def vision_boxes_for_images(image_paths: list[Path]) -> dict[int, dict]:
    if not image_paths:
        return {}
    result = subprocess.run(
        ["swift", str(VISION_SCRIPT), *map(str, image_paths)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    pages = {}
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        page = json.loads(line)
        pages[int(page["page"])] = page
    return pages


def add_highlights_for_pdf(
    pdf_path: Path,
    output_path: Path,
    dpi: int,
    batch_size: int,
    max_pages: int | None,
) -> dict:
    doc = fitz.open(pdf_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    page_total = min(len(doc), max_pages or len(doc))
    scale = dpi / 72
    matrix = fitz.Matrix(scale, scale)
    stats = {
        "pdf": pdf_path.name,
        "pages": len(doc),
        "processed_pages": page_total,
        "highlight_rects": 0,
        "pages_with_highlights": 0,
    }

    with tempfile.TemporaryDirectory(prefix=f"{pdf_slug(pdf_path)}-highlight-") as tmp:
        tmp_dir = Path(tmp)
        for batch_start in range(0, page_total, batch_size):
            batch_end = min(page_total, batch_start + batch_size)
            image_paths = []
            rendered_images: dict[int, Path] = {}
            for page_index in range(batch_start, batch_end):
                page = doc[page_index]
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                image_path = tmp_dir / f"page-{page_index + 1:03d}.png"
                pixmap.save(image_path)
                image_paths.append(image_path)
                rendered_images[page_index + 1] = image_path

            ocr_pages = vision_boxes_for_images(image_paths)
            for page_number, image_path in rendered_images.items():
                page = doc[page_number - 1]
                image = Image.open(image_path).convert("RGB")
                image_width, image_height = image.size
                scale_x = image_width / page.rect.width
                scale_y = image_height / page.rect.height
                page_rects = 0
                for line in ocr_pages.get(page_number, {}).get("lines", []):
                    for x0, y0, x1, y1 in colored_segments_for_ocr_line(image, line):
                        rect = fitz.Rect(
                            max(0, x0 / scale_x),
                            max(0, y0 / scale_y),
                            min(page.rect.width, x1 / scale_x),
                            min(page.rect.height, y1 / scale_y),
                        )
                        if rect.is_empty or rect.width < 1 or rect.height < 1:
                            continue
                        page.draw_rect(
                            rect,
                            color=None,
                            fill=(1, 1, 0),
                            fill_opacity=0.35,
                            overlay=True,
                        )
                        page_rects += 1
                if page_rects:
                    stats["pages_with_highlights"] += 1
                    stats["highlight_rects"] += page_rects
            print(
                f"{pdf_path.name}: processed pages {batch_start + 1}-{batch_end}, "
                f"highlight_rects={stats['highlight_rects']}",
                flush=True,
            )

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Highlight non-black colored text in scanned Pilates PDFs.")
    parser.add_argument("pdfs", nargs="*", type=Path, default=DEFAULT_PDFS)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "highlighted_pdfs")
    parser.add_argument("--dpi", type=int, default=170)
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--max-pages", type=int, default=None, help="Debug option: only process the first N pages.")
    args = parser.parse_args()

    summary = []
    for pdf in args.pdfs:
        pdf_path = pdf if pdf.is_absolute() else ROOT / pdf
        output_path = args.output_dir / f"{pdf_path.stem}_highlighted.pdf"
        summary.append(
            add_highlights_for_pdf(
                pdf_path=pdf_path,
                output_path=output_path,
                dpi=args.dpi,
                batch_size=args.batch_size,
                max_pages=args.max_pages,
            )
        )

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
