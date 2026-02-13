import re
from playwright.sync_api import Page, expect, sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    page.goto("http://localhost:8080/")

    # Give it a moment to load something, just in case
    page.wait_for_timeout(5000)

    # Print the page content to a file for analysis
    with open("page_content.html", "w") as f:
        f.write(page.content())
    print("Page content saved to page_content.html")

    context.close()
    browser.close()

with sync_playwright() as playwright:
    run(playwright)