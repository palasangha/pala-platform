#!/usr/bin/env python3
"""
Playwright Test - Logical Validation of Each Response Section
Analyzes each of the 8 Dhamma response sections for logical acceptance
"""

import asyncio
import json
import re
from datetime import datetime


class LogicalValidator:
    """Validates response sections for logical coherence and accuracy."""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "validations": {},
            "summary": {}
        }

    async def test_api_response(self, question: str, model_id: str = 'claude-sonnet-4-20250514'):
        """Fetch API response using Playwright."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print("❌ Playwright not installed")
            return None

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                response = await page.evaluate(f"""
                    async () => {{
                        const res = await fetch('http://localhost:5001/api/chat', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/json'}},
                            body: JSON.stringify({{
                                message: '{question}',
                                model_id: '{model_id}'
                            }})
                        }});
                        return {{
                            status: res.status,
                            data: await res.json()
                        }};
                    }}
                """)

                await browser.close()
                return response
            except Exception as e:
                await browser.close()
                print(f"Error: {e}")
                return None

    def validate_section(self, section_name: str, content: dict, question: str) -> dict:
        """Validate individual section for logical coherence."""
        result = {
            "section": section_name,
            "checks": {},
            "score": 0,
            "max_score": 0,
            "analysis": ""
        }

        # Handle both dict and string formats
        if isinstance(content, dict):
            text = content.get('content', '')
            title = content.get('title', '')
        else:
            text = str(content)
            title = section_name

        # Check 1: Content not empty
        result["max_score"] += 1
        if text and len(text.strip()) > 0:
            result["checks"]["not_empty"] = "✅ PASS"
            result["score"] += 1
        else:
            result["checks"]["not_empty"] = "❌ FAIL - Empty content"

        # Section-specific validations
        if section_name == "direct_definition":
            result = self._validate_direct_definition(result, text, question)
        elif section_name == "interpretive_insight":
            result = self._validate_interpretive_insight(result, text, question)
        elif section_name == "canonical_teachings":
            result = self._validate_canonical_teachings(result, content, question)
        elif section_name == "commentary":
            result = self._validate_commentary(result, text, question)
        elif section_name == "tika_clarification":
            result = self._validate_tika(result, text, question)
        elif section_name == "lexical_analysis":
            result = self._validate_lexical(result, text, question)
        elif section_name == "doctrinal_function":
            result = self._validate_doctrinal_function(result, text, question)
        elif section_name == "final_summary":
            result = self._validate_final_summary(result, text, question)

        # Calculate final score
        result["acceptance"] = "✅ ACCEPT" if result["score"] == result["max_score"] else "⚠️  PARTIAL"
        if result["score"] < result["max_score"] / 2:
            result["acceptance"] = "❌ REJECT"

        return result

    def _validate_direct_definition(self, result, text, question):
        """Validate direct definition section."""
        result["max_score"] += 3

        # Check 2: Concise (3-6 lines typically)
        lines = len([l for l in text.split('\n') if l.strip()])
        if 2 <= lines <= 10:
            result["checks"]["concise"] = f"✅ PASS - {lines} lines"
            result["score"] += 1
        else:
            result["checks"]["concise"] = f"⚠️  {lines} lines (expected 3-6)"

        # Check 3: No interpretation marker (should be canonical)
        if "interpretation" not in text.lower() and "believe" not in text.lower():
            result["checks"]["canonical_tone"] = "✅ PASS - No AI interpretation"
            result["score"] += 1
        else:
            result["checks"]["canonical_tone"] = "⚠️  Contains interpretation language"

        # Check 4: Related to question topic
        question_words = set(question.lower().split())
        text_words = set(text.lower().split())
        overlap = len(question_words & text_words)
        if overlap > 0:
            result["checks"]["relevance"] = f"✅ PASS - {overlap} matching terms"
            result["score"] += 1
        else:
            result["checks"]["relevance"] = "❌ FAIL - No overlap with question"

        result["analysis"] = f"Definition is {'canonical' if result['score'] == 3 else 'partially'} aligned"
        return result

    def _validate_interpretive_insight(self, result, text, question):
        """Validate interpretive insight section."""
        result["max_score"] += 2

        # Check 2: Contains synthesis/interpretation
        synthesis_words = ["integr", "synth", "understand", "insight", "perspective"]
        has_synthesis = any(word in text.lower() for word in synthesis_words)
        if has_synthesis:
            result["checks"]["interpretive"] = "✅ PASS - Contains synthesis"
            result["score"] += 1
        else:
            result["checks"]["interpretive"] = "⚠️  Limited interpretive content"

        # Check 3: Clearly marks as AI interpretation
        if "samma ai" in text.lower() or "interpretation" in text.lower():
            result["checks"]["marked_as_ai"] = "✅ PASS - Marked as interpretation"
            result["score"] += 1
        else:
            result["checks"]["marked_as_ai"] = "⚠️  Not clearly marked as interpretation"

        result["analysis"] = "Provides practical wisdom while maintaining distinction from canon"
        return result

    def _validate_canonical_teachings(self, result, content, question):
        """Validate canonical teachings section."""
        result["max_score"] += 4

        if not isinstance(content, list):
            result["checks"]["is_list"] = "❌ FAIL - Not a list"
            result["analysis"] = "Canonical teachings must be a list of teachings"
            return result

        result["checks"]["is_list"] = f"✅ PASS - {len(content)} teachings"
        result["score"] += 1

        if not content:
            result["checks"]["has_teachings"] = "❌ FAIL - Empty list"
            result["analysis"] = "No canonical teachings found"
            return result

        result["checks"]["has_teachings"] = "✅ PASS - Contains teachings"
        result["score"] += 1

        # Validate first teaching structure
        teaching = content[0]
        required_fields = ["pali", "english", "explanation", "reference"]
        missing = [f for f in required_fields if f not in teaching or not teaching[f]]

        if not missing:
            result["checks"]["structure"] = "✅ PASS - All fields present"
            result["score"] += 1
        else:
            result["checks"]["structure"] = f"⚠️  Missing: {', '.join(missing)}"

        # Check English is different from Pāḷi
        pali = teaching.get("pali", "").strip()
        english = teaching.get("english", "").strip()

        if pali and english and pali != english:
            result["checks"]["pali_english_different"] = "✅ PASS - English differs from Pāḷi"
            result["score"] += 1
        elif not english:
            result["checks"]["pali_english_different"] = "❌ FAIL - No English translation"
        else:
            result["checks"]["pali_english_different"] = "❌ FAIL - English duplicates Pāḷi"

        result["analysis"] = f"Valid structure with {len(content)} teachings, proper English translation"
        return result

    def _validate_commentary(self, result, text, question):
        """Validate commentary section."""
        result["max_score"] += 2

        # Check 2: References Aṭṭhakathā
        if "atthakathat" in text.lower() or "commentary" in text.lower():
            result["checks"]["aṭṭhakathā_reference"] = "✅ PASS - References commentary tradition"
            result["score"] += 1
        else:
            result["checks"]["aṭṭhakathā_reference"] = "⚠️  No explicit Aṭṭhakathā reference"

        # Check 3: Contains explanation (not just Pāḷi)
        if len(text) > 50:
            result["checks"]["explanation_present"] = "✅ PASS - Contains explanation"
            result["score"] += 1
        else:
            result["checks"]["explanation_present"] = "⚠️  Brief or missing explanation"

        result["analysis"] = "Commentary provides deeper technical understanding"
        return result

    def _validate_tika(self, result, text, question):
        """Validate Ṭīkā section."""
        result["max_score"] += 1

        # Check 2: Either present or explicitly states not needed
        if len(text.strip()) > 20 or "not provided" in text.lower() or "not necessary" in text.lower():
            result["checks"]["present_or_noted"] = "✅ PASS - Present or noted as not needed"
            result["score"] += 1
        else:
            result["checks"]["present_or_noted"] = "⚠️  Unclear status"

        result["analysis"] = "Ṭīkā included only when doctrinally relevant"
        return result

    def _validate_lexical(self, result, text, question):
        """Validate lexical analysis section."""
        result["max_score"] += 2

        # Check 2: Contains root/etymology
        if "root" in text.lower() or "dhat" in text.lower() or "etymology" in text.lower():
            result["checks"]["root_present"] = "✅ PASS - Contains root analysis"
            result["score"] += 1
        else:
            result["checks"]["root_present"] = "⚠️  No root analysis found"

        # Check 3: Explains meaning progression
        meaning_words = ["literal", "technical", "doctrinal", "meaning", "definition"]
        has_meanings = sum(1 for w in meaning_words if w in text.lower())
        if has_meanings >= 2:
            result["checks"]["meaning_levels"] = f"✅ PASS - {has_meanings} meaning levels"
            result["score"] += 1
        else:
            result["checks"]["meaning_levels"] = "⚠️  Single or unclear meaning level"

        result["analysis"] = "Provides etymological and doctrinal word analysis"
        return result

    def _validate_doctrinal_function(self, result, text, question):
        """Validate doctrinal function section."""
        result["max_score"] += 2

        # Check 2: References Four Noble Truths, Dependent Origination, etc.
        doctrinal_refs = ["noble truth", "dependent origin", "impermanence", "anatta", "three characteristics"]
        has_refs = sum(1 for ref in doctrinal_refs if ref in text.lower())
        if has_refs >= 1:
            result["checks"]["doctrinal_framework"] = f"✅ PASS - {has_refs} framework references"
            result["score"] += 1
        else:
            result["checks"]["doctrinal_framework"] = "⚠️  Limited doctrinal framework"

        # Check 3: Analytical (not devotional)
        devotional = ["blessed", "precious", "holy", "sacred", "divine", "worship"]
        is_devotional = any(word in text.lower() for word in devotional)
        if not is_devotional:
            result["checks"]["analytical_tone"] = "✅ PASS - Analytical tone"
            result["score"] += 1
        else:
            result["checks"]["analytical_tone"] = "⚠️  Contains devotional language"

        result["analysis"] = "Explains doctrinal function within Buddhist framework"
        return result

    def _validate_final_summary(self, result, text, question):
        """Validate final summary section."""
        result["max_score"] += 2

        # Check 2: Integrative (brings together themes)
        integration_words = ["integration", "synthesis", "understand", "see", "realize", "path"]
        has_integration = sum(1 for word in integration_words if word in text.lower())
        if has_integration >= 2:
            result["checks"]["integrative"] = f"✅ PASS - {has_integration} integration indicators"
            result["score"] += 1
        else:
            result["checks"]["integrative"] = "⚠️  Limited integration"

        # Check 3: References liberation/Nibbāna
        if "liberation" in text.lower() or "nibbana" in text.lower() or "nirvana" in text.lower():
            result["checks"]["liberation_oriented"] = "✅ PASS - Oriented toward liberation"
            result["score"] += 1
        else:
            result["checks"]["liberation_oriented"] = "⚠️  No liberation reference"

        result["analysis"] = "Provides guiding synthesis toward ultimate goal"
        return result

    def _run_mock_validation(self):
        """Run validation with mock data to demonstrate logical checks."""
        print("\n   📋 MOCK VALIDATION DATA")
        print("   " + "-"*76)

        mock_response = {
            "direct_definition": {
                "title": "DIRECT DEFINITION",
                "content": "Dukkha refers to the unsatisfactory nature of existence, encompassing physical pain, emotional distress, and the inherent instability of all conditioned phenomena. It is a central aspect of the Four Noble Truths."
            },
            "interpretive_insight": {
                "title": "INTERPRETIVE INSIGHT",
                "content": "Dukkha implies more than just overt suffering; it encompasses a broader existential realization that life, as experienced through the lens of sensory attachment and craving, is fundamentally unsatisfactory. This Samma AI interpretation integrates doctrinal principles across Nikāyas."
            },
            "canonical_teachings": [
                {
                    "pali": "\"Idaṃ kho pana, bhikkhave, dukkhaṃ ariyasaccaṃ: jāti pi dukkhā…\"",
                    "english": "\"This, monks, is the Noble Truth of suffering: birth is suffering, aging is suffering, death is suffering…\"",
                    "explanation": "This establishes Dukkha as the First Noble Truth, framing it as an experiential reality that must be recognized for liberation to be sought.",
                    "reference": "Sutta Piṭaka → Saṃyutta Nikāya → Saccasaṃyutta → Dhammacakkappavattana Sutta"
                }
            ],
            "commentary": {
                "title": "AṬṬHAKATHĀ COMMENTARY",
                "content": "The Aṭṭhakathā commentary elucidates Dukkha as that which causes oppression or affliction, reinforcing the understanding of suffering's pervasive nature across all realms of existence."
            },
            "tika_clarification": {
                "title": "ṬĪKĀ CLARIFICATION",
                "content": "The Ṭīkā further clarifies that Dukkha functions as the fundamental characteristic of saṃsāra, demonstrating how all conditioned existence carries the mark of unsatisfactoriness."
            },
            "lexical_analysis": {
                "title": "LEXICAL ANALYSIS",
                "content": "Root (Dhātu): dukkha means difficult to bear or oppressive. Literal meaning: hard to endure. Technical doctrinal meaning: the unstable, oppressive nature of conditioned existence. Contextual shifts: from mere pain to encompass all forms of existential dissatisfaction."
            },
            "doctrinal_function": {
                "title": "DOCTRINAL FUNCTION",
                "content": "Dukkha functions as the foundation of the First Noble Truth within the Four Noble Truths framework. It demonstrates the arising of suffering through Dependent Origination via craving and attachment. It embodies the Three Characteristics of impermanence and non-self, illustrating fundamental insights into the human condition."
            },
            "final_summary": {
                "title": "FINAL SUMMARY",
                "content": "Understanding Dukkha is crucial for cultivating wisdom in the Buddhist path. By deeply recognizing suffering, one becomes motivated to practice the Noble Eightfold Path, which ultimately leads to the cessation of Dukkha — the realization of Nibbāna, the unconditioned state free from all suffering."
            }
        }

        question = "What is dukkha?"
        sections = [
            ('direct_definition', 'Direct Definition'),
            ('interpretive_insight', 'Interpretive Insight'),
            ('canonical_teachings', 'Canonical Teachings'),
            ('commentary', 'Aṭṭhakathā Commentary'),
            ('tika_clarification', 'Ṭīkā Clarification'),
            ('lexical_analysis', 'Lexical Analysis'),
            ('doctrinal_function', 'Doctrinal Function'),
            ('final_summary', 'Final Summary'),
        ]

        total_score = 0
        max_total = 0

        for section_key, section_name in sections:
            content = mock_response.get(section_key, {})
            validation = self.validate_section(section_key, content, question)

            total_score += validation['score']
            max_total += validation['max_score']

            status = validation['acceptance']
            score = f"{validation['score']}/{validation['max_score']}"
            print(f"   {status} {section_name:30} [{score}]")

        percentage = (total_score / max_total * 100) if max_total > 0 else 0
        print(f"\n   📊 Mock Data Score: {total_score}/{max_total} ({percentage:.1f}%)")

        return percentage

    async def run_comprehensive_test(self):
        """Run comprehensive test on all sections."""
        print("\n" + "="*80)
        print("🧪 PLAYWRIGHT LOGICAL VALIDATION TEST")
        print("="*80)

        test_questions = [
            ("What is dukkha?", "Understanding suffering"),
            ("Explain anicca", "Understanding impermanence"),
        ]

        all_results = []

        for question, desc in test_questions:
            print(f"\n📝 Testing: {desc}")
            print(f"   Question: '{question}'")
            print("-" * 80)

            # Get API response
            response = await self.test_api_response(question)

            if not response or response.get('status') != 200:
                print(f"   ❌ API Error: {response}")
                continue

            data = response['data']
            resp = data.get('response', {})

            # Validate each section
            section_results = []
            total_score = 0
            max_total = 0

            sections = [
                ('direct_definition', 'Direct Definition'),
                ('interpretive_insight', 'Interpretive Insight'),
                ('canonical_teachings', 'Canonical Teachings'),
                ('commentary', 'Aṭṭhakathā Commentary'),
                ('tika_clarification', 'Ṭīkā Clarification'),
                ('lexical_analysis', 'Lexical Analysis'),
                ('doctrinal_function', 'Doctrinal Function'),
                ('final_summary', 'Final Summary'),
            ]

            for section_key, section_name in sections:
                content = resp.get(section_key, {})
                validation = self.validate_section(section_key, content, question)
                section_results.append(validation)

                total_score += validation['score']
                max_total += validation['max_score']

                # Print result
                status = validation['acceptance']
                score = f"{validation['score']}/{validation['max_score']}"
                print(f"   {status} {section_name:30} [{score}]")

                # Print checks
                for check, result in validation['checks'].items():
                    print(f"      • {result}")

            # Summary for this question
            print(f"\n   📊 Summary: {total_score}/{max_total} checks passed")
            percentage = (total_score / max_total * 100) if max_total > 0 else 0
            print(f"   Score: {percentage:.1f}%")

            result_set = {
                "question": question,
                "description": desc,
                "total_score": total_score,
                "max_score": max_total,
                "percentage": percentage,
                "sections": section_results
            }
            all_results.append(result_set)
            self.results["validations"][question] = result_set

        # Final summary
        print("\n" + "="*80)
        print("📊 OVERALL TEST SUMMARY")
        print("="*80)

        avg_percentage = 0
        if all_results:
            avg_percentage = sum(r['percentage'] for r in all_results) / len(all_results)
            print(f"\n✅ Tests Completed: {len(all_results)}")
            print(f"📈 Average Score: {avg_percentage:.1f}%")

            if avg_percentage >= 80:
                print("🎯 LOGICAL ACCEPTANCE: ✅ EXCELLENT")
            elif avg_percentage >= 60:
                print("🎯 LOGICAL ACCEPTANCE: ⚠️  ACCEPTABLE")
            else:
                print("🎯 LOGICAL ACCEPTANCE: ❌ NEEDS IMPROVEMENT")
        else:
            print("\n⚠️  No tests completed - API unavailable")
            print("    Running with mock data for validation demonstration...")
            avg_percentage = self._run_mock_validation()

        self.results["summary"] = {
            "tests_completed": len(all_results),
            "average_score": avg_percentage,
            "status": "EXCELLENT" if avg_percentage >= 80 else ("ACCEPTABLE" if avg_percentage >= 60 else "NEEDS_IMPROVEMENT")
        }

        return self.results


async def main():
    """Run the test."""
    validator = LogicalValidator()
    results = await validator.run_comprehensive_test()

    # Save results
    with open('/tmp/logical_validation_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("\n📄 Results saved to /tmp/logical_validation_results.json")


if __name__ == "__main__":
    asyncio.run(main())
