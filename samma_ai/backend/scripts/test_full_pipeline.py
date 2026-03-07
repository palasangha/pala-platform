#!/usr/bin/env python3
"""
test_full_pipeline.py — End-to-end test: 9 questions × format validation

3 Common   — beginner-level Dhamma concepts
3 Advanced — intermediate doctrinal questions
3 Expert   — specialist Abhidhamma/Vinaya/Pali philology questions

Validates:
  - HTTP 200 response
  - Required top-level keys present
  - All 8 response sections populated (non-empty)
  - canonical_teachings: at least 1 teaching with pali/english/explanation/reference
  - pali_texts: at least 1 passage returned from Tipitaka
  - formatted_text: all 8 section headers present

Usage:
    cd backend
    python scripts/test_full_pipeline.py [--url http://localhost:5001] [--model copilot]
"""

import sys
import os
import json
import time
import argparse
import requests
from typing import Dict, List, Tuple

# ── Question banks ─────────────────────────────────────────────────────────────

COMMON_QUESTIONS = [
    {
        'id': 'C1',
        'question': 'What is the meaning of dukkha?',
        'level': 'Common',
        'expect_pali': ['dukkh'],
    },
    {
        'id': 'C2',
        'question': 'What are the Three Jewels (Ti-Ratana)?',
        'level': 'Common',
        'expect_pali': ['buddha', 'dhamma', 'sangha', 'ratana'],
    },
    {
        'id': 'C3',
        'question': 'What is metta (loving-kindness) in Buddhism?',
        'level': 'Common',
        'expect_pali': ['mett'],
    },
]

ADVANCED_QUESTIONS = [
    {
        'id': 'A1',
        'question': 'Explain the twelve links of dependent origination (paticca-samuppada).',
        'level': 'Advanced',
        'expect_pali': ['pa\u1e6diccasamuppāda', 'pa\u1e6diccasamuppada', 'avijj', 'nidāna', 'nidana'],
    },
    {
        'id': 'A2',
        'question': 'What is the difference between samatha and vipassana meditation?',
        'level': 'Advanced',
        'expect_pali': ['samatha', 'vipassan'],
    },
    {
        'id': 'A3',
        'question': 'Explain the five aggregates (panca-khandha) and their role in understanding non-self.',
        'level': 'Advanced',
        'expect_pali': ['khandh', 'rūpa', 'vedanā', 'anatt'],
    },
]

EXPERT_QUESTIONS = [
    {
        'id': 'E1',
        'question': 'In the Abhidhamma, what is the precise classification of citta (consciousness) types and their cetasika (mental factors) according to the Dhammasangani?',
        'level': 'Expert',
        'expect_pali': ['citta', 'cetasika', 'dhammasangani', 'kusala', 'akusala'],
    },
    {
        'id': 'E2',
        'question': 'What is the Vinaya rule (Parajika) regarding theft and what are the precise conditions that constitute a full violation according to the Suttavibhanga commentarial analysis?',
        'level': 'Expert',
        'expect_pali': ['pārājika', 'parajika', 'vinaya', 'adinn', 'theyyacitta'],
    },
    {
        'id': 'E3',
        'question': 'Analyze the Pali grammatical structure of the term "sabbe sankhara anicca" and its doctrinal significance in the three characteristics of existence.',
        'level': 'Expert',
        'expect_pali': ['sabbe', 'saṅkhāra', 'sankhara', 'anicca', 'tilakkhaṇa'],
    },
]

ALL_QUESTIONS = COMMON_QUESTIONS + ADVANCED_QUESTIONS + EXPERT_QUESTIONS

# ── Format validation ──────────────────────────────────────────────────────────

REQUIRED_TOP_KEYS = ['id', 'conversation_id', 'model_used', 'response', 'passages', 'timestamp']

REQUIRED_RESPONSE_KEYS = [
    'direct_definition',
    'interpretive_insight',
    'canonical_teachings',
    'commentary',
    'tika_clarification',
    'lexical_analysis',
    'doctrinal_function',
    'final_summary',
    'pali_texts',
    'formatted_text',
]

FORMATTED_TEXT_HEADERS = [
    '1. DIRECT DEFINITION',
    '2. SAMMA AI INTERPRETIVE INSIGHT',
    '3. CANONICAL TEACHINGS',
    '8. FINAL TEACHING SUMMARY',
]

