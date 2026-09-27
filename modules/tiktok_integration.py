import os
import asyncio
from playwright.async_api import async_playwright

# Directory to store the browser session (cookies, local storage)
SESSION_DIR = os.path.join(os.getcwd(), "browser_sessions", "tiktok")

async def login_to_tiktok():
    """
    Opens a browser window and waits for the user to log in manually.
    Saves the session to SESSION_DIR.
    """
    import subprocess
    try:
        subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/IM", "chromium.exe", "/T"], capture_output=True)
    except Exception:
        pass

    async with async_playwright() as p:
        try:
            # Ensure SESSION_DIR is absolute and clean
            abs_session_dir = os.path.abspath(SESSION_DIR)
            
            # Use a separate folder for the actual profile to avoid lock conflicts if possible, 
            # but Playwright's launch_persistent_context expects the root of the profile.
            # We ensure the path is trimmed of trailing slashes.
            abs_session_dir = abs_session_dir.rstrip('\\').rstrip('/')

            browser = await p.chromium.launch_persistent_context(
                user_data_dir=abs_session_dir,
                headless=False,
                args=["--start-maximized", "--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
                no_viewport=True,
            )
            # Playwright launch_persistent_context usually opens one page by default
            pages = browser.pages
            page = pages[0] if pages else await browser.new_page()
            try:
                await page.goto("https://www.tiktok.com/login", wait_until="domcontentloaded", timeout=60000)
            except Exception as e:
                print(f"[TIKTOK] Initial page load warning: {e}")
                # We continue anyway to let the user try to interact
            
            print("[TIKTOK] Browser opened. Please log in to your account.")
            print("[TIKTOK] Once you are logged in and see your feed, close the browser window.")
            
            while True:
                if not browser or len(browser.pages) == 0:
                    break
                await asyncio.sleep(1)
            
            await browser.close()
            print(f"[TIKTOK] Session saved to {abs_session_dir}. You are now logged in for JARVIS.")
        except Exception as e:
            print(f"[TIKTOK] Error during login: {e}")
            print("[TIKTOK] Suggestion: Ensure no other Chrome/Chromium instances are using this profile.")

async def get_tiktok_analytics(username):
    """
    Opens a headless browser, loads the session, and scrapes analytics.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            headless=True
        )
        page = await browser.new_page()
        url = f"https://www.tiktok.com/@{username}/analytics"
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Extract text from the body and clean up whitespace to reduce "rubbish" for the LLM
            text_content = await page.evaluate("""
                () => {
                    document.querySelectorAll('script, style, noscript, iframe').forEach(el => el.remove());
                    return document.body.innerText;
                }
            """)
            cleaned_text = "\\n".join([line.strip() for line in text_content.splitlines() if line.strip()])
            return {"raw_content": cleaned_text, "status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            await browser.close()

def sync_login():
    """Synchronous wrapper for login_to_tiktok. Returns True if successful."""
    try:
        asyncio.run(login_to_tiktok())
        return True
    except Exception as e:
        print(f"[TIKTOK] Sync login failed: {e}")
        return False

def sync_get_analytics(username):
    """Synchronous wrapper for get_tiktok_analytics."""
    return asyncio.run(get_tiktok_analytics(username))

__all__ = ["sync_login", "sync_get_analytics"]
