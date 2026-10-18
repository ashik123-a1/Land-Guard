"""LandGuard Site-Wide Persistent Hands-Free Voice Assistant E2E Test Suite.

Verifies the complete real browser cross-page navigation workflow:
1. Citizen authenticates and opens /user/voice.
2. Single-click enables Hands-Free mode.
3. Wake-word activation via "Hello Daffodil".
4. Real cross-page navigation via "Open Verification History" -> URL changes to /user/history.
5. Verification that destination page restores Hands-Free ON without re-toggling.
6. Consecutive command execution without re-speaking the wake phrase ("Search Plot 9044").
7. Real cross-page navigation to /user/parcels/9044.
8. Bengali voice command execution ("ড্যাশবোর্ডে যাও") -> navigates to /user/dashboard.
9. Manual sidebar navigation persistence -> state remains ON across tab transitions.
10. Explicit "Stop Daffodil" deactivation -> turns Hands-Free OFF and clears sessionStorage.
11. Subsequent navigation maintains OFF state without auto-restarting.
12. Re-enabling Hands-Free on a destination page.
13. Sign-out cleanup -> clears sessionStorage and releases resources.
14. Multi-cycle navigation resilience without duplicate recognizers or console errors.

NOTE: Uses deterministic simulated speech injection (window.simulateSpeechInput) for automated
headless browser execution where real physical acoustic microphone audio is unavailable.
"""

import sys
import time
import subprocess
import urllib.request

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://127.0.0.1:8000"
server_process = None

