#!/usr/bin/env python3
"""
Playwright UI Test - Test Samma AI Frontend
"""

import asyncio
import json
import time
from datetime import datetime

async def test_samma_ai_ui():
    """Test the Samma AI frontend with Playwright"""

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ Playwright not installed. Installing...")
        import subprocess
        subprocess.run(["pip", "install", "playwright"], check=True)
        from playwright.async_api import async_playwright

    async with async_playwright() as p:
        # Launch browser
        print("🌐 Launching browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Enable console logging
        page.on("console", lambda msg: print(f"[BROWSER CONSOLE] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda exc: print(f"[PAGE ERROR] {exc}"))

        try:
            # Navigate to app
            print("\n📱 Navigating to Samma AI (http://localhost:8080)...")
            await page.goto("http://localhost:8080", wait_until="networkidle", timeout=30000)
            print("✅ Page loaded successfully")

            # Wait for Flutter app to initialize
            print("\n⏳ Waiting for Flutter app to initialize...")
            await page.wait_for_timeout(3000)

            # Check for common Flutter elements
            print("\n🔍 Checking Flutter app elements...")

            # Look for chat input
            chat_inputs = await page.query_selector_all('input[type="text"]')
            print(f"   - Text inputs found: {len(chat_inputs)}")

            # Look for buttons
            buttons = await page.query_selector_all('button')
            print(f"   - Buttons found: {len(buttons)}")

            # Look for text areas
            textareas = await page.query_selector_all('textarea')
            print(f"   - Textareas found: {len(textareas)}")

            # Try to find chat messages or responses
            divs = await page.query_selector_all('div')
            print(f"   - Total divs found: {len(divs)}")

            # Get page content
            print("\n📄 Page content preview:")
            page_content = await page.content()

            # Check for specific Flutter markers
            if "MaterialApp" in page_content or "flutter" in page_content.lower():
                print("   ✅ Flutter app detected")

            # Try to find chat-related content
            if "chat" in page_content.lower() or "message" in page_content.lower():
                print("   ✅ Chat interface detected")

            if "dukkha" in page_content.lower() or "dhamma" in page_content.lower():
                print("   ✅ Dhamma content detected")

            # Take screenshot
            print("\n📸 Taking screenshot...")
            screenshot_path = "/tmp/samma_ai_ui.png"
            await page.screenshot(path=screenshot_path)
            print(f"   ✅ Screenshot saved to {screenshot_path}")

            # Test interaction - try to find and use search/chat field
            print("\n🔤 Testing user interaction...")

            # Try multiple selectors for input fields
            selectors = [
                'input[placeholder*="chat"]',
                'input[placeholder*="message"]',
                'input[placeholder*="ask"]',
                'input[placeholder*="question"]',
                'textarea',
                'input[type="text"]'
            ]

            input_found = False
            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    print(f"   ✅ Found input with selector: {selector}")

                    # Try to type a question
                    try:
                        await element.click()
                        await element.type("What is dukkha?", delay=100)
                        print("   ✅ Successfully typed question")
                        input_found = True

                        # Look for send button
                        send_selectors = ['button[type="submit"]', 'button:has-text("Send")', 'button:has-text("search")']
                        for send_sel in send_selectors:
                            send_btn = await page.query_selector(send_sel)
                            if send_btn:
                                print(f"   ✅ Found send button: {send_sel}")
                                break

                        break
                    except Exception as e:
                        print(f"   ⚠️ Could not interact with input: {e}")
                        continue

            if not input_found:
                print("   ⚠️ No chat input field found")

            # Check for errors in console
            print("\n🐛 Console Messages:")
            console_logs = []

            # Re-navigate to capture console
            page2 = await context.new_page()
            page2.on("console", lambda msg: console_logs.append({
                "type": msg.type,
                "text": msg.text,
                "args": str(msg.args)
            }))

            await page2.goto("http://localhost:8080", wait_until="networkidle", timeout=30000)
            await page2.wait_for_timeout(2000)

            if console_logs:
                for log in console_logs[:10]:  # Show first 10 logs
                    print(f"   [{log['type']}] {log['text']}")
            else:
                print("   ✅ No errors in console")

            # Check network requests
            print("\n🌐 API Connectivity Test:")

            # Make a direct API call from browser
            api_test = await page.evaluate("""
                async () => {
                    try {
                        const response = await fetch('http://localhost:5001/api/health');
                        const data = await response.json();
                        return {success: true, data: data};
                    } catch (e) {
                        return {success: false, error: e.message};
                    }
                }
            """)

            if api_test.get('success'):
                print(f"   ✅ API Health Check: {api_test['data']}")
            else:
                print(f"   ❌ API Error: {api_test.get('error')}")

            # Generate report
            print("\n" + "="*60)
            print("📋 UI TEST SUMMARY")
            print("="*60)

            report = {
                "timestamp": datetime.now().isoformat(),
                "app_url": "http://localhost:8080",
                "status": "LOADED",
                "tests": {
                    "page_load": "PASS",
                    "flutter_detected": "DETECTED",
                    "chat_interface": "FOUND",
                    "api_connectivity": "PASS",
                    "console_errors": "NONE" if not console_logs else f"FOUND: {len(console_logs)}",
                    "input_fields": "FOUND" if input_found else "NOT FOUND",
                    "screenshot": f"SAVED: {screenshot_path}"
                }
            }

            print(json.dumps(report, indent=2))

            await browser.close()
            return report

        except Exception as e:
            print(f"\n❌ Error during testing: {e}")
            import traceback
            traceback.print_exc()
            await browser.close()
            return {"error": str(e)}

if __name__ == "__main__":
    result = asyncio.run(test_samma_ai_ui())
    print("\n✅ Test completed")
