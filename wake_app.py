import os
from playwright.sync_api import sync_playwright

url = os.environ["STREAMLIT_APP_URL"]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(url, wait_until="networkidle")

    try:
        page.get_by_text("Yes, get this app back up").click(timeout=5000)
        page.wait_for_load_state("networkidle")
    except:
        pass

    browser.close()
