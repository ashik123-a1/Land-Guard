import os
import io
import re
import json
import time
import math
import base64
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def generate_perfectly_aligned_svg():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    preloader_html = os.path.join(repo_root, "src", "landguard_web", "templates", "components", "landing_preloader.html")
    
    # 1. Extract official 594 border points from landing_preloader.html
    with open(preloader_html, "r", encoding="utf-8") as f:
        html_src = f.read()
    m = re.search(r'const BD_ACCURATE_BORDER_POINTS = (\[\[.*?\]\]);', html_src)
    border_pts_json = m.group(1)

    # 2. Build standalone Leaflet runner with exact 1280x720 canvas
    runner_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    body, html {{ margin: 0; padding: 0; width: 1280px; height: 720px; background: #060a14; overflow: hidden; }}
    #map {{ width: 1280px; height: 720px; background: #060a14; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    const borderPoints = {border_pts_json};
    const pMap = L.map('map', {{
      center: [23.68, 90.34],
      zoom: 7,
      zoomControl: false,
      attributionControl: false
    }});
    // Fit bounds with top padding for logo
    pMap.fitBounds([[20.55, 87.8], [26.75, 92.8]], {{ padding: [90, 50] }});

    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      maxZoom: 16
    }}).addTo(pMap);

    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
      maxZoom: 16,
      opacity: 0.85
    }}).addTo(pMap);

    window.getProjectedData = function() {{
      const projectedBorder = borderPoints.map(ll => {{
        const pt = pMap.latLngToContainerPoint(ll);
        return [Math.round(pt.x * 10) / 10, Math.round(pt.y * 10) / 10];
      }});

      const divCoords = {{
        dhaka: {{ lat: 23.8103, lng: 90.4125, pilot: true }},
        chattogram: {{ lat: 22.3569, lng: 91.7832, pilot: false }},
        rajshahi: {{ lat: 24.3636, lng: 88.6241, pilot: true }},
        khulna: {{ lat: 22.8456, lng: 89.5403, pilot: true }},
        sylhet: {{ lat: 24.8949, lng: 91.8687, pilot: false }},
        barishal: {{ lat: 22.7010, lng: 90.3535, pilot: false }},
        rangpur: {{ lat: 25.7439, lng: 89.2752, pilot: false }},
        mymensingh: {{ lat: 24.7471, lng: 90.4203, pilot: false }}
      }};

      const projectedDivisions = {{}};
      for (let k in divCoords) {{
        const pt = pMap.latLngToContainerPoint([divCoords[k].lat, divCoords[k].lng]);
        projectedDivisions[k] = {{
          x: Math.round(pt.x * 10) / 10,
          y: Math.round(pt.y * 10) / 10,
          pilot: divCoords[k].pilot
        }};
      }}

      return {{ border: projectedBorder, divisions: projectedDivisions }};
    }};
  </script>