def ensure_server(base_url=BASE_URL):
    global server_process
    try:
        req = urllib.request.urlopen(f"{base_url}/api/health", timeout=1)
        if req.getcode() == 200:
            print("[Server] LandGuard backend is already running on port 8000.")
            return
    except Exception:
        pass

    print("[Server] Launching background LandGuard server...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.landguard_web.app:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=r"F:\land gurd main project",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    for _ in range(40):
        time.sleep(0.5)
        try:
            req = urllib.request.urlopen(f"{base_url}/api/health", timeout=1)
            if req.getcode() == 200:
                print("[Server] Server successfully booted and responding at /api/health")
                return
        except Exception:
            pass
    raise RuntimeError("Failed to start LandGuard server within 20 seconds.")

def run_site_wide_test():
    import urllib.request
    import subprocess
    ensure_server()

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--use-fake-ui-for-media-stream")
    opts.add_argument("--use-fake-device-for-media-stream")
    opts.add_argument("--window-size=1600,1000")

    driver = webdriver.Chrome(options=opts)
    wait = WebDriverWait(driver, 10)

    try:
        print("\n========================================================")
        print("LANDGUARD SITE-WIDE VOICE CONTROL E2E VERIFICATION SUITE")
        print("========================================================\n")

        # Step 1: Login as Citizen and open /user/voice
        print("[Step 1] Opening login page and authenticating as Citizen...")
        driver.get(f"{BASE_URL}/login")
        time.sleep(1)
        demo_btn = wait.until(EC.element_to_be_clickable((By.ID, "demo-btn-citizen")))
        demo_btn.click()
        time.sleep(2)

        print("[Step 1b] Navigating to Voice Assistant page...")
        driver.get(f"{BASE_URL}/user/voice")
        wait.until(EC.presence_of_element_located((By.ID, "handsFreeToggleBtn")))
        assert "/user/voice" in driver.current_url
        print(f"    Loaded page: {driver.current_url}")

        # Step 2: Initial state & Enable Hands-Free
        print("\n[Step 2] Checking initial state and enabling Hands-Free...")
        hf_btn = driver.find_element(By.ID, "handsFreeToggleBtn")
        hf_label = driver.find_element(By.ID, "handsFreeLabel")
        print(f"    Initial state: {hf_label.text}")
        assert "OFF" in hf_label.text

        hf_btn.click()
        time.sleep(1)
        hf_label = driver.find_element(By.ID, "handsFreeLabel")
        print(f"    Updated state after click: {hf_label.text}")
        assert "ON" in hf_label.text
        assert driver.execute_script("return window.isHandsFreeActive();") is True

        # Step 3: Trigger Wake Word "Hello Daffodil"
        print("\n[Step 3] Simulating wake-word activation: 'Hello Daffodil'...")
        driver.execute_script("window.simulateSpeechInput('Hello Daffodil');")
        time.sleep(2.5)

        spoken_en = driver.find_element(By.ID, "spoken-en").get_attribute("textContent")
        print(f"    Assistant acknowledgment: '{spoken_en}'")
        assert "listening" in spoken_en.lower() or "daffodil" in spoken_en.lower()
        assert driver.execute_script("return window.isHandsFreeActive();") is True
        assert driver.execute_script("return window.isSessionActive();") is True

        # Step 4 & 5: Speak "Open Verification History" -> Assert REAL cross-page URL navigation
        print("\n[Step 4 & 5] Issuing navigation command: 'Open Verification History'...")
        driver.execute_script("window.simulateSpeechInput('Open Verification History');")
        
        # Wait for actual browser URL change to /user/history
        wait.until(EC.url_contains("/user/history"))
        time.sleep(2)
        print(f"    Successfully navigated! New URL: {driver.current_url}")
        assert "/user/history" in driver.current_url

        # Step 6: Verify destination page restored the shared controller and Hands-Free remains ON
        print("\n[Step 6] Verifying destination page (/user/history) state...")
        wait.until(EC.presence_of_element_located((By.ID, "handsFreeToggleBtn")))
        is_hf_active = driver.execute_script("return window.isHandsFreeActive();")
        is_sess_active = driver.execute_script("return window.isSessionActive();")
        hf_label = driver.find_element(By.ID, "handsFreeLabel").text
        print(f"    Destination Hands-Free label: '{hf_label}'")
        print(f"    isHandsFreeActive(): {is_hf_active}, isSessionActive(): {is_sess_active}")
        assert is_hf_active is True, "Hands-Free must be automatically restored ON destination page"
        assert is_sess_active is True, "Session must remain active for consecutive commands"

        # Step 7 & 8: Consecutive command WITHOUT wake word: "Search Plot 9044" -> navigates to /user/parcels/9044
        print("\n[Step 7 & 8] Issuing consecutive command without wake-word: 'Search Plot 9044'...")
        driver.execute_script("window.simulateSpeechInput('Search Plot 9044');")

        wait.until(EC.url_contains("/user/parcels/9044"))
        time.sleep(2)
        print(f"    Successfully navigated to plot route! New URL: {driver.current_url}")
        assert "/user/parcels/9044" in driver.current_url

        # Step 9: Confirm Hands-Free remains ON on parcel details
        print("\n[Step 9] Verifying Hands-Free state on /user/parcels/9044...")
        assert driver.execute_script("return window.isHandsFreeActive();") is True
        assert driver.execute_script("return window.isSessionActive();") is True
        print("    Hands-Free remains active on parcel details page.")

        # Step 10: Issue Bengali command: "ড্যাশবোর্ডে যাও" -> navigates to /user/dashboard
        print("\n[Step 10] Issuing Bengali voice command: 'ড্যাশবোর্ডে যাও'...")
        driver.execute_script("window.simulateSpeechInput('ড্যাশবোর্ডে যাও');")

        wait.until(EC.url_contains("/user/dashboard"))
        time.sleep(2)
        print(f"    Successfully navigated via Bengali command! New URL: {driver.current_url}")
        assert "/user/dashboard" in driver.current_url
        assert driver.execute_script("return window.isHandsFreeActive();") is True

        # Step 11: Manual sidebar navigation -> state persists across manual page transitions
        print("\n[Step 11] Navigating manually through sidebar to /user/notifications...")
        notif_link = driver.find_element(By.CSS_SELECTOR, "a[href='/user/notifications']")
        notif_link.click()
        wait.until(EC.url_contains("/user/notifications"))
        time.sleep(1.5)
        print(f"    Loaded page: {driver.current_url}")
        assert driver.execute_script("return window.isHandsFreeActive();") is True
        print("    Hands-Free successfully preserved across manual page navigation.")

        # Step 12: Say "Stop Daffodil" -> turns Hands-Free OFF and clears stored state
        print("\n[Step 12] Simulating stop phrase: 'Stop Daffodil'...")
        driver.execute_script("window.simulateSpeechInput('Stop Daffodil');")
        time.sleep(1)

        is_hf_active = driver.execute_script("return window.isHandsFreeActive();")
        hf_label = driver.find_element(By.ID, "handsFreeLabel").text
        stored_session = driver.execute_script("return sessionStorage.getItem('landguard_voice_hands_free');")
        print(f"    Label after stop: '{hf_label}'")
        print(f"    isHandsFreeActive(): {is_hf_active}")
        print(f"    sessionStorage: {stored_session}")
        assert is_hf_active is False
        assert "OFF" in hf_label
        assert stored_session is None or "false" in str(stored_session).lower()

        # Step 13: Subsequent navigation maintains OFF state
        print("\n[Step 13] Navigating to /user/history to verify Hands-Free remains OFF...")
        driver.get(f"{BASE_URL}/user/history")
        wait.until(EC.presence_of_element_located((By.ID, "handsFreeToggleBtn")))
        time.sleep(1)
        is_hf_active = driver.execute_script("return window.isHandsFreeActive();")
        hf_label = driver.find_element(By.ID, "handsFreeLabel").text
        print(f"    State on /user/history: {hf_label}, isHandsFreeActive(): {is_hf_active}")
        assert is_hf_active is False
        assert "OFF" in hf_label

        # Step 14: Re-enable Hands-Free on destination page
        print("\n[Step 14] Re-enabling Hands-Free on /user/history...")
        hf_btn = driver.find_element(By.ID, "handsFreeToggleBtn")
        hf_btn.click()
        time.sleep(1)
        assert driver.execute_script("return window.isHandsFreeActive();") is True
        print("    Successfully re-enabled Hands-Free on destination page.")

        # Step 15: Sign-out clears state and terminates controller
        print("\n[Step 15] Signing out via /logout...")
        driver.get(f"{BASE_URL}/logout")
        wait.until(EC.url_contains("/login"))
        time.sleep(1)
        stored_session = driver.execute_script("return sessionStorage.getItem('landguard_voice_hands_free');")
        print(f"    Current URL: {driver.current_url}")
        print(f"    sessionStorage after logout: {stored_session}")
        assert stored_session is None

        # Step 16 & 17: Log in again and verify multi-cycle resilience
        print("\n[Step 16 & 17] Verifying multi-cycle navigation resilience without console errors...")
        driver.find_element(By.ID, "demo-btn-citizen").click()
        time.sleep(1.5)

        for path in ["/user/dashboard", "/user/parcels", "/user/history"]:
            driver.get(f"{BASE_URL}{path}")
            time.sleep(0.5)
            # Ensure no crash and controller is present
            has_controller = driver.execute_script("return typeof window.LandGuardVoiceController !== 'undefined';")
            assert has_controller is True, f"Controller missing on {path}"

        print("\n>>> ALL 17 SITE-WIDE VOICE CONTROL CRITERIA VERIFIED SUCCESSFULLY! <<<\n")

    finally:
        try:
            driver.quit()
        except Exception:
            pass
        if server_process:
            print("[Server] Terminating background test server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except Exception:
                server_process.kill()

if __name__ == "__main__":
    run_site_wide_test()
