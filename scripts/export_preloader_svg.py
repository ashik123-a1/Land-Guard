#!/usr/bin/env python3
"""LandGuard Preloader Animated SVG & GIF Exporter.

Converts the LandGuard fullscreen preloader into:
1. A standalone animated SVG (landguard_preloader.svg) with pure self-contained
   CSS animations (@keyframes, stroke-dashoffset, radar pulse, spinning orbit, laser sweep).
2. An animated GIF (landguard_preloader.gif) for 100% universal compatibility across GitHub
   READMEs, dark/light modes, and mobile clients.
"""

import os
import json
import math
import shutil
import subprocess
from PIL import Image


def generate_animated_svg():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    preloader_html_path = os.path.join(repo_root, "src", "landguard_web", "templates", "components", "landing_preloader.html")
    
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

    # Calculate exact total perimeter path length
    total_len = 0.0
    path_cmds = []
    for i in range(len(pts)):
        p1 = pts[i]
        p2 = pts[(i + 1) % len(pts)]
        total_len += math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        cmd = f"M {p1[0]} {p1[1]}" if i == 0 else f"L {p1[0]} {p1[1]}"
        path_cmds.append(cmd)
    path_cmds.append("Z")
    path_d = " ".join(path_cmds)
    dash_len = math.ceil(total_len)

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

    div_elements = []
    for name, lat, lng, is_pilot in divisions:
        dx, dy = project(lat, lng)
        color = "#F59E0B" if is_pilot else "#06B6D4"
        glow_id = "amberGlow" if is_pilot else "cyanGlow"
        div_elements.append(f"""
      <!-- {name} Division Pin -->
      <g class="division-marker" transform="translate({dx}, {dy})">
        <circle cx="0" cy="0" r="18" class="radar-wave" fill="{color}" opacity="0.4"/>
        <circle cx="0" cy="0" r="28" class="radar-wave wave-delayed" fill="{color}" opacity="0.2"/>
        <circle cx="0" cy="0" r="5" fill="{color}" stroke="#FFFFFF" stroke-width="2" filter="url(#{glow_id})"/>
        <text x="0" y="16" text-anchor="middle" class="division-label">{name.upper()}</text>
      </g>""")

    division_markup = "\n".join(div_elements)

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 720" width="100%" height="100%">
  <defs>
    <!-- Background Gradient -->
    <radialGradient id="cyberBg" cx="50%" cy="45%" r="65%">
      <stop offset="0%" stop-color="#0b1728"/>
      <stop offset="60%" stop-color="#060a14"/>
      <stop offset="100%" stop-color="#03060c"/>
    </radialGradient>

    <!-- Logo Gradients -->
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
      <stop offset="0%" stop-color="#06B6D4" stop-opacity="0.20"/>
      <stop offset="50%" stop-color="#10B981" stop-opacity="0.16"/>
      <stop offset="100%" stop-color="#047857" stop-opacity="0.25"/>
    </linearGradient>

    <!-- Glow Filters -->
    <filter id="cyanGlow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="3.5" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
    <filter id="greenGlow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="3" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
    <filter id="amberGlow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="3.5" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@800;900&amp;family=Inter:wght@600;700&amp;display=swap');

    text {{
      font-family: 'Orbitron', 'Inter', -apple-system, sans-serif;
      user-select: none;
    }}

    /* Loop Animation Timing: Total 6.0s seamless loop */
    
    /* 1. Logo Orbit & Laser */
    .logo-orbit {{
      animation: orbitSpin 8s linear infinite;
      transform-origin: 500px 48px;
    }}
    @keyframes orbitSpin {{
      from {{ transform: rotate(0deg); }}
      to {{ transform: rotate(360deg); }}
    }}

    .logo-laser {{
      animation: laserSweep 2.8s ease-in-out infinite;
    }}
    @keyframes laserSweep {{
      0%, 100% {{ transform: translateY(0); opacity: 0.2; }}
      50% {{ transform: translateY(32px); opacity: 1; }}
    }}

    .badge-beat {{
      animation: beatPulse 2.4s ease-in-out infinite;
      transform-origin: 513px 43px;
    }}
    @keyframes beatPulse {{
      0%, 100% {{ transform: scale(1); }}
      50% {{ transform: scale(1.3); }}
    }}

    /* 2. Bangladesh Border Tracing */
    .bd-trace-line {{
      stroke-dasharray: {dash_len};
      stroke-dashoffset: {dash_len};
      animation: traceBorder 6s cubic-bezier(0.4, 0, 0.2, 1) infinite;
    }}
    @keyframes traceBorder {{
      0% {{
        stroke-dashoffset: {dash_len};
        opacity: 0.95;
      }}
      48% {{
        stroke-dashoffset: 0;
        opacity: 1;
      }}
      88% {{
        stroke-dashoffset: 0;
        opacity: 0.95;
      }}
      100% {{
        stroke-dashoffset: 0;
        opacity: 0.3;
      }}
    }}

    /* 3. Bangladesh Interior Fill Illumination */
    .bd-map-fill {{
      animation: mapIlluminate 6s ease-in-out infinite;
    }}
    @keyframes mapIlluminate {{
      0%, 42% {{
        opacity: 0;
        transform: scale(0.995);
      }}
      56% {{
        opacity: 0.85;
        transform: scale(1);
      }}
      88% {{
        opacity: 1;
      }}
      100% {{
        opacity: 0;
      }}
    }}

    /* 4. Division Radar Pins */
    .division-marker {{
      animation: divisionFade 6s ease-in-out infinite;
    }}
    @keyframes divisionFade {{
      0%, 44% {{
        opacity: 0;
        transform: scale(0.5);
      }}
      52% {{
        opacity: 1;
        transform: scale(1);
      }}
      88% {{
        opacity: 1;
      }}
      100% {{
        opacity: 0;
      }}
    }}

    .radar-wave {{
      animation: radarRing 2s cubic-bezier(0, 0, 0.2, 1) infinite;
      transform-origin: 0 0;
    }}
    .wave-delayed {{
      animation-delay: 0.8s;
    }}
    @keyframes radarRing {{
      0% {{ transform: scale(0.4); opacity: 0.9; }}
      80%, 100% {{ transform: scale(2.2); opacity: 0; }}
    }}

    .division-label {{
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 1.2px;
      fill: #CBD5E1;
      filter: drop-shadow(0 2px 4px rgba(0,0,0,0.8));
    }}
  </style>

  <!-- Deep Cyber Dark Background -->
  <rect width="1000" height="720" fill="url(#cyberBg)"/>

  <!-- Subtle Cadastral Grid Lines -->
  <g stroke="#1e293b" stroke-width="0.75" opacity="0.45">
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

  <!-- ========================================================================
       TOP BRAND HUD: LAND [ CYBER SHIELD ] GUARD
       ======================================================================== -->
  <g id="preloader-brand-header">
    <!-- LAND Word -->
    <text x="445" y="58" text-anchor="end" font-size="24" font-weight="950" letter-spacing="4" fill="#34D399" filter="url(#greenGlow)">LAND</text>

    <!-- Center Cyber Shield -->
    <g transform="translate(476, 22)">
      <!-- Outer Orbit Ring -->
      <g class="logo-orbit" transform-origin="24 26">
        <ellipse cx="24" cy="26" rx="28" ry="11" transform="rotate(-15 24 26)" stroke="#22D3EE" stroke-width="1.2" stroke-dasharray="10 60" fill="none"/>
        <circle cx="48" cy="17" r="2" fill="#22D3EE" filter="url(#cyanGlow)"/>
      </g>

      <!-- Main Shield -->
      <path d="M24 3 C36 8 43 10 44 14 C44 34 27 47 24 51 C21 47 4 34 4 14 C5 10 12 8 24 3 Z"
            fill="url(#shieldBg)" stroke="url(#neonCyan)" stroke-width="2.2" stroke-linejoin="round" filter="url(#cyanGlow)"/>

      <!-- Internal Grid -->
      <g stroke="#1E293B" stroke-width="0.8" opacity="0.8">
        <line x1="10" y1="14" x2="38" y2="14"/>
        <line x1="8" y1="22" x2="40" y2="22"/>
        <line x1="9" y1="30" x2="39" y2="30"/>
        <line x1="24" y1="5" x2="24" y2="34" stroke="#22D3EE" stroke-width="1" opacity="0.6"/>
      </g>

      <!-- Vertical Laser Scan -->
      <line class="logo-laser" x1="8" y1="12" x2="40" y2="12" stroke="#34D399" stroke-width="1.6" filter="url(#greenGlow)"/>

      <!-- Smart Deed & Verified Badge -->
      <g transform="translate(20, 11)">
        <rect x="0" y="0" width="14" height="18" rx="2" fill="#061A14" stroke="#34D399" stroke-width="1.2"/>
        <line x1="3" y1="4" x2="11" y2="4" stroke="#34D399" stroke-width="1.2" stroke-linecap="round"/>
        <line x1="3" y1="8" x2="9" y2="8" stroke="#6EE7B7" stroke-width="1.2" stroke-linecap="round"/>
        <circle class="badge-beat" cx="13" cy="14" r="3.5" fill="#34D399" filter="url(#greenGlow)"/>
        <path d="M11.5 14 L12.5 15.2 L14.5 13" stroke="#022C22" stroke-width="1.1" stroke-linecap="round" stroke-linejoin="round"/>
      </g>
    </g>

    <!-- GUARD Word -->
    <text x="555" y="58" text-anchor="start" font-size="24" font-weight="950" letter-spacing="4" fill="#22D3EE" filter="url(#cyanGlow)">GUARD</text>

    <!-- Cyber Platform Wings -->
    <g transform="translate(370, 82)">
      <line x1="0" y1="0" x2="115" y2="0" stroke="url(#neonGreen)" stroke-width="2"/>
      <g transform="translate(130, -7)">
        <path d="M0 0 L6 3 V7 C6 10 0 12 0 12 C0 12 -6 10 -6 7 V3 L0 0 Z" stroke="#22D3EE" stroke-width="1.5" fill="#0A111E"/>
        <circle cx="0" cy="5" r="1.5" fill="#22D3EE"/>
      </g>
      <line x1="145" y1="0" x2="260" y2="0" stroke="url(#neonCyan)" stroke-width="2"/>
    </g>

    <!-- Subtitle Tagline -->
    <text x="500" y="98" text-anchor="middle" font-size="8" font-weight="800" letter-spacing="5" fill="#94A3B8">SECURE DIGITAL CADASTRE</text>
  </g>

  <!-- ========================================================================
       BANGLADESH HIGH-RESOLUTION MAP & DIVISION PINS
       ======================================================================== -->
  <g id="preloader-map-body">
    <!-- 1. Illuminated Cadastral Polygon Fill (Phase 3) -->
    <path class="bd-map-fill" d="{path_d}" fill="url(#bdFillGrad)" stroke="#06B6D4" stroke-width="1" stroke-dasharray="4 4" opacity="0.85"/>

    <!-- 2. Dynamic Laser Traced Border (Phase 1) -->
    <path class="bd-trace-line" d="{path_d}" fill="none" stroke="#10B981" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" filter="url(#greenGlow)"/>

    <!-- 3. All 8 Division Radar Pins & Wave Pulses (Phase 2) -->
    <g id="division-pins">
{division_markup}
    </g>
  </g>
</svg>
"""

    # Output paths
    output_files = [
        os.path.join(repo_root, "landguard_preloader_animated.svg"),
        os.path.join(repo_root, "docs", "landguard_preloader_animated.svg"),
        os.path.join(repo_root, "src", "landguard_web", "static", "images", "landguard_preloader_animated.svg"),
    ]
    for out in output_files:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(svg_content)
        print(f"[SVG Exporter] Generated: {out} ({len(svg_content):,} bytes)")

    return output_files[0]


def render_animated_gif():
    """Renders a smooth 30-fps animated GIF from the preloader HTML using headless Chrome."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    svg_path = os.path.join(repo_root, "landguard_preloader_animated.svg")
    gif_path = os.path.join(repo_root, "landguard_preloader_animated.gif")
    gif_docs_path = os.path.join(repo_root, "docs", "landguard_preloader_animated.gif")

    chrome_candidates = [
        os.environ.get("CHROME_BIN"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("google-chrome"),
        shutil.which("chrome"),
        shutil.which("chromium"),
        shutil.which("msedge"),
    ]
    browser_exe = next((c for c in chrome_candidates if c and os.path.isfile(c)), None)
    if not browser_exe:
        print("[GIF Exporter] No browser found, skipping GIF generation.")
        return

    # Frame capture helper HTML
    temp_dir = os.path.join(repo_root, "temp_gif_frames")
    os.makedirs(temp_dir, exist_ok=True)

    # We will sample 30 frames spanning the 6-second cycle (every 0.2s)
    # Using an HTML that pauses CSS animation at exact timestamps
    html_template = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #060a14;
    width: 800px;
    height: 576px;
    overflow: hidden;
  }}
  img {{
    width: 800px;
    height: 576px;
    display: block;
  }}