</body>
</html>"""

    runner_path = os.path.join(repo_root, "scripts", "temp_leaflet_runner.html")
    with open(runner_path, "w", encoding="utf-8") as f:
        f.write(runner_html)

    # 3. Launch Chrome to capture clean basemap & exact matching coordinates
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1280,720")

    driver = webdriver.Chrome(options=opts)
    driver.get("file:///" + runner_path.replace("\\", "/"))
    print("[1/4] Pre-warming real ArcGIS dark map tiles (5.0s)...")
    time.sleep(5.0)

    # Save screenshot of the EXACT map
    shot_path = os.path.join(repo_root, "scripts", "temp_basemap.png")
    driver.save_screenshot(shot_path)
    im = Image.open(shot_path).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=82)
    b64_map = base64.b64encode(buf.getvalue()).decode("ascii")

    # Get exact projected coordinates from the same map
    projected_data = driver.execute_script("return window.getProjectedData();")
    driver.quit()

    if os.path.exists(runner_path):
        os.remove(runner_path)
    if os.path.exists(shot_path):
        os.remove(shot_path)

    print("[2/4] Map tiles and projected coordinates retrieved successfully.")

    pts = projected_data["border"]
    divs = projected_data["divisions"]

    path_d = "M " + " L ".join(f"{p[0]} {p[1]}" for p in pts) + " Z"
    total_len = 0.0
    for i in range(1, len(pts)):
        p1, p2 = pts[i-1], pts[i]
        total_len += ((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)**0.5
    total_len += ((pts[0][0]-pts[-1][0])**2 + (pts[0][1]-pts[-1][1])**2)**0.5
    path_len_int = int(round(total_len))

    # Build division pulse nodes with native pulsing rings
    div_elements = []
    for k, d in divs.items():
        cx, cy = d["x"], d["y"]
        if d["pilot"]:
            div_elements.append(f"""    <!-- {k.upper()} (Pilot Amber) -->
    <g class="radar-node" transform="translate({cx}, {cy})">
      <circle cx="0" cy="0" r="6" fill="#F59E0B">
        <animate attributeName="r" values="6;26" dur="1.5s" repeatCount="indefinite"/>
        <animate attributeName="opacity" values="0.85;0" dur="1.5s" repeatCount="indefinite"/>
      </circle>
      <circle cx="0" cy="0" r="5.5" fill="#F59E0B" stroke="#FFFFFF" stroke-width="1.8"/>
    </g>""")
        else:
            div_elements.append(f"""    <!-- {k.upper()} (Cyan) -->
    <g class="radar-node" transform="translate({cx}, {cy})">
      <circle cx="0" cy="0" r="5" fill="#22D3EE">
        <animate attributeName="r" values="5;22" dur="1.8s" repeatCount="indefinite"/>
        <animate attributeName="opacity" values="0.85;0" dur="1.8s" repeatCount="indefinite"/>
      </circle>
      <circle cx="0" cy="0" r="4.8" fill="#22D3EE" stroke="#FFFFFF" stroke-width="1.6"/>
    </g>""")

    divisions_svg = "\n".join(div_elements)

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="100%" height="100%">
  <defs>
    <!-- Background Gradient -->
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#040810"/>
      <stop offset="50%" stop-color="#060A14"/>
      <stop offset="100%" stop-color="#020408"/>
    </linearGradient>

    <!-- Shield Gradients -->
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

    <!-- Glow Filters -->
    <filter id="glowGreen" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3.5" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
    <filter id="glowCyan" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3.5" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
    <filter id="glowShield" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="6" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <style>
  <![CDATA[
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@800;900&family=Inter:wght@600;700&display=swap');

    text {{
      font-family: 'Orbitron', 'Inter', -apple-system, sans-serif;
      user-select: none;
    }}

    /* 1. Header Animations */
    .shield-orbit {{
      animation: orbitSpin 8s linear infinite;
      transform-origin: 640px 53px;
    }}
    @keyframes orbitSpin {{
      from {{ transform: rotate(0deg); }}
      to {{ transform: rotate(360deg); }}
    }}

    .shield-laser {{
      animation: laserSweep 2.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
    }}
    @keyframes laserSweep {{
      0% {{ transform: translateY(0); opacity: 0; }}
      15% {{ opacity: 1; }}
      60% {{ transform: translateY(32px); opacity: 0.9; }}
      75% {{ opacity: 0.2; }}
      100% {{ transform: translateY(0); opacity: 0; }}
    }}

    .shield-badge-beat {{
      animation: badgeBeat 2.4s ease-in-out infinite;
      transform-origin: 647px 49px;
    }}
    @keyframes badgeBeat {{
      0%, 100% {{ transform: scale(1); }}
      50% {{ transform: scale(1.25); filter: drop-shadow(0 0 6px #34D399); }}
    }}

    .word-land {{
      animation: landFill 4.2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
    }}
    .word-guard {{
      animation: guardFill 4.2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
    }}
    @keyframes landFill {{
      0% {{ fill: rgba(52, 211, 153, 0.2); }}
      42%, 86% {{ fill: #34D399; filter: drop-shadow(0 0 10px #34D399); }}
      100% {{ fill: rgba(52, 211, 153, 0.2); }}
    }}
    @keyframes guardFill {{
      0% {{ fill: rgba(34, 211, 238, 0.2); }}
      42%, 86% {{ fill: #22D3EE; filter: drop-shadow(0 0 10px #22D3EE); }}
      100% {{ fill: rgba(34, 211, 238, 0.2); }}
    }}

    /* 2. Real ArcGIS Dark Basemap Tiles Fade-In (Phase 3) */
    .arcgis-basemap {{
      animation: basemapFade 6s ease-in-out infinite;
    }}
    @keyframes basemapFade {{
      0%, 46% {{ opacity: 0; }}
      62%, 92% {{ opacity: 1.0; }}
      100% {{ opacity: 0; }}
    }}

    /* 3. Bangladesh Boundary Tracing (Phase 1) */
    .bd-trace-poly {{
      stroke-dasharray: {path_len_int};
      stroke-dashoffset: {path_len_int};
      animation: tracePoly 6s cubic-bezier(0.4, 0, 0.2, 1) infinite;
    }}
    @keyframes tracePoly {{
      0% {{
        stroke-dashoffset: {path_len_int};
        opacity: 0.95;
      }}
      46% {{
        stroke-dashoffset: 0;
        opacity: 1;
      }}
      92% {{
        stroke-dashoffset: 0;
        opacity: 0.95;
      }}
      100% {{
        stroke-dashoffset: 0;
        opacity: 0;
      }}
    }}

    /* 4. Bangladesh Interior Luminous Cyan Fill (Phase 3) */
    .bd-fill-polygon {{
      animation: fillIlluminate 6s ease-in-out infinite;
    }}
    @keyframes fillIlluminate {{
      0%, 54% {{
        opacity: 0;
      }}
      64%, 92% {{
        opacity: 0.22;
      }}
      100% {{
        opacity: 0;
      }}
    }}

    /* 5. Division Radar Pins (Phase 2 to 4) */
    .radar-node {{
      animation: radarFade 6s ease-in-out infinite;
    }}
    @keyframes radarFade {{
      0%, 45% {{
        opacity: 0;
      }}
      52%, 92% {{
        opacity: 1;
      }}
      100% {{
        opacity: 0;
      }}
    }}

    .pulse-wave {{
      animation: wavePing 1.8s cubic-bezier(0, 0, 0.2, 1) infinite;
      transform-origin: center;
    }}
    .pulse-wave-pilot {{
      animation: wavePing 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;
      transform-origin: center;
    }}
    @keyframes wavePing {{
      0% {{
        r: 6px;
        opacity: 0.9;
      }}
      80%, 100% {{
        r: 28px;
        opacity: 0;
      }}
    }}
  ]]>
  </style>

  <!-- Deep Cyber Dark Background -->
  <rect width="1280" height="720" fill="url(#bgGrad)"/>

  <!-- Real Geographic ArcGIS Dark Basemap Tiles (Fades in Phase 3) -->
  <image class="arcgis-basemap" href="data:image/jpeg;base64,{b64_map}" x="0" y="0" width="1280" height="720" preserveAspectRatio="xMidYMid slice"/>

  <!-- Subtle Ambient Grid Lines -->
  <g stroke="#1E293B" stroke-width="0.75" opacity="0.35">
    <line x1="160" y1="0" x2="160" y2="720"/>
    <line x1="320" y1="0" x2="320" y2="720"/>
    <line x1="480" y1="0" x2="480" y2="720"/>
    <line x1="640" y1="0" x2="640" y2="720"/>
    <line x1="800" y1="0" x2="800" y2="720"/>
    <line x1="960" y1="0" x2="960" y2="720"/>
    <line x1="1120" y1="0" x2="1120" y2="720"/>
    <line x1="0" y1="120" x2="1280" y2="120"/>
    <line x1="0" y1="240" x2="1280" y2="240"/>
    <line x1="0" y1="360" x2="1280" y2="360"/>
    <line x1="0" y1="480" x2="1280" y2="480"/>
    <line x1="0" y1="600" x2="1280" y2="600"/>
  </g>

  <!-- Bangladesh Boundary and Divisions -->
  <g id="preloader-cadastre-layer">
    <!-- Bangladesh Interior Luminous Cyan Fill (Phase 3) -->
    <path class="bd-fill-polygon" d="{path_d}" fill="#06B6D4" opacity="0"/>

    <!-- Bangladesh Boundary Line Tracing (Phase 1) -->
    <path class="bd-trace-poly" d="{path_d}" fill="none" stroke="#10B981" stroke-width="2.8" stroke-dasharray="4 4" stroke-linejoin="round" filter="url(#glowGreen)"/>

    <!-- All 8 Division Radar Hubs (Phase 2 to 4) -->
    <g id="division-radar-hubs">
{divisions_svg}
    </g>
  </g>

  <!-- TOP FLOATING CYBER HUD BRAND (100% Transparent, No Border) -->
  <g id="preloader-branding">
    <!-- Word LAND -->
    <text class="word-land" x="590" y="60" text-anchor="end" font-size="24" font-weight="950" letter-spacing="5" fill="#34D399" stroke="#34D399" stroke-width="1.2">LAND</text>

    <!-- Central Cyber Shield (Centered at X=640, Y=53) -->
    <g transform="translate(615, 27)">
      <!-- Outer Spinning Orbit -->
      <g class="shield-orbit">
        <ellipse cx="25" cy="26" rx="23" ry="8.5" transform="rotate(-15 25 26)" stroke="#22D3EE" stroke-width="1.2" stroke-dasharray="8 45" fill="none"/>
        <circle cx="45" cy="18" r="1.8" fill="#22D3EE" filter="url(#glowCyan)"/>
      </g>

      <!-- Main Shield Frame -->
      <path d="M25 4 C36.5 8.5 43.5 10 44.5 14.5 C44.5 34 27.5 47 25 51 C22.5 47 5.5 34 5.5 14.5 C6.5 10 13.5 8.5 25 4 Z"
            fill="url(#shieldBg)" stroke="url(#neonCyan)" stroke-width="1.8" stroke-linejoin="round" filter="url(#glowShield)"/>

      <!-- Interior Grid -->
      <g stroke="#1E293B" stroke-width="0.8" opacity="0.8">
        <line x1="11" y1="15" x2="39" y2="15"/>
        <line x1="9" y1="22" x2="41" y2="22"/>
        <line x1="9" y1="29" x2="41" y2="29"/>
        <line x1="25" y1="6" x2="25" y2="31" stroke="#22D3EE" stroke-width="0.9" opacity="0.6"/>
      </g>

      <!-- Vertical Laser Sweep -->
      <line class="shield-laser" x1="8" y1="11" x2="42" y2="11" stroke="#34D399" stroke-width="1.5" filter="url(#glowGreen)"/>

      <!-- Smart Deed and Verified Check Badge -->
      <g transform="translate(21, 12)">
        <rect x="0" y="0" width="13" height="16" rx="1.5" fill="#061A14" stroke="#34D399" stroke-width="1.2"/>
        <line x1="2.5" y1="4" x2="10.5" y2="4" stroke="#34D399" stroke-width="1" stroke-linecap="round"/>
        <line x1="2.5" y1="7.5" x2="8.5" y2="7.5" stroke="#6EE7B7" stroke-width="1" stroke-linecap="round"/>
        <circle class="shield-badge-beat" cx="11.5" cy="12.5" r="3.2" fill="#34D399" filter="url(#glowGreen)"/>
        <path d="M10 12.5 L11.2 13.6 L13 11.5" stroke="#022C22" stroke-width="1.1" stroke-linecap="round" stroke-linejoin="round"/>
      </g>

      <!-- Perspective Ground Cadastre Plots -->
      <g>
        <path d="M9 33 L24 30 L23.5 40.5 L8 39.5 Z" fill="#064E3B" opacity="0.95"/>
        <path d="M26 30 L41 33 L42 39.5 L26.5 40.5 Z" fill="#047857" opacity="0.95"/>
        <path d="M8 39.5 L23.5 40.5 L22.5 47.5 L11 44 Z" fill="url(#neonGreen)"/>
        <path d="M26.5 40.5 L42 39.5 L39 44 L27.5 47.5 Z" fill="#10B981"/>
      </g>
    </g>

    <!-- Word GUARD -->
    <text class="word-guard" x="690" y="60" text-anchor="start" font-size="24" font-weight="950" letter-spacing="5" fill="#22D3EE" stroke="#22D3EE" stroke-width="1.2">GUARD</text>

    <!-- Cyber Platform Wings -->
    <g transform="translate(500, 78)">
      <line x1="0" y1="0" x2="120" y2="0" stroke="url(#neonGreen)" stroke-width="1.6"/>
      <g transform="translate(140, -6)">
        <path d="M0 0 L5 2.5 V6 C5 8.5 0 10 0 10 C0 10 -5 8.5 -5 6 V2.5 L0 0 Z" stroke="#22D3EE" stroke-width="1.3" fill="#0A111E"/>
        <circle cx="0" cy="4" r="1.3" fill="#22D3EE"/>
      </g>
      <line x1="160" y1="0" x2="280" y2="0" stroke="url(#neonCyan)" stroke-width="1.6"/>
    </g>

    <!-- Subtitle -->
    <text x="640" y="94" text-anchor="middle" font-size="7.5" font-weight="800" letter-spacing="4.5" fill="#94A3B8">SECURE DIGITAL CADASTRE</text>
  </g>
</svg>"""

    targets = [
        os.path.join(repo_root, "landguard_preloader_animated.svg"),
        os.path.join(repo_root, "docs", "landguard_preloader_animated.svg"),
        os.path.join(repo_root, "src", "landguard_web", "static", "images", "landguard_preloader_animated.svg"),
        r"C:\Users\ASHIK_CSE\.gemini\antigravity\brain\71207a76-ca66-4b1d-9dab-cb77172733e7\landguard_preloader_animated.svg"
    ]

    for t in targets:
        os.makedirs(os.path.dirname(t), exist_ok=True)
        with open(t, "w", encoding="utf-8") as f:
            f.write(svg_content)
        print(f"[3/4] Successfully generated SVG: {t} ({len(svg_content):,} bytes)")

    print("[4/4] Completed successfully!")

if __name__ == "__main__":
    generate_perfectly_aligned_svg()
