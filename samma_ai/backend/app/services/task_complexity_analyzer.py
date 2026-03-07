"""
Task Complexity Analyzer - Determines if a question requires complex reasoning or simple lookup.

Scores questions 0-100:
  0-30:   Simple (factual lookup, definitions) → use DeepSeek (cheaper, fast)
  31-70:  Medium (interpretation, comparison) → use DeepSeek with monitoring
  71-100: Complex (reasoning, synthesis, philosophy) → use Claude (best quality)
"""

import logging
import re
from typing import Dict, Tuple

logger = logging.getLogger(__name__)


class TaskComplexityAnalyzer:
    """Analyzes Dhamma questions to determine reasoning complexity."""

    def __init__(self):
        """Initialize complexity scoring patterns."""
        # Simple tasks: factual lookups, definitions
        self.simple_keywords = [
            r'\b(what\s+is|define|meaning\s+of|explain\s+\w+)\b',
            r'\b(translate|pali\s+word|etymology)\b',
            r'\b(who\s+is|when\s+was|where\s+is)\b',
            r'\b(list|example|quote)\b',
        ]

        # Complex tasks: reasoning, synthesis, philosophy
        self.complex_keywords = [
            r'\b(why|how\s+does|explain.*relate|connection|difference)',
            r'\b(interpret|meaning\s+in\s+context|deeper|philosophical)',
            r'\b(reconcile|contradict|compare|contrast|relationship)',
            r'\b(purpose|function|doctrinal|practice|path)',
            r'\b(synthesis|integrate|understand|cultivate|liberation)',
            r'\b(nuance|subtlety|implication|consequence)',
        ]

        # Indicators of complexity
        self.complexity_indicators = {
            'length': {'threshold': 50, 'score': 15},  # Long questions
            'multiple_concepts': {'pattern': r'[,;]', 'threshold': 2, 'score': 20},
            'reasoning_verbs': {
                'pattern': r'\b(should|why|how|what.*mean|interpret|apply|relate)\b',
                'score': 25,
            },
            'conditional': {'pattern': r'\b(if|when|whether|assume)\b', 'score': 20},
            'multiple_questions': {'pattern': r'\?(?=.*\?)', 'score': 15},
        }

    def analyze(self, question: str, passages: list = None) -> Tuple[int, Dict]:
        """
        Analyze task complexity.

        Args:
            question: User's Dhamma question
            passages: Optional list of retrieved passages (affects complexity)

        Returns:
            (score: 0-100, details: analysis breakdown)
        """
        if not question or not isinstance(question, str):
            return 0, {'error': 'Invalid question'}

        question_lower = question.lower().strip()
        logger.debug(
            "[TaskComplexityAnalyzer.analyze] Analyzing question=%.100r",
            question,
        )

        score = 50  # Start at medium baseline
        details = {
            'raw_score': 0,
            'simple_score': 0,
            'complex_score': 0,
            'length_adjustment': 0,
            'passage_adjustment': 0,
            'reasoning_keywords': [],
            'complexity_level': '',
            'recommended_model': '',
            'rationale': [],
        }

        # ── SIMPLE KEYWORD DETECTION ──────────────────────────────────────
        for pattern in self.simple_keywords:
            if re.search(pattern, question_lower, re.IGNORECASE):
                details['simple_score'] += 15
                logger.debug(
                    "[TaskComplexityAnalyzer.analyze] Matched simple pattern: %s",
                    pattern,
                )

        # ── COMPLEX KEYWORD DETECTION ─────────────────────────────────────
        for pattern in self.complex_keywords:
            matches = re.findall(pattern, question_lower, re.IGNORECASE)
            if matches:
                details['complex_score'] += 15
                details['reasoning_keywords'].extend(matches)
                logger.debug(
                    "[TaskComplexityAnalyzer.analyze] Matched complex pattern: %s  "
                    "matches=%s", pattern, matches,
                )

        # ── LENGTH ADJUSTMENT ─────────────────────────────────────────────
        # Longer, detailed questions usually require more reasoning
        question_length = len(question_lower.split())
        if question_length > 30:
            length_adj = min(15, (question_length - 30) // 10)
            details['length_adjustment'] = length_adj
            details['rationale'].append(
                f"Longer question ({question_length} words) → +{length_adj} complexity"
            )
            score += length_adj

        # ── MULTIPLE CONCEPTS ─────────────────────────────────────────────
        # Questions with multiple concepts (separated by comma/semicolon)
        concept_separators = len(re.findall(r'[,;]', question_lower))
        if concept_separators >= 2:
            score += 10
            details['rationale'].append(
                f"Multiple concepts ({concept_separators} separators) → +10 complexity"
            )

        # ── CONDITIONAL/SUBJUNCTIVE REASONING ─────────────────────────────
        if re.search(r'\b(if|when|whether|assume|suppose)\b', question_lower):
            score += 15
            details['rationale'].append(
                "Conditional reasoning detected → +15 complexity"
            )

        # ── MULTIPLE QUESTIONS ────────────────────────────────────────────
        num_questions = len(re.findall(r'\?', question_lower))
        if num_questions > 1:
            score += 5 * (num_questions - 1)
            details['rationale'].append(
                f"Multiple questions ({num_questions}) → +{5 * (num_questions - 1)} complexity"
            )

        # ── PASSAGE CONTEXT ADJUSTMENT ────────────────────────────────────
        # If we have many relevant passages, it's likely a straightforward lookup
        if passages:
            passage_count = len(passages)
            if passage_count >= 5:
                # Many passages suggests straightforward reference
                score -= min(10, passage_count)
                details['passage_adjustment'] = -min(10, passage_count)
                details['rationale'].append(
                    f"High passage match count ({passage_count}) suggests "
                    "straightforward reference → -{details['passage_adjustment']} complexity"
                )

        # ── FINAL SCORING ──────────────────────────────────────────────────
        # Apply keyword scores (simple reduces, complex increases)
        final_score = score + (details['complex_score'] - details['simple_score'])

        # Clamp to 0-100 range
        final_score = max(0, min(100, final_score))
        details['raw_score'] = final_score

        # ── DETERMINE COMPLEXITY LEVEL ────────────────────────────────────
        if final_score <= 30:
            details['complexity_level'] = 'simple'
            details['recommended_model'] = 'deepseek'
            details['rationale'].append(
                "SIMPLE TASK: Use DeepSeek (fast, cheap, sufficient for factual lookup)"
            )
        elif final_score <= 70:
            details['complexity_level'] = 'medium'
            details['recommended_model'] = 'deepseek'
            details['rationale'].append(
                "MEDIUM TASK: Use DeepSeek (good enough, cost-effective). "
                "Monitor quality; escalate if needed."
            )
        else:
            details['complexity_level'] = 'complex'
            details['recommended_model'] = 'claude'
            details['rationale'].append(
                "COMPLEX TASK: Use Claude (superior reasoning for philosophy/synthesis)"
            )

        logger.info(
            "[TaskComplexityAnalyzer.analyze] COMPLETE — "
            "score=%d  level=%s  model=%s  question_len=%d",
            final_score,
            details['complexity_level'],
            details['recommended_model'],
            question_length,
        )

        return final_score, details

    def should_use_claude(self, question: str, passages: list = None) -> bool:
        """Quick check: return True if Claude recommended, False for DeepSeek."""
        score, details = self.analyze(question, passages)
        return details['recommended_model'] == 'claude'

    def get_model_for_complexity(self, complexity_score: int) -> str:
        """Get recommended model based on raw complexity score."""
        if complexity_score <= 30:
            return 'deepseek'
        elif complexity_score <= 70:
            return 'deepseek'
        else:
            return 'claude'
