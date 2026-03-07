#!/usr/bin/env python3
"""
Test Deepseek translation quality for Pali Buddhist texts.
"""

import requests
import json
import time
from typing import Tuple, List

OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"
MODEL = "deepseek-r1:32b"

# Sample Pali passages with known English translations
TEST_PASSAGES = [
    {
        "pali": "Metta bhavana citta sukhaya hotati",
        "known_translation": "Cultivation of loving-kindness brings happiness to the mind",
        "context": "Basic metta practice"
    },
    {
        "pali": "Sabbapapassa akarana, kusalassa upsampadha, Sachitta pariyodapanam, etam buddhana sasanam",
        "known_translation": "To avoid all evil, to cultivate good, and to purify one's mind - this is the teaching of all the Buddhas",
        "context": "Dhammapada verse 183"
    },
    {
        "pali": "Anatta vipassana bhavana dukkha samudaya nirodha magga",
        "known_translation": "Meditation on non-self, insight, suffering, origin, cessation, and the path",
        "context": "Four Noble Truths framework"
    },
    {
        "pali": "Samadhi dhammo aniccam anicca sabbe sankhara anicca",
        "known_translation": "Concentration is a quality, all conditioned things are impermanent",
        "context": "Key Buddhist concepts"
    },
    {
        "pali": "Samma samadhi etam magga bhavana",
        "known_translation": "Right concentration is the path to cultivation",
        "context": "Eightfold Path"
    },
]

# Shorter, simpler terms
SIMPLE_TERMS = [
    {"pali": "metta", "known": "loving-kindness"},
    {"pali": "karuna", "known": "compassion"},
    {"pali": "mudita", "known": "sympathetic joy"},
    {"pali": "upekkha", "known": "equanimity"},
    {"pali": "samadhi", "known": "concentration"},
    {"pali": "prajna", "known": "wisdom"},
    {"pali": "sila", "known": "morality/virtue"},
    {"pali": "dukkha", "known": "suffering"},
    {"pali": "anicca", "known": "impermanence"},
    {"pali": "anatta", "known": "non-self"},
]

def translate_pali(pali_text: str) -> Tuple[str, float]:
    """Translate Pali to English using Deepseek."""
    prompt = f"""Translate this Pali Buddhist text to English.
Keep it literal and accurate to preserve the original meaning.
Do not add commentary or explanation.

Pali text:
{pali_text}

English translation:"""

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "temperature": 0.3,  # Low temp for consistency
    }

    start_time = time.time()
    try:
        response = requests.post(OLLAMA_ENDPOINT, json=payload, timeout=30)
        elapsed = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            translation = result.get("response", "").strip()
            return translation, elapsed
        else:
            return f"[ERROR] HTTP {response.status_code}", elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        return f"[ERROR] {str(e)}", elapsed

