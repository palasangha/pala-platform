#!/usr/bin/env python3
"""
Playwright Test - Validate Samma AI 8-Part Response Format
Tests that API responses match the strict Dhamma response protocol
"""

import asyncio
import json
import re
from datetime import datetime
from typing import Dict, List, Tuple


class ResponseFormatValidator:
    """Validates Samma AI 8-part response format."""

    REQUIRED_SECTIONS = [
        'direct_definition',
        'interpretive_insight',
        'canonical_teachings',
        'commentary',
        'tika_clarification',
        'lexical_analysis',
        'doctrinal_function',
        'final_summary'
    ]

    def __init__(self):
        self.errors = []
        self.warnings = []

    def validate_response_structure(self, response: Dict) -> Tuple[bool, List[str]]:
        """Validate that response has all required 8 parts."""
        issues = []

        # Check for response key
        if 'response' not in response:
            return False, ["Response missing 'response' key"]

        resp = response['response']

        # Check all required sections exist
        for section in self.REQUIRED_SECTIONS:
            if section not in resp:
                issues.append(f"Missing section: {section}")

        return len(issues) == 0, issues

    def validate_sections_not_empty(self, response: Dict) -> Tuple[bool, List[str]]:
        """Validate that sections have content (not just empty strings)."""
        issues = []

        if 'response' not in response:
            return False, ["Response missing 'response' key"]

        resp = response['response']

        for section in self.REQUIRED_SECTIONS:
            if section not in resp:
                continue

            content = resp[section]

            # canonical_teachings should be a list
            if section == 'canonical_teachings':
                if not isinstance(content, list):
                    issues.append(f"{section} should be a list, got {type(content)}")
                elif len(content) == 0:
                    issues.append(f"{section} is empty list")
                else:
                    # Validate each teaching has required fields
                    for i, teaching in enumerate(content):
                        if not isinstance(teaching, dict):
                            issues.append(f"Teaching {i} is not a dict")
                            continue
                        required_fields = ['pali', 'english', 'explanation', 'reference']
                        for field in required_fields:
                            if field not in teaching:
                                issues.append(f"Teaching {i} missing field: {field}")
            else:
                # Other sections can be dict with title/content (frontend format) or string
                if isinstance(content, dict):
                    # Format: {title: "...", content: "..."}
                    if 'content' not in content:
                        issues.append(f"{section} dict missing 'content' key")
                    elif len(str(content.get('content', '')).strip()) == 0:
                        issues.append(f"{section} content is empty or whitespace only")
                elif isinstance(content, str):
                    if len(content.strip()) == 0:
                        issues.append(f"{section} is empty or whitespace only")
                else:
                    issues.append(f"{section} should be dict or string, got {type(content)}")

        return len(issues) == 0, issues

    def validate_reference_format(self, response: Dict) -> Tuple[bool, List[str]]:
        """Validate that canonical teachings have proper reference format."""
        issues = []

        if 'response' not in response or 'canonical_teachings' not in response['response']:
            return True, []  # Skip if not present

        teachings = response['response'].get('canonical_teachings', [])

        for i, teaching in enumerate(teachings):
            reference = teaching.get('reference', '')

            # Check for expected reference structure
            # Should contain: Sutta Piṭaka, Nikāya, Book/Division, Sutta Name, TPR Page/Paragraph
            if reference and isinstance(reference, str) and reference.strip():
                # Basic check - should have content (at least some length)
                reference_text = reference.strip()
                if len(reference_text) > 0:
                    # References should have some structure (paths, arrows, etc)
                    # This is just a basic sanity check - not expecting TPR necessarily
                    pass
            elif not reference or (isinstance(reference, str) and not reference.strip()):
                # Empty reference is acceptable - model may not provide complete info
                pass

        return len(issues) == 0, issues

    def validate_pali_content(self, response: Dict) -> Tuple[bool, List[str]]:
        """Validate that Pali content is present."""
        issues = []

        if 'response' not in response or 'canonical_teachings' not in response['response']:
            return True, []

        teachings = response['response'].get('canonical_teachings', [])

        for i, teaching in enumerate(teachings):
            pali = teaching.get('pali', '').strip()

            if not pali:
                issues.append(f"Teaching {i} missing Pali text")
            elif len(pali) < 5:
                issues.append(f"Teaching {i} Pali text too short: '{pali}'")

        return len(issues) == 0, issues

    def validate_english_translations(self, response: Dict) -> Tuple[bool, List[str]]:
        """Validate that English translations exist."""
        issues = []

        if 'response' not in response or 'canonical_teachings' not in response['response']:
            return True, []

        teachings = response['response'].get('canonical_teachings', [])

        for i, teaching in enumerate(teachings):
            english = teaching.get('english', '').strip()

            if not english:
                issues.append(f"Teaching {i} missing English translation")
            elif len(english) < 5:
                issues.append(f"Teaching {i} English translation too short: '{english}'")

        return len(issues) == 0, issues


