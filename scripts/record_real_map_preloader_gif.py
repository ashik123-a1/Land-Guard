#!/usr/bin/env python3
"""Records the authentic LandGuard preloader with real ArcGIS dark map tiles into an animated GIF."""

import os
import time
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image


def record_real_map_gif():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    out_gif = os.path.join(repo_root, "landguard_preloader_animated.gif")
    docs_gif = os.path.join(repo_root, "docs", "landguard_preloader_animated.gif")
    static_gif = os.path.join(repo_root, "src", "landguard_web", "static", "images", "landguard_preloader_animated.gif")
    artifact_gif = r"C:\Users\ASHIK_CSE\.gemini\antigravity\brain\71207a76-ca66-4b1d-9dab-cb77172733e7\landguard_preloader_animated.gif"

    temp_dir = os.path.join(repo_root, "temp_real_frames")
    os.makedirs(temp_dir, exist_ok=True)

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,720")

    print("[Recorder] Launching headless browser...")
    driver = webdriver.Chrome(options=opts)
    driver.get("http://127.0.0.1:8000/")

    # Pre-warm: wait for ArcGIS map tiles to fully download into browser cache
    print("[Recorder] Pre-warming real map tiles (waiting 4.5s)...")
    time.sleep(4.5)

    # Put preloader in manual recording mode & hide skip button
    driver.execute_script("""
        window.DISABLE_PRELOADER_DISMISS = true;
        window.RECORDING_MODE = true;
        const skipBtn = document.querySelector('.absolute.top-6.right-8');
        if (skipBtn) skipBtn.style.display = 'none';
    """)

    # Timestamps spanning all 4 phases:
    # Phase 1: Border line tracing (10 frames)
    # Phase 2: Divisions ignite (4 frames)
    # Phase 3: Real ArcGIS dark map tiles fade in (7 frames)
    # Phase 4: Full map showcase (3 frames)
    timestamps = [
        150, 450, 800, 1150, 1500, 1850, 2200, 2500, 2700, 2800,
        2950, 3150, 3350, 3550,
        3750, 3950, 4150, 4350, 4550, 4700, 4800,
        4900, 5000, 5100
    ]

    frames = []
    print(f"[Recorder] Capturing {len(timestamps)} frames with real map tiles...")

    for idx, t in enumerate(timestamps):
        driver.execute_script(f"window.renderPreloaderFrame({t});")
        time.sleep(0.08)  # ensure DOM redraws
        shot_path = os.path.join(temp_dir, f"frame_{idx:02d}.png")
        driver.save_screenshot(shot_path)

        im = Image.open(shot_path)
        # Crop or resize cleanly to 800x450 (16:9)
        im_opt = im.resize((800, 450), Image.Resampling.LANCZOS)
        frames.append(im_opt)
        print(f"  - Frame {idx+1}/{len(timestamps)} at t={t}ms captured.")

    driver.quit()

    if frames:
        # Normal frames 130ms, final frame with full map holds for 1600ms
        durations = [130] * (len(frames) - 1) + [1600]

        frames[0].save(
            out_gif,
            save_all=True,
            append_images=frames[1:],
            optimize=True,
            duration=durations,
            loop=0
        )
        shutil.copy2(out_gif, docs_gif)
        shutil.copy2(out_gif, static_gif)
        shutil.copy2(out_gif, artifact_gif)
        print(f"[Recorder] Successfully generated real map animated GIF: {out_gif} ({os.path.getsize(out_gif):,} bytes)")

    shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    record_real_map_gif()
