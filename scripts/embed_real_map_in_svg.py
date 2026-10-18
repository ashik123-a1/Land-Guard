import os
import io
import base64
import shutil
from PIL import Image

def update_svg():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    svg_path = os.path.join(repo_root, "landguard_preloader_animated.svg")
    test_img = os.path.join(repo_root, "test_render_frame_4400.png")

    if not os.path.isfile(test_img):
        print("test_render_frame_4400.png not found, skipping SVG update.")
        return

    with open(svg_path, "r", encoding="utf-8") as f:
        svg_text = f.read()

    im = Image.open(test_img).resize((1000, 720), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    im.convert("RGB").save(buf, format="JPEG", quality=82)
    b64_map = base64.b64encode(buf.getvalue()).decode("ascii")

    style_add = """
    /* Real Geographic Map Tiles Fade-In (Phase 3) */
    .real-map-tiles {
      animation: realMapFade 6s ease-in-out infinite;
    }
    @keyframes realMapFade {
      0%, 46% { opacity: 0; }
      58%, 88% { opacity: 0.90; }
      100% { opacity: 0; }
    }
"""

    if ".real-map-tiles" not in svg_text:
        svg_text = svg_text.replace("    /* 3. Bangladesh Interior Fill Illumination */", style_add + "\n    /* 3. Bangladesh Interior Fill Illumination */")

    img_tag = f"""  <!-- Real Geographic Dark Map Tiles (Phase 3) -->
  <image class="real-map-tiles" href="data:image/jpeg;base64,{b64_map}" x="0" y="0" width="1000" height="720" preserveAspectRatio="xMidYMid slice"/>\n"""

    if 'class="real-map-tiles"' not in svg_text:
        svg_text = svg_text.replace('  <g id="preloader-map-body">', '  <g id="preloader-map-body">\n' + img_tag)

    targets = [
        svg_path,
        os.path.join(repo_root, "docs", "landguard_preloader_animated.svg"),
        os.path.join(repo_root, "src", "landguard_web", "static", "images", "landguard_preloader_animated.svg"),
    ]
    for t in targets:
        with open(t, "w", encoding="utf-8") as f:
            f.write(svg_text)
        print(f"[SVG Updater] Updated: {t} ({len(svg_text):,} bytes)")

    # Clean up temp test files
    for tmp in ["test_phase3_map.png", "test_phase4_map.png", "test_render_frame_4400.png"]:
        p = os.path.join(repo_root, tmp)
        if os.path.exists(p):
            os.remove(p)

if __name__ == "__main__":
    update_svg()
