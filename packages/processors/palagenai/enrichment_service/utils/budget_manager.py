"""
Budget Manager - Enforces budget limits and prevents cost overruns

Prevents enrichment from exceeding daily/document/monthly budgets
Automatically disables expensive agents when budget is low
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from enrichment_service.utils.cost_tracker import CostTracker

logger = logging.getLogger(__name__)


class BudgetManager:
    """
    Manages budget limits and controls enrichment behavior based on costs

    Can automatically disable expensive agents (e.g., Claude Opus) when:
    - Daily budget is near capacity
    - Document cost exceeds limit
    - Monthly budget is near capacity
    """

    def __init__(self, db=None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize BudgetManager

        Args:
            db: MongoDB database instance
            config: Optional configuration dict
        """
        self.cost_tracker = CostTracker(db, config)
        self.config = self.cost_tracker.config
        self.db = db

    def can_afford_task(self, task_name: str) -> bool:
        """
        Check if we can afford to run a task within remaining budget

        Args:
            task_name: Task name (e.g., 'generate_summary')

        Returns:
            True if task can be afforded within budget
        """
        # Get estimated cost
        task_cost = self.cost_tracker.estimate_task_cost(task_name)
        estimated_cost = task_cost.get('estimated_usd', 0.0)

        # Check against daily budget
        daily_budget = self.check_budget('daily')
        if daily_budget['spent_usd'] + estimated_cost > daily_budget['budget_usd']:
            logger.warning(
                f"Cannot afford task {task_name}: "
                f"${estimated_cost:.4f} would exceed daily budget"
            )
            return False

        return True

    def get_enrichment_config(self) -> Dict[str, bool]:
        """
        Get recommended enrichment configuration based on budget status

        Returns:
            Config dict with which agents to enable:
            {
                'enable_ollama': true,
                'enable_claude_sonnet': bool,
                'enable_claude_opus': bool,
                'enable_entity_disambiguation': bool
            }
        """
        daily_budget = self.check_budget('daily')
        spent_percent = daily_budget['percentage_used']

        config = {
            'enable_ollama': True,  # Always enable (free)
            'enable_claude_sonnet': spent_percent < 50,  # Disable if >50% spent
            'enable_claude_opus': spent_percent < 25,    # Disable if >25% spent
            'enable_entity_disambiguation': spent_percent < 75  # Optional
        }

        if not config['enable_claude_opus']:
            logger.info("Budget alert: Disabling Claude Opus, too much daily spend")
        if not config['enable_claude_sonnet']:
            logger.warning("Budget critical: Disabling Claude Sonnet, nearly at daily limit")

        return config

    def should_enable_context_agent(self) -> bool:
        """
        Determine if we should enable expensive context agent (Claude Opus)

        Returns:
            True if budget allows context agent, False otherwise
        """
        daily_budget = self.check_budget('daily')
        monthly_budget = self.check_budget('monthly')

        # Disable if daily budget is >80% spent
        if daily_budget['percentage_used'] > 80:
            logger.warning(f"Context agent disabled: daily budget {daily_budget['percentage_used']:.1f}% spent")
            return False

        # Disable if monthly budget is >80% spent
        if monthly_budget['percentage_used'] > 80:
            logger.warning(f"Context agent disabled: monthly budget {monthly_budget['percentage_used']:.1f}% spent")
            return False

        return True

    def is_daily_budget_exceeded(self) -> bool:
        """Check if daily budget has been exceeded"""
        daily_budget = self.check_budget('daily')
        exceeded = daily_budget['spent_usd'] > daily_budget['budget_usd']

        if exceeded:
            logger.error(
                f"Daily budget exceeded by ${daily_budget['spent_usd'] - daily_budget['budget_usd']:.2f}"
            )

        return exceeded

    def is_monthly_budget_exceeded(self) -> bool:
        """Check if monthly budget has been exceeded"""
        monthly_budget = self.check_budget('monthly')
        exceeded = monthly_budget['spent_usd'] > monthly_budget['budget_usd']

        if exceeded:
            logger.error(
                f"Monthly budget exceeded by ${monthly_budget['spent_usd'] - monthly_budget['budget_usd']:.2f}"
            )

        return exceeded

    def can_process_document(self, doc_length_chars: int = 2000) -> tuple[bool, Optional[str]]:
        """
        Check if we can process a document within budget constraints

        Args:
            doc_length_chars: Estimated document length in characters

        Returns:
            Tuple of (can_process, reason_if_not)
        """
        # Check daily budget
        if self.is_daily_budget_exceeded():
            return False, "Daily budget already exceeded, stop processing"

        # Check if document cost would exceed per-doc limit
        doc_cost = self.cost_tracker.estimate_document_cost(doc_length_chars)
        max_cost_per_doc = self.config['MAX_COST_PER_DOC']

        if doc_cost['total_usd'] > max_cost_per_doc:
            logger.warning(
                f"Document cost ${doc_cost['total_usd']:.2f} exceeds limit ${max_cost_per_doc:.2f}, "
                f"context agent will be disabled"
            )

        # Check daily budget has room for this document
        daily_budget = self.check_budget('daily')
        if daily_budget['remaining_usd'] < doc_cost['total_usd']:
            return False, f"Insufficient daily budget: ${daily_budget['remaining_usd']:.2f} remaining, ${doc_cost['total_usd']:.2f} needed"

        return True, None

    def check_budget(self, time_period: str = 'daily') -> Dict[str, Any]:
        """
        Check budget status (wrapper around cost_tracker)

        Args:
            time_period: 'daily' or 'monthly'

        Returns:
            Budget status dict
        """
        return self.cost_tracker.check_budget(time_period)

    def get_recommendations(self) -> Dict[str, Any]:
        """
        Get cost optimization recommendations

        Returns:
            Dict with recommendations based on current spending patterns
        """
        daily_budget = self.check_budget('daily')
        monthly_budget = self.check_budget('monthly')

        recommendations = {
            'daily_status': 'OK' if daily_budget['percentage_used'] < 80 else 'WARNING' if daily_budget['percentage_used'] < 100 else 'CRITICAL',
            'monthly_status': 'OK' if monthly_budget['percentage_used'] < 80 else 'WARNING' if monthly_budget['percentage_used'] < 100 else 'CRITICAL',
            'actions': []
        }

        # Daily recommendations
        if daily_budget['percentage_used'] > 80:
            recommendations['actions'].append({
                'priority': 'HIGH',
                'action': 'Disable Claude Opus (context agent)',
                'reason': f"Daily budget {daily_budget['percentage_used']:.1f}% spent"
            })

        if daily_budget['percentage_used'] > 95:
            recommendations['actions'].append({
                'priority': 'CRITICAL',
                'action': 'Stop all Claude API calls',
                'reason': 'Daily budget nearly exceeded'
            })

        # Monthly recommendations
        if monthly_budget['percentage_used'] > 80:
            recommendations['actions'].append({
                'priority': 'HIGH',
                'action': 'Review monthly spending patterns',
                'reason': f"Monthly budget {monthly_budget['percentage_used']:.1f}% spent"
            })

        # Model-specific recommendations
        if 'claude-opus-4-5' in daily_budget['breakdown']:
            opus_cost = daily_budget['breakdown'].get('claude-opus-4-5', {}).get('cost', 0)
            if opus_cost > 50:  # If Opus is >$50 of daily budget
                recommendations['actions'].append({
                    'priority': 'MEDIUM',
                    'action': 'Consider reducing context agent frequency',
                    'reason': f"Claude Opus alone costs ${opus_cost:.2f} daily"
                })

        return recommendations

    def create_budget_report(self) -> str:
        """
        Create human-readable budget report

        Returns:
            Formatted budget report as string
        """
        daily = self.check_budget('daily')
        monthly = self.check_budget('monthly')

        report = []
        report.append("=" * 60)
        report.append("BUDGET REPORT")
        report.append("=" * 60)

        # Daily section
        report.append("\nDAILY BUDGET")
        report.append(f"  Budget:   ${daily['budget_usd']:.2f}")
        report.append(f"  Spent:    ${daily['spent_usd']:.2f}")
        report.append(f"  Remaining: ${daily['remaining_usd']:.2f}")
        report.append(f"  Usage:    {daily['percentage_used']:.1f}%")

        if daily['breakdown']:
            report.append("\n  By Model:")
            for model, costs in daily['breakdown'].items():
                report.append(f"    {model}: ${costs.get('cost', 0):.2f}")

        # Monthly section
        report.append("\nMONTHLY BUDGET")
        report.append(f"  Budget:   ${monthly['budget_usd']:.2f}")
        report.append(f"  Spent:    ${monthly['spent_usd']:.2f}")
        report.append(f"  Remaining: ${monthly['remaining_usd']:.2f}")
        report.append(f"  Usage:    {monthly['percentage_used']:.1f}%")

        if monthly['breakdown']:
            report.append("\n  By Model:")
            for model, costs in monthly['breakdown'].items():
                report.append(f"    {model}: ${costs.get('cost', 0):.2f}")

        # Recommendations
        recommendations = self.get_recommendations()
        if recommendations['actions']:
            report.append("\nRECOMMENDATIONS")
            for action in recommendations['actions']:
                report.append(f"  [{action['priority']}] {action['action']}")
                report.append(f"       Reason: {action['reason']}")

        # Alerts
        if daily['alert']:
            report.append(f"\nALERT: {daily['alert']}")
        if monthly['alert']:
            report.append(f"ALERT: {monthly['alert']}")

        report.append("\n" + "=" * 60)

        return "\n".join(report)
