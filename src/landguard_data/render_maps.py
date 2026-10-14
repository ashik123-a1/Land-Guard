"""Renders vector-based cadastral parcel/plot maps with boundary coordinates and metadata."""

import math
from typing import Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont
import os

FONT_PATH = "C:/Windows/Fonts/arial.ttf"
FONT_BOLD_PATH = "C:/Windows/Fonts/arialbd.ttf"
BN_FONT_PATH = "C:/Windows/Fonts/Nirmala.ttf"


def get_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    if os.path.exists(path):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def render_parcel_map(doc: Dict[str, Any], width: int = 1000, height: int = 1200) -> Tuple[Image.Image, str, Dict[str, list], bool, bool]:
    img = Image.new("RGB", (width, height), color=(250, 248, 242))
    draw = ImageDraw.Draw(img)
    
    font_title = get_font(FONT_BOLD_PATH, 24)
    font_body = get_font(FONT_PATH, 16)
    font_bold = get_font(FONT_BOLD_PATH, 18)
    font_watermark = get_font(FONT_BOLD_PATH, 32)
    
    bboxes = {}
    full_text_parts = []
    
    # Outer cadastral sheet border
    draw.rectangle([40, 40, width - 40, height - 40], outline=(40, 40, 40), width=3)
    draw.rectangle([48, 48, width - 48, height - 48], outline=(80, 80, 80), width=1)
    
    # Title Header Box
    title_text = doc["fields"].get("map_title", "CADASTRAL PARCEL SURVEY MAP")
    draw.text((80, 70), title_text, fill=(20, 20, 20), font=font_title)
    bboxes["title"] = [70, 80, 105, width - 80]
    full_text_parts.append(title_text)
    
    scale_text = f"Scale: {doc['fields'].get('scale', '1:1000')} | Area: {doc['fields'].get('total_area_decimal')} Decimals"
    draw.text((80, 110), scale_text, fill=(60, 60, 60), font=font_body)
    bboxes["scale"] = [110, 80, 135, 500]
    full_text_parts.append(scale_text)
    
    # Compass / North Arrow at top right
    cx, cy = width - 130, 130
    draw.polygon([(cx, cy - 45), (cx - 15, cy + 15), (cx, cy), (cx, cy - 45)], fill=(30, 30, 30))
    draw.polygon([(cx, cy - 45), (cx + 15, cy + 15), (cx, cy), (cx, cy - 45)], fill=(120, 120, 120))
    draw.text((cx - 7, cy - 75), "N", fill=(10, 10, 10), font=font_bold)
    full_text_parts.append("N")
    
    # Central Cadastral Plot Grid
    grid_top, grid_left = 220, 100
    grid_w, grid_h = 800, 750
    draw.rectangle([grid_left, grid_top, grid_left + grid_w, grid_top + grid_h], outline=(150, 150, 150), width=1)
    
    # Draw adjacent plots
    # Center target plot
    target_dag = doc["fields"]["dag_plot_number"]
    cw, ch = 360, 320
    center_x, center_y = grid_left + 220, grid_top + 200
    
    # Neighbor plots
    north_label = f"DAG #{int(target_dag) - 1} (North)"
    draw.rectangle([grid_left + 20, grid_top + 20, center_x + cw + 180, center_y - 20], outline=(100, 100, 100), width=2, fill=(242, 240, 235))
    draw.text((grid_left + 250, grid_top + 90), north_label, fill=(50, 50, 50), font=font_bold)
    full_text_parts.append(north_label)
    
    # Main highlighted parcel polygon
    draw.rectangle([center_x, center_y, center_x + cw, center_y + ch], outline=(180, 20, 20), width=4, fill=(255, 252, 240))
    draw.text((center_x + 90, center_y + 110), f"TARGET PLOT #{target_dag}", fill=(180, 20, 20), font=font_bold)
    draw.text((center_x + 90, center_y + 145), f"Area: {doc['fields']['total_area_decimal']} Dec.", fill=(40, 40, 40), font=font_body)
    bboxes["target_plot"] = [center_y, center_x, center_y + ch, center_x + cw]
    full_text_parts.append(f"TARGET PLOT #{target_dag}")
    full_text_parts.append(f"Area: {doc['fields']['total_area_decimal']} Dec.")

    south_label = f"DAG #{int(target_dag) + 1} (South)"
    draw.rectangle([grid_left + 20, center_y + ch + 20, center_x + cw + 180, grid_top + grid_h - 20], outline=(100, 100, 100), width=2, fill=(242, 240, 235))
    draw.text((grid_left + 250, center_y + ch + 90), south_label, fill=(50, 50, 50), font=font_bold)
    full_text_parts.append(south_label)
    
    # Scale Bar at bottom
    bar_x, bar_y = 120, height - 120
    draw.line([(bar_x, bar_y), (bar_x + 300, bar_y)], fill=(30, 30, 30), width=3)
    draw.line([(bar_x, bar_y - 10), (bar_x, bar_y + 10)], fill=(30, 30, 30), width=3)
    draw.line([(bar_x + 150, bar_y - 6), (bar_x + 150, bar_y + 6)], fill=(30, 30, 30), width=2)
    draw.line([(bar_x + 300, bar_y - 10), (bar_x + 300, bar_y + 10)], fill=(30, 30, 30), width=3)
    draw.text((bar_x - 5, bar_y + 15), "0m", fill=(40, 40, 40), font=font_body)
    draw.text((bar_x + 135, bar_y + 15), "50m", fill=(40, 40, 40), font=font_body)
    draw.text((bar_x + 280, bar_y + 15), "100m", fill=(40, 40, 40), font=font_body)
    full_text_parts.append("0m 50m 100m")
    
    # Legend
    legend_text = "LEGEND: Cadastral Survey Boundary (Simulated)"
    draw.text((width - 380, height - 130), legend_text, fill=(50, 50, 50), font=font_body)
    full_text_parts.append(legend_text)
    
    # Prominent Synthetic Watermark (Mandatory)
    wm_text = "SYNTHETIC DEMO — NOT AN OFFICIAL DOCUMENT"
    wm_overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    wm_draw = ImageDraw.Draw(wm_overlay)
    
    # Draw two diagonal watermarks across page
    for offset_y in [400, 800]:
        wm_draw.text((90, offset_y), wm_text, fill=(200, 40, 40, 85), font=font_watermark)
    
    img = Image.alpha_composite(img.convert("RGBA"), wm_overlay).convert("RGB")
    
    return img, "\n".join(full_text_parts), bboxes, False, True