SECTION_FIELDS = [
    'direct_definition',
    'interpretive_insight',
    'commentary',
    'tika_clarification',
    'lexical_analysis',
    'doctrinal_function',
    'final_summary',
]


def _contains_any(text: str, fragments: list) -> bool:
    t = text.lower()
    return any(f.lower() in t for f in fragments)


def validate_format(data: Dict, test_id: str) -> Tuple[List[str], List[str]]:
    """
    Returns (errors, warnings).
    errors   = format failures (hard failures)
    warnings = non-fatal issues worth noting
    """
    errors = []
    warnings = []

    # 1. Top-level keys
    for k in REQUIRED_TOP_KEYS:
        if k not in data:
            errors.append(f"Missing top-level key: '{k}'")

    resp = data.get('response', {})
    if not isinstance(resp, dict):
        errors.append("'response' is not a dict")
        return errors, warnings

    # 2. Response sub-keys
    for k in REQUIRED_RESPONSE_KEYS:
        if k not in resp:
            errors.append(f"response missing key: '{k}'")

    # 3. Section content non-empty
    for field in SECTION_FIELDS:
        section = resp.get(field, {})
        if isinstance(section, dict):
            content = section.get('content', '').strip()
        else:
            content = str(section).strip()
        if not content:
            warnings.append(f"response.{field}.content is empty")

    # 4. canonical_teachings
    teachings = resp.get('canonical_teachings', [])
    if not teachings:
        errors.append("canonical_teachings is empty (no teaching blocks)")
    else:
        for i, t in enumerate(teachings):
            for field in ['pali', 'english', 'explanation', 'reference']:
                if not t.get(field, '').strip():
                    warnings.append(f"canonical_teachings[{i}].{field} is empty")

    # 5. pali_texts (passages from Tipitaka)
    pali_texts = resp.get('pali_texts', [])
    if not pali_texts:
        warnings.append("pali_texts is empty (no Tipitaka passages returned)")
    else:
        for i, pt in enumerate(pali_texts):
            if not pt.get('pali', '').strip():
                warnings.append(f"pali_texts[{i}].pali is empty")

    # 6. formatted_text headers
    ft = resp.get('formatted_text', '')
    for header in FORMATTED_TEXT_HEADERS:
        if header not in ft:
            warnings.append(f"formatted_text missing section header: '{header}'")

    return errors, warnings


