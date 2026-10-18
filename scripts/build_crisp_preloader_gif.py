#!/usr/bin/env python3
"""Generates a perfectly choreographed, ultra-smooth animated GIF of the LandGuard Preloader.

Frames:
- Phase 1 (Frames 0-14): Green laser tracer sweeps along Bangladesh 594-point border.
- Phase 2 (Frames 15-20): Perimeter closes, 8 division radar pins ignite with pulsing wave rings.
- Phase 3 (Frames 21-27): Luminous cyan/emerald map fill illuminates the entire nation.
- Phase 4 (Frames 28-31): Peak brilliance showcase before smooth looping.
"""

import os
import json
import math
import shutil
import subprocess
from PIL import Image


def generate_choreographed_gif():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    preloader_html_path = os.path.join(repo_root, "src", "landguard_web", "templates", "components", "landing_preloader.html")
    gif_root = os.path.join(repo_root, "landguard_preloader_animated.gif")
    gif_docs = os.path.join(repo_root, "docs", "landguard_preloader_animated.gif")
    gif_static = os.path.join(repo_root, "src", "landguard_web", "static", "images", "landguard_preloader_animated.gif")

    with open(preloader_html_path, "r", encoding="utf-8") as f:
        text = f.read()

    start_marker = "const BD_ACCURATE_BORDER_POINTS = "
    end_marker = "];"
    idx1 = text.find(start_marker) + len(start_marker)
    idx2 = text.find(end_marker, idx1) + 1
    coords = json.loads(text[idx1:idx2])

    lat_min, lat_max = 20.65, 26.75
    lng_min, lng_max = 87.95, 92.75
    map_top = 155
    map_bottom = 690
    map_h = map_bottom - map_top
    cos_lat = math.cos(math.radians(23.7))
    scale_y = map_h / (lat_max - lat_min)
    scale_x = scale_y * cos_lat
    map_w = (lng_max - lng_min) * scale_x
    map_left = (1000 - map_w) / 2

    def project(lat, lng):
        return round(map_left + (lng - lng_min) * scale_x, 1), round(map_top + (lat_max - lat) * scale_y, 1)

    pts = [project(lat, lng) for lat, lng in coords]
    total_pts = len(pts)

    divisions = [
        ("Dhaka", 23.8103, 90.4125, True),
        ("Chattogram", 22.3569, 91.7832, False),
        ("Rajshahi", 24.3636, 88.6241, True),
        ("Khulna", 22.8456, 89.5403, True),
        ("Sylhet", 24.8949, 91.8687, False),
        ("Barishal", 22.7010, 90.3535, False),
        ("Rangpur", 25.7439, 89.2752, False),
        ("Mymensingh", 24.7471, 90.4203, False),
    ]

    chrome_candidates = [
        os.environ.get("CHROME_BIN"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    browser_exe = next((c for c in chrome_candidates if c and os.path.isfile(c)), None)

    temp_dir = os.path.join(repo_root, "temp_gif_render")
    os.makedirs(temp_dir, exist_ok=True)

    num_frames = 32
    frames = []

    print(f"[GIF Builder] Rendering {num_frames} choreographed frames...")

    try:
        for f_idx in range(num_frames):
            progress = f_idx / (num_frames - 1)  # 0.0 to 1.0

            # 1. Tracing progress (0.0 to 0.48 of total loop)
            trace_u = min(1.0, progress / 0.48)
            current_pt_count = max(2, int(trace_u * total_pts))
            sub_pts = pts[:current_pt_count]

            trace_cmds = [f"M {sub_pts[0][0]} {sub_pts[0][1]}"]
            for p in sub_pts[1:]:
                trace_cmds.append(f"L {p[0]} {p[1]}")
            if trace_u >= 1.0:
                trace_cmds.append("Z")
            trace_d = " ".join(trace_cmds)

            # Laser tracer head dot
            head_x, head_y = sub_pts[-1]

            # 2. Map fill opacity (starts after tracing completes at 0.48, reaches peak at 0.85)
            if progress < 0.48:
                fill_opacity = 0.0
            else:
                fill_ratio = (progress - 0.48) / (0.85 - 0.48)
                fill_opacity = min(0.32, fill_ratio * 0.32)

            # 3. Division pins opacity & pulse ring
            if progress < 0.44:
                div_opacity = 0.0
                ring_r = 10
            else:
                div_opacity = min(1.0, (progress - 0.44) / 0.10)
                # Pulse cycle: 3 pulses across remaining frames
                wave_t = ((progress - 0.44) * 5.0) % 1.0
                ring_r = 8 + int(wave_t * 24)

            # Full polygon path for fill
            full_cmds = [f"M {pts[0][0]} {pts[0][1]}"]
            for p in pts[1:]:
                full_cmds.append(f"L {p[0]} {p[1]}")
            full_cmds.append("Z")
            full_d = " ".join(full_cmds)

            # Build division pins markup
            div_svg = []
            if div_opacity > 0:
                for name, lat, lng, is_pilot in divisions:
                    dx, dy = project(lat, lng)
                    color = "#F59E0B" if is_pilot else "#06B6D4"
                    div_svg.append(f"""
                    <g transform="translate({dx}, {dy})" opacity="{div_opacity:.2f}">
                      <circle cx="0" cy="0" r="{ring_r}" fill="none" stroke="{color}" stroke-width="1.8" opacity="0.6"/>
                      <circle cx="0" cy="0" r="5" fill="{color}" stroke="#FFFFFF" stroke-width="1.8"/>
                      <text x="0" y="16" text-anchor="middle" font-family="Orbitron, Inter, sans-serif" font-size="9" font-weight="700" fill="#CBD5E1">{name.upper()}</text>
                    </g>
                    """)
            div_markup = "\n".join(div_svg)

            # Orbit angle
            orbit_deg = int((progress * 360) % 360)

            frame_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 720" width="800" height="576">
  <defs>
    <radialGradient id="cyberBg" cx="50%" cy="45%" r="65%">
      <stop offset="0%" stop-color="#0b1728"/>
      <stop offset="60%" stop-color="#060a14"/>
      <stop offset="100%" stop-color="#03060c"/>
    </radialGradient>
    <linearGradient id="shieldBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0F172A"/>
      <stop offset="50%" stop-color="#0A221C"/>
      <stop offset="100%" stop-color="#02150F"/>
    </linearGradient>
    <linearGradient id="neonCyan" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#22D3EE"/>
      <stop offset="100%" stop-color="#06B6D4"/>
    </linearGradient>
    <linearGradient id="neonGreen" x1="0%" y1="100%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#065F46"/>
      <stop offset="60%" stop-color="#34D399"/>
      <stop offset="100%" stop-color="#6EE7B7"/>
    </linearGradient>
    <linearGradient id="bdFillGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#06B6D4" stop-opacity="0.35"/>
      <stop offset="50%" stop-color="#10B981" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="#047857" stop-opacity="0.40"/>
    </linearGradient>
    <filter id="greenGlow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="3.5" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <rect width="1000" height="720" fill="url(#cyberBg)"/>

  <!-- Subtle Cadastral Grid -->
  <g stroke="#1e293b" stroke-width="0.8" opacity="0.45">
    <line x1="100" y1="0" x2="100" y2="720"/>
    <line x1="250" y1="0" x2="250" y2="720"/>
    <line x1="400" y1="0" x2="400" y2="720"/>
    <line x1="550" y1="0" x2="550" y2="720"/>
    <line x1="700" y1="0" x2="700" y2="720"/>
    <line x1="850" y1="0" x2="850" y2="720"/>
    <line x1="0" y1="120" x2="1000" y2="120"/>
    <line x1="0" y1="260" x2="1000" y2="260"/>
    <line x1="0" y1="400" x2="1000" y2="400"/>
    <line x1="0" y1="540" x2="1000" y2="540"/>
    <line x1="0" y1="660" x2="1000" y2="660"/>
  </g>

  <!-- Top Logo HUD -->
  <g id="preloader-brand">
    <text x="445" y="58" text-anchor="end" font-family="Orbitron, Inter, sans-serif" font-size="24" font-weight="950" letter-spacing="4" fill="#34D399" filter="url(#greenGlow)">LAND</text>
    <g transform="translate(476, 22)">
      <!-- Spinning Orbit -->
      <g transform="rotate({orbit_deg} 24 26)">
        <ellipse cx="24" cy="26" rx="28" ry="11" stroke="#22D3EE" stroke-width="1.4" stroke-dasharray="10 60" fill="none"/>
        <circle cx="48" cy="17" r="2.5" fill="#22D3EE"/>
      </g>
      <!-- Shield Frame -->
      <path d="M24 3 C36 8 43 10 44 14 C44 34 27 47 24 51 C21 47 4 34 4 14 C5 10 12 8 24 3 Z"
            fill="url(#shieldBg)" stroke="url(#neonCyan)" stroke-width="2.4" stroke-linejoin="round"/>
      <!-- Smart Deed & Badge -->
      <g transform="translate(20, 11)">
        <rect x="0" y="0" width="14" height="18" rx="2" fill="#061A14" stroke="#34D399" stroke-width="1.4"/>
        <line x1="3" y1="4" x2="11" y2="4" stroke="#34D399" stroke-width="1.4" stroke-linecap="round"/>
        <line x1="3" y1="8" x2="9" y2="8" stroke="#6EE7B7" stroke-width="1.4" stroke-linecap="round"/>
        <circle cx="13" cy="14" r="3.5" fill="#34D399"/>
        <path d="M11.5 14 L12.5 15.2 L14.5 13" stroke="#022C22" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
      </g>
    </g>
    <text x="555" y="58" text-anchor="start" font-family="Orbitron, Inter, sans-serif" font-size="24" font-weight="950" letter-spacing="4" fill="#22D3EE">GUARD</text>
    <g transform="translate(370, 82)">
      <line x1="0" y1="0" x2="115" y2="0" stroke="url(#neonGreen)" stroke-width="2"/>
      <g transform="translate(130, -7)">
        <path d="M0 0 L6 3 V7 C6 10 0 12 0 12 C0 12 -6 10 -6 7 V3 L0 0 Z" stroke="#22D3EE" stroke-width="1.5" fill="#0A111E"/>
        <circle cx="0" cy="5" r="1.5" fill="#22D3EE"/>
      </g>
      <line x1="145" y1="0" x2="260" y2="0" stroke="url(#neonCyan)" stroke-width="2"/>
    </g>
    <text x="500" y="98" text-anchor="middle" font-family="Orbitron, Inter, sans-serif" font-size="8" font-weight="800" letter-spacing="5" fill="#94A3B8">SECURE DIGITAL CADASTRE</text>
  </g>

  <!-- Map Graphics -->
  <!-- 1. Illuminated Fill -->
  <path d="{full_d}" fill="url(#bdFillGrad)" opacity="{fill_opacity:.2f}"/>

  <!-- 2. Animated Traced Border -->
  <path d="{trace_d}" fill="none" stroke="#10B981" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" filter="url(#greenGlow)"/>

  <!-- 3. Laser Tracer Head -->
  <g transform="translate({head_x}, {head_y})" opacity="{1.0 if trace_u < 1.0 else 0.0}">
    <circle cx="0" cy="0" r="12" fill="#10B981" opacity="0.35"/>
    <circle cx="0" cy="0" r="5" fill="#FFFFFF" stroke="#10B981" stroke-width="2"/>
  </g>

  <!-- 4. Division Radar Pins -->
  {div_markup}
</svg>
"""
            frame_svg_path = os.path.join(temp_dir, f"frame_{f_idx:02d}.svg")
            frame_png_path = os.path.join(temp_dir, f"frame_{f_idx:02d}.png")
            with open(frame_svg_path, "w", encoding="utf-8") as f:
                f.write(frame_svg)

            # Render to PNG with Chromium
            cmd = [
                browser_exe,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--window-size=800,576",
                f"--screenshot={frame_png_path}",
                frame_svg_path
            ]
            subprocess.run(cmd, capture_output=True, timeout=10)
            if os.path.isfile(frame_png_path):
                im = Image.open(frame_png_path).convert("RGB")
                # Scale down for lightweight, super-fast loading on GitHub
                im_opt = im.resize((700, 504), Image.Resampling.LANCZOS)
                frames.append(im_opt)

        if frames:
            # Durations per frame (ms)
            # Normal frames: ~140ms
            # Hold last illuminated frame slightly longer: ~800ms
            durations = [140] * (len(frames) - 1) + [800]

            frames[0].save(
                gif_root,
                save_all=True,
                append_images=frames[1:],
                optimize=True,
                duration=durations,
                loop=0
            )
            shutil.copy2(gif_root, gif_docs)
            shutil.copy2(gif_root, gif_static)
            print(f"[GIF Builder] Successfully built looping animated GIF:\n  - {gif_root} ({os.path.getsize(gif_root):,} bytes)\n  - {gif_docs}\n  - {gif_static}")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    generate_choreographed_gif()
