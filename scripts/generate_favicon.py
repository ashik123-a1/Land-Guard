import os
import subprocess
import shutil
from PIL import Image

def generate_favicons():
    svg_path = os.path.abspath("src/landguard_web/static/images/favicon.svg")
    png_path = os.path.abspath("src/landguard_web/static/images/favicon.png")
    ico_path = os.path.abspath("src/landguard_web/static/images/favicon.ico")

    # Locate modern Chromium browser
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
    browser_exe = None
    for c in chrome_candidates:
        if c and os.path.isfile(c):
            browser_exe = c
            break

    if not browser_exe:
        print("[Favicon Generator] No browser found, drawing raster fallback with Pillow.")
        im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        im.save(png_path)
        im.save(ico_path)
        return

    svg_uri = svg_path.replace("\\", "/")
    html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{
    background: transparent !important;
    width: 256px;
    height: 256px;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }}
  img {{
    width: 240px;
    height: 240px;
    object-fit: contain;
  }}
</style>
</head>
<body>
  <img src="file:///{svg_uri}" alt="Favicon">
</body>
</html>
"""
    temp_html = os.path.abspath("temp_favicon.html")
    temp_shot = os.path.abspath("temp_favicon_shot.png")
    with open(temp_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    try:
        cmd = [
            browser_exe,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--window-size=256,256",
            "--default-background-color=00000000",
            f"--screenshot={temp_shot}",
            temp_html,
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if res.returncode == 0 and os.path.isfile(temp_shot):
            im = Image.open(temp_shot).convert("RGBA")
            # Auto-crop transparent borders if any
            bbox = im.getbbox()
            if bbox:
                # Add slight padding
                w, h = im.size
                cropped = im.crop(bbox)
                max_dim = max(cropped.width, cropped.height)
                square_im = Image.new("RGBA", (max_dim + 16, max_dim + 16), (0, 0, 0, 0))
                paste_x = (square_im.width - cropped.width) // 2
                paste_y = (square_im.height - cropped.height) // 2
                square_im.paste(cropped, (paste_x, paste_y), cropped)
                im = square_im

            # Save PNG versions
            im_64 = im.resize((64, 64), Image.Resampling.LANCZOS)
            im_64.save(png_path, format="PNG")
            
            # Save ICO with multiple standard sizes
            im_64.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
            print(f"[Favicon Generator] Successfully created:\n  - {png_path}\n  - {ico_path}")
        else:
            print(f"[Favicon Generator] Headless capture failed: {res.stderr}")
    finally:
        if os.path.exists(temp_html):
            os.remove(temp_html)
        if os.path.exists(temp_shot):
            os.remove(temp_shot)

if __name__ == "__main__":
    generate_favicons()