def test_translations():
    """Test translation quality on sample passages."""
    print("=" * 80)
    print("DEEPSEEK PALI TRANSLATION QUALITY TEST")
    print("=" * 80)
    print()

    # Test simple terms first
    print("PART 1: SIMPLE PALI TERMS (Single Words)")
    print("-" * 80)
    simple_results = []

    for item in SIMPLE_TERMS:
        pali = item["pali"]
        known = item["known"]

        print(f"\nPali: {pali}")
        print(f"Known translation: {known}")
        print(f"Translating...", end=" ")

        translation, elapsed = translate_pali(pali)

        print(f"({elapsed:.2f}s)")
        print(f"Deepseek: {translation}")

        # Simple quality check
        keywords = known.lower().split("/")[0].split()  # Get first variant
        quality = "✅ GOOD" if any(kw.lower() in translation.lower() for kw in keywords) else "⚠️ PARTIAL"
        print(f"Quality: {quality}")

        simple_results.append({
            "pali": pali,
            "known": known,
            "deepseek": translation,
            "time": elapsed,
            "quality": quality
        })

    # Test complex passages
    print("\n" + "=" * 80)
    print("PART 2: COMPLEX PALI PASSAGES")
    print("-" * 80)
    complex_results = []

    for i, passage in enumerate(TEST_PASSAGES, 1):
        pali = passage["pali"]
        known = passage["known_translation"]
        context = passage["context"]

        print(f"\n[Passage {i}] {context}")
        print(f"Pali: {pali}")
        print(f"Known translation: {known}")
        print(f"Translating...", end=" ")

        translation, elapsed = translate_pali(pali)

        print(f"({elapsed:.2f}s)")
        print(f"Deepseek: {translation}")

        # Quality assessment (very basic)
        key_words = known.lower().split()[:3]
        match_count = sum(1 for kw in key_words if kw in translation.lower())
        quality_pct = (match_count / 3) * 100

        if quality_pct >= 66:
            quality = "✅ GOOD"
        elif quality_pct >= 33:
            quality = "⚠️ PARTIAL"
        else:
            quality = "❌ POOR"

        print(f"Quality: {quality} ({match_count}/3 key terms matched)")

        complex_results.append({
            "context": context,
            "pali": pali,
            "known": known,
            "deepseek": translation,
            "time": elapsed,
            "quality": quality,
            "match_score": quality_pct
        })

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 80)

    simple_good = sum(1 for r in simple_results if "✅" in r["quality"])
    complex_good = sum(1 for r in complex_results if "✅" in r["quality"])

    print(f"\nSimple terms: {simple_good}/{len(simple_results)} translations good ({simple_good*100//len(simple_results)}%)")
    print(f"Complex passages: {complex_good}/{len(complex_results)} translations good ({complex_good*100//len(complex_results)}%)")

    avg_time_simple = sum(r["time"] for r in simple_results) / len(simple_results)
    avg_time_complex = sum(r["time"] for r in complex_results) / len(complex_results)

    print(f"\nAverage response time (simple): {avg_time_simple:.2f}s")
    print(f"Average response time (complex): {avg_time_complex:.2f}s")

    print("\n" + "-" * 80)
    print("RECOMMENDATION:")
    print("-" * 80)

    overall_quality = (simple_good + complex_good) / (len(simple_results) + len(complex_results))

    if overall_quality >= 0.80:
        print("✅ PROCEED WITH IMPLEMENTATION")
        print("   Deepseek provides good translations for most Pali texts.")
        print("   Recommended for production use with fallback to original Pali.")
    elif overall_quality >= 0.60:
        print("⚠️ PROCEED WITH CAUTION")
        print("   Deepseek provides reasonable translations but with some gaps.")
        print("   Consider:")
        print("   - Manual review of critical passages")
        print("   - Use as fallback only, not primary translation")
        print("   - Flag translations for user review")
    else:
        print("❌ DO NOT PROCEED")
        print("   Translation quality too low for production use.")
        print("   Consider alternative models or translation services.")

    print()

def test_caching_strategy():
    """Test how caching would improve performance."""
    print("\n" + "=" * 80)
    print("CACHING STRATEGY TEST")
    print("=" * 80)

    # Translate same passage twice
    test_passage = "Metta bhavana"

    print(f"\nTranslating: '{test_passage}'")
    print("First call (no cache)...", end=" ")
    translation1, time1 = translate_pali(test_passage)
    print(f"✓ {time1:.2f}s")
    print(f"Result: {translation1}")

    print(f"\nSecond call (would be cached in production)...", end=" ")
    translation2, time2 = translate_pali(test_passage)
    print(f"✓ {time2:.2f}s")
    print(f"Result: {translation2}")

    print(f"\nSpeedup with caching: {time1/0.01:.0f}x (cached would be <10ms)")
    print(f"For 100 passages: {(time1 * 100):.1f}s → {(time2 * 100 + 0.01 * 99):.1f}s with caching")

if __name__ == "__main__":
    try:
        test_translations()
        test_caching_strategy()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nMake sure Ollama is running:")
        print("  ollama serve")
        print("\nAnd Deepseek model is pulled:")
        print("  ollama pull deepseek-r1:32b")