def run_test(url: str, model_id: str, test: Dict, timeout: int = 120) -> Dict:
    """Send one question to the API and validate the response."""
    tid = test['id']
    level = test['level']
    question = test['question']

    print(f"\n{'─'*70}")
    print(f"  [{tid}] {level.upper()}")
    print(f"  Q: {question}")
    print(f"{'─'*70}")

    start = time.time()
    try:
        resp = requests.post(
            f"{url}/api/chat",
            json={'message': question, 'model_id': model_id},
            timeout=timeout,
        )
        elapsed = time.time() - start
    except requests.exceptions.ConnectionError as e:
        print(f"  ✗ CONNECTION ERROR: {e}")
        return {'id': tid, 'status': 'connection_error', 'error': str(e)}
    except requests.exceptions.Timeout:
        print(f"  ✗ TIMEOUT after 120s")
        return {'id': tid, 'status': 'timeout'}

    print(f"  HTTP {resp.status_code}  ({elapsed:.1f}s)")

    if resp.status_code != 200:
        print(f"  ✗ Non-200 response: {resp.text[:300]}")
        return {'id': tid, 'status': 'http_error', 'http_status': resp.status_code}

    try:
        data = resp.json()
    except Exception as e:
        print(f"  ✗ JSON parse error: {e}")
        return {'id': tid, 'status': 'json_error', 'error': str(e)}

    # Format validation
    errors, warnings = validate_format(data, tid)

    # Passage count
    passages = data.get('passages', [])
    resp_obj  = data.get('response', {})
    teachings = resp_obj.get('canonical_teachings', [])

    print(f"  Passages returned : {len(passages)}")
    print(f"  Teachings found   : {len(teachings)}")

    # Pali content check
    all_pali = ' '.join(
        pt.get('pali', '') for pt in resp_obj.get('pali_texts', [])
    ) + ' '.join(p.get('pali_text', '') for p in passages)

    pali_ok = _contains_any(all_pali, test.get('expect_pali', []))
    if test.get('expect_pali'):
        pali_status = '✓' if pali_ok else '✗'
        print(f"  Pali relevance    : {pali_status} (expected one of {test['expect_pali'][:2]}...)")

    # Show section fill status
    section_status = []
    for field in SECTION_FIELDS:
        section = resp_obj.get(field, {})
        content = section.get('content', '').strip() if isinstance(section, dict) else str(section).strip()
        section_status.append(f"{field[:12]}={'✓' if content else '✗'}")
    print(f"  Sections          : {' '.join(section_status)}")

    # Show first teaching snippet
    if teachings:
        t0 = teachings[0]
        print(f"  Teaching[0] pali  : {t0.get('pali','')[:80]}...")
        print(f"  Teaching[0] ref   : {t0.get('reference','')[:60]}")

    # Errors / warnings
    if errors:
        print(f"\n  ✗ FORMAT ERRORS ({len(errors)}):")
        for e in errors:
            print(f"    • {e}")
    if warnings:
        print(f"\n  ⚠ WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"    • {w}")

    if not errors:
        print(f"\n  ✓ FORMAT OK")

    return {
        'id': tid,
        'level': level,
        'status': 'pass' if not errors else 'fail',
        'pali_ok': pali_ok,
        'passages': len(passages),
        'teachings': len(teachings),
        'errors': errors,
        'warnings': warnings,
        'elapsed': round(elapsed, 1),
    }


def main():
    parser = argparse.ArgumentParser(description='Samma AI full pipeline test')
    parser.add_argument('--url',     default='http://localhost:5001', help='Base URL')
    parser.add_argument('--model',   default='copilot',              help='model_id')
    parser.add_argument('--ids',     default='',                     help='Comma-separated test IDs to run (e.g. C1,A2,E3). Default: all')
    parser.add_argument('--timeout', default=120, type=int,          help='Per-request timeout in seconds (default: 120)')
    args = parser.parse_args()

    tests_to_run = ALL_QUESTIONS
    if args.ids:
        ids = [x.strip().upper() for x in args.ids.split(',')]
        tests_to_run = [t for t in ALL_QUESTIONS if t['id'] in ids]
        if not tests_to_run:
            print(f"No tests matched IDs: {ids}")
            sys.exit(1)

    print(f"\n{'='*70}")
    print(f"  Samma AI — Full Pipeline Test")
    print(f"  URL   : {args.url}")
    print(f"  Model : {args.model}")
    print(f"  Tests : {len(tests_to_run)} questions")
    print(f"  Timeout: {args.timeout}s per request")
    print(f"{'='*70}")

    results = []
    for test in tests_to_run:
        result = run_test(args.url, args.model, test, timeout=args.timeout)
        results.append(result)

    # Summary table
    print(f"\n\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    print(f"  {'ID':<4}  {'Level':<8}  {'Status':<6}  {'Pali':<5}  {'Pass':<5}  {'Warn':<5}  {'Time':>5}s")
    print(f"  {'─'*4}  {'─'*8}  {'─'*6}  {'─'*5}  {'─'*5}  {'─'*5}  {'─'*6}")

    passed = failed = 0
    by_level = {'Common': [], 'Advanced': [], 'Expert': []}

    for r in results:
        if 'status' not in r:
            continue
        status_str = '✓ PASS' if r.get('status') == 'pass' else '✗ FAIL'
        pali_str   = '✓' if r.get('pali_ok') else '✗'
        level      = r.get('level', '?')
        print(f"  {r['id']:<4}  {level:<8}  {status_str:<6}  {pali_str:<5}  "
              f"{len(r.get('errors',[])):<5}  {len(r.get('warnings',[])):<5}  "
              f"{r.get('elapsed',0):>6.1f}")
        if r.get('status') == 'pass':
            passed += 1
        else:
            failed += 1
        if level in by_level:
            by_level[level].append(r.get('status') == 'pass')

    print(f"\n  Overall  : {passed} passed, {failed} failed / {len(results)} total")
    for level, statuses in by_level.items():
        if statuses:
            p = sum(statuses)
            print(f"  {level:<10}: {p}/{len(statuses)} passed")

    print(f"{'='*70}\n")
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