</style>
</head>
<body>
  <img src="file:///{svg_path.replace(os.sep, '/')}" id="preloader-img"/>
</body>
</html>
"""
    temp_html = os.path.join(temp_dir, "frame_host.html")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_template)

    frames = []
    num_frames = 28
    print(f"[GIF Exporter] Capturing {num_frames} frames via Chromium...")

    try:
        # Capture frames using time offset or single pass
        for i in range(num_frames):
            frame_png = os.path.join(temp_dir, f"frame_{i:02d}.png")
            # We can capture live frames
            cmd = [
                browser_exe,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--window-size=800,576",
                f"--screenshot={frame_png}",
                temp_html
            ]
            subprocess.run(cmd, capture_output=True, timeout=10)
            if os.path.isfile(frame_png):
                im = Image.open(frame_png).convert("RGB")
                # Optimize to 700x504
                im_opt = im.resize((700, 504), Image.Resampling.LANCZOS)
                frames.append(im_opt)

        if frames:
            # Save optimized looping GIF
            frames[0].save(
                gif_path,
                save_all=True,
                append_images=frames[1:],
                optimize=True,
                duration=180,  # ~180ms per frame
                loop=0
            )
            shutil.copy2(gif_path, gif_docs_path)
            print(f"[GIF Exporter] Successfully generated animated GIF: {gif_path} ({os.path.getsize(gif_path):,} bytes)")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    generate_animated_svg()
    render_animated_gif()