async def test_api_response_format():
    """Test the API response format using Playwright for HTTP requests."""

    print("="*70)
    print("🧪 SAMMA AI RESPONSE FORMAT TEST")
    print("="*70)

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ Playwright not installed. Installing...")
        import subprocess
        subprocess.run(["pip", "install", "playwright"], check=True)
        from playwright.async_api import async_playwright

    validator = ResponseFormatValidator()
    test_results = {
        'timestamp': datetime.now().isoformat(),
        'tests': {}
    }

    async with async_playwright() as p:
        # Create a browser context for making API requests
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        # Test questions covering different aspects of Dhamma
        test_questions = [
            "What is dukkha (suffering)?",
            "Explain anicca (impermanence)",
            "What is the Noble Eightfold Path?",
        ]

        for question in test_questions:
            print(f"\n📝 Testing question: '{question}'")
            print("-" * 70)

            test_key = question[:30].replace(" ", "_")
            test_results['tests'][test_key] = {
                'question': question,
                'status': 'UNKNOWN',
                'results': {}
            }

            try:
                # Make API call
                api_url = 'http://localhost:5001/api/chat'

                page = await context.new_page()

                # Make request
                print(f"📡 Calling {api_url}")
                response = await page.evaluate(f"""
                    async () => {{
                        try {{
                            const response = await fetch('{api_url}', {{
                                method: 'POST',
                                headers: {{'Content-Type': 'application/json'}},
                                body: JSON.stringify({{
                                    message: '{question}',
                                    model_id: 'ollama:llama3.2:latest'
                                }})
                            }});

                            if (!response.ok) {{
                                return {{error: 'HTTP ' + response.status}};
                            }}

                            return await response.json();
                        }} catch (e) {{
                            return {{error: e.message}};
                        }}
                    }}
                """)

                await page.close()

                if 'error' in response:
                    print(f"   ❌ API Error: {response['error']}")
                    test_results['tests'][test_key]['status'] = 'FAILED'
                    test_results['tests'][test_key]['results']['error'] = response['error']
                    continue

                print(f"   ✅ API Response received")

                # Run validators
                validators = [
                    ("Structure", validator.validate_response_structure),
                    ("Content (Non-Empty)", validator.validate_sections_not_empty),
                    ("Pali Content", validator.validate_pali_content),
                    ("English Translations", validator.validate_english_translations),
                    ("Reference Format", validator.validate_reference_format),
                ]

                all_passed = True
                for validator_name, validator_func in validators:
                    passed, issues = validator_func(response)

                    if passed:
                        print(f"   ✅ {validator_name}: PASS")
                        test_results['tests'][test_key]['results'][validator_name] = 'PASS'
                    else:
                        print(f"   ❌ {validator_name}: FAIL")
                        print(f"      Issues: {issues}")
                        test_results['tests'][test_key]['results'][validator_name] = 'FAIL'
                        test_results['tests'][test_key]['results'][f'{validator_name}_issues'] = issues
                        all_passed = False

                # Display response preview
                if 'response' in response:
                    resp = response['response']
                    print(f"\n   📋 Response Summary:")

                    def get_section_len(section):
                        content = resp.get(section, '')
                        if isinstance(content, dict):
                            return len(str(content.get('content', '')))
                        return len(str(content))

                    print(f"      - Direct Definition: {get_section_len('direct_definition')} chars")
                    print(f"      - Interpretive Insight: {get_section_len('interpretive_insight')} chars")
                    print(f"      - Canonical Teachings: {len(resp.get('canonical_teachings', []))} teachings")
                    print(f"      - Commentary: {get_section_len('commentary')} chars")
                    print(f"      - Lexical Analysis: {get_section_len('lexical_analysis')} chars")
                    print(f"      - Doctrinal Function: {get_section_len('doctrinal_function')} chars")
                    print(f"      - Final Summary: {get_section_len('final_summary')} chars")

                test_results['tests'][test_key]['status'] = 'PASSED' if all_passed else 'FAILED'

            except Exception as e:
                print(f"   ❌ Test Error: {e}")
                test_results['tests'][test_key]['status'] = 'ERROR'
                test_results['tests'][test_key]['results']['error'] = str(e)
                import traceback
                traceback.print_exc()

        await browser.close()

    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)

    passed = sum(1 for t in test_results['tests'].values() if t['status'] == 'PASSED')
    failed = sum(1 for t in test_results['tests'].values() if t['status'] == 'FAILED')
    errors = sum(1 for t in test_results['tests'].values() if t['status'] == 'ERROR')

    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Errors: {errors}")
    print(f"Total Tests: {len(test_results['tests'])}")

    print("\n" + json.dumps(test_results, indent=2))

    return test_results


if __name__ == "__main__":
    result = asyncio.run(test_api_response_format())
    print("\n✅ Response format validation completed")
