"""
Cost Reporter - Generates cost analysis and reports

Creates detailed reports on enrichment costs, ROI, and optimization opportunities
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from enrichment_service.utils.cost_tracker import CostTracker
from enrichment_service.utils.budget_manager import BudgetManager

logger = logging.getLogger(__name__)


class CostReporter:
    """
    Generates comprehensive cost analysis and reports
    """

    def __init__(self, db=None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize CostReporter

        Args:
            db: MongoDB database instance
            config: Optional configuration dict
        """
        self.cost_tracker = CostTracker(db, config)
        self.budget_manager = BudgetManager(db, config)
        self.db = db

    def get_enrichment_summary(self, enrichment_job_id: str) -> Dict[str, Any]:
        """
        Get summary report for single enrichment job

        Args:
            enrichment_job_id: ID of enrichment job

        Returns:
            Summary dict with costs, efficiency metrics, etc.
        """
        job_costs = self.cost_tracker.get_job_costs(enrichment_job_id)

        if self.db:
            # Get job metadata
            job = self.db.enrichment_jobs.find_one({'_id': enrichment_job_id})
            if job:
                total_docs = job.get('total_documents', 0)
                success_count = job.get('success_count', 0)
                review_count = job.get('review_count', 0)

                # Calculate efficiency
                auto_approve_rate = (success_count - review_count) / total_docs if total_docs > 0 else 0

                return {
                    'enrichment_job_id': enrichment_job_id,
                    'total_documents': total_docs,
                    'processed_documents': job_costs.get('num_documents', 0),
                    'success_count': success_count,
                    'review_count': review_count,
                    'auto_approve_rate': auto_approve_rate,
                    'total_cost_usd': job_costs.get('total_cost_usd', 0.0),
                    'cost_per_document': job_costs.get('cost_per_document', 0.0),
                    'cost_breakdown_by_model': job_costs.get('breakdown_by_model', {}),
                    'total_api_calls': job_costs.get('api_calls', 0),
                    'status': job.get('status', 'unknown'),
                    'created_at': job.get('created_at'),
                    'completed_at': job.get('completed_at')
                }

        return job_costs

    def get_document_efficiency(self, document_id: str) -> Dict[str, Any]:
        """
        Analyze cost efficiency for single document enrichment

        Args:
            document_id: Document ID

        Returns:
            Efficiency analysis dict
        """
        doc_costs = self.cost_tracker.get_document_costs(document_id)

        if self.db:
            # Get enriched document quality metrics
            doc = self.db.enriched_documents.find_one({'_id': document_id})
            if doc:
                quality = doc.get('quality_metrics', {})
                completeness = quality.get('completeness_score', 0.0)
                cost_per_completeness = doc_costs.get('total_cost_usd', 0.0) / completeness if completeness > 0 else 0

                return {
                    'document_id': document_id,
                    'total_cost_usd': doc_costs.get('total_cost_usd', 0.0),
                    'total_tokens': doc_costs.get('total_tokens', 0),
                    'completeness_score': completeness,
                    'cost_per_percentage_complete': cost_per_completeness,
                    'review_required': quality.get('missing_fields', []) != [],
                    'missing_fields_count': len(quality.get('missing_fields', [])),
                    'api_calls': doc_costs.get('api_calls', 0),
                    'breakdown_by_task': doc_costs.get('breakdown_by_task', {}),
                    'cost_per_api_call': (doc_costs.get('total_cost_usd', 0.0) / doc_costs.get('api_calls', 1)) if doc_costs.get('api_calls', 0) > 0 else 0
                }

        return doc_costs

    def get_model_analysis(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Analyze costs by model across time period

        Args:
            start_date: Start of analysis period (default: 30 days ago)
            end_date: End of analysis period (default: today)

        Returns:
            Model-level cost analysis
        """
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        if self.db is None:
            return {}

        try:
            records = list(self.db.cost_records.find({
                'timestamp': {'$gte': start_date, '$lt': end_date}
            }))

            analysis_by_model = defaultdict(lambda: {
                'total_cost': 0.0,
                'total_tokens': 0,
                'api_calls': 0,
                'tasks': defaultdict(int),
                'avg_cost_per_call': 0.0
            })

            for record in records:
                model = record.get('model', 'unknown')
                cost = record.get('cost_usd', 0.0)
                tokens = record.get('total_tokens', 0)
                task = record.get('task_name', 'unknown')

                analysis_by_model[model]['total_cost'] += cost
                analysis_by_model[model]['total_tokens'] += tokens
                analysis_by_model[model]['api_calls'] += 1
                analysis_by_model[model]['tasks'][task] += 1

            # Calculate averages
            result = {}
            for model, data in analysis_by_model.items():
                data['avg_cost_per_call'] = data['total_cost'] / data['api_calls'] if data['api_calls'] > 0 else 0
                data['avg_tokens_per_call'] = data['total_tokens'] / data['api_calls'] if data['api_calls'] > 0 else 0
                result[model] = dict(data)

            return {
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'by_model': result,
                'total_cost': sum(m['total_cost'] for m in analysis_by_model.values()),
                'total_tokens': sum(m['total_tokens'] for m in analysis_by_model.values()),
                'total_api_calls': sum(m['api_calls'] for m in analysis_by_model.values())
            }

        except Exception as e:
            logger.error(f"Error analyzing models: {e}")
            return {}

    def get_cost_trends(self, days: int = 30) -> Dict[str, Any]:
        """
        Analyze cost trends over time

        Args:
            days: Number of days to analyze

        Returns:
            Daily cost trend analysis
        """
        if self.db is None:
            return {}

        try:
            trends = []
            end_date = datetime.utcnow()

            for i in range(days):
                current_date = end_date - timedelta(days=i)
                daily_costs = self.cost_tracker.get_daily_costs(current_date)

                trends.append({
                    'date': current_date.isoformat().split('T')[0],
                    'cost_usd': daily_costs.get('total_cost_usd', 0.0),
                    'api_calls': daily_costs.get('api_calls', 0),
                    'tokens': daily_costs.get('total_tokens', 0),
                    'models': daily_costs.get('breakdown_by_model', {})
                })

            # Calculate statistics
            costs = [t['cost_usd'] for t in trends]
            avg_daily_cost = sum(costs) / len(costs) if costs else 0
            max_daily_cost = max(costs) if costs else 0
            min_daily_cost = min(c for c in costs if c > 0) if any(c > 0 for c in costs) else 0

            return {
                'period_days': days,
                'daily_trends': trends,
                'statistics': {
                    'average_daily_cost': avg_daily_cost,
                    'max_daily_cost': max_daily_cost,
                    'min_daily_cost': min_daily_cost,
                    'projected_monthly_cost': avg_daily_cost * 30,
                    'projected_yearly_cost': avg_daily_cost * 365
                }
            }

        except Exception as e:
            logger.error(f"Error analyzing trends: {e}")
            return {}

    def get_optimization_opportunities(self) -> List[Dict[str, Any]]:
        """
        Identify cost optimization opportunities

        Returns:
            List of optimization recommendations
        """
        opportunities = []

        if self.db is None:
            return opportunities

        try:
            # Analyze last 7 days
            model_analysis = self.get_model_analysis(
                start_date=datetime.utcnow() - timedelta(days=7)
            )

            # Opportunity 1: High-cost tasks
            by_model = model_analysis.get('by_model', {})
            for model, data in by_model.items():
                if model.startswith('claude-opus'):
                    total_cost = data.get('total_cost', 0)
                    if total_cost > 50:  # If Opus >$50/week
                        opportunities.append({
                            'type': 'model_usage',
                            'severity': 'medium',
                            'title': f"High Claude Opus usage",
                            'description': f"Claude Opus costs ${total_cost:.2f}/week. Consider using Claude Sonnet for some tasks.",
                            'potential_savings': total_cost * 0.8,  # Assuming 80% savings with Sonnet
                            'action': 'Review context-agent frequency or consider lower-cost alternatives'
                        })

            # Opportunity 2: Low completeness despite high cost
            records = list(self.db.cost_records.find({
                'timestamp': {'$gte': datetime.utcnow() - timedelta(days=7)}
            }))

            # Opportunity 3: Inefficient agents (many calls for little benefit)
            tasks_count = defaultdict(int)
            tasks_cost = defaultdict(float)
            for record in records:
                task = record.get('task_name', 'unknown')
                tasks_count[task] += 1
                tasks_cost[task] += record.get('cost_usd', 0.0)

            for task, count in tasks_count.items():
                if count > 100 and tasks_cost[task] > 10:
                    avg_cost = tasks_cost[task] / count
                    if avg_cost > 0.20:
                        opportunities.append({
                            'type': 'inefficient_task',
                            'severity': 'low',
                            'title': f"High average cost for {task}",
                            'description': f"Task {task} costs ${avg_cost:.4f} per call on average.",
                            'potential_savings': tasks_cost[task] * 0.3,
                            'action': f"Consider optimizing {task} or using faster model"
                        })

            return opportunities

        except Exception as e:
            logger.error(f"Error identifying opportunities: {e}")
            return []

    def generate_report(self, enrichment_job_id: Optional[str] = None) -> str:
        """
        Generate comprehensive cost report

        Args:
            enrichment_job_id: Optional specific job to report on

        Returns:
            Formatted report as string
        """
        report = []
        report.append("\n" + "=" * 70)
        report.append("ENRICHMENT COST REPORT")
        report.append("=" * 70)
        report.append(f"Generated: {datetime.utcnow().isoformat()}\n")

        if enrichment_job_id:
            # Single job report
            job_summary = self.get_enrichment_summary(enrichment_job_id)
            report.append(f"JOB SUMMARY: {enrichment_job_id}")
            report.append("-" * 70)
            report.append(f"Documents Processed: {job_summary.get('processed_documents', 0)}")
            report.append(f"Success Rate: {(job_summary.get('success_count', 0) / job_summary.get('total_documents', 1)) * 100:.1f}%")
            report.append(f"Auto-Approve Rate: {job_summary.get('auto_approve_rate', 0) * 100:.1f}%")
            report.append(f"Total Cost: ${job_summary.get('total_cost_usd', 0):.2f}")
            report.append(f"Cost per Document: ${job_summary.get('cost_per_document', 0):.2f}")
            report.append(f"API Calls: {job_summary.get('total_api_calls', 0)}\n")

            # Model breakdown
            breakdown = job_summary.get('cost_breakdown_by_model', {})
            if breakdown:
                report.append("Cost by Model:")
                for model, costs in breakdown.items():
                    report.append(f"  {model}: ${costs.get('cost', 0):.2f}")

        else:
            # Overall report
            budget = self.budget_manager.check_budget('daily')
            trends = self.get_cost_trends(7)

            report.append("DAILY BUDGET STATUS")
            report.append("-" * 70)
            report.append(f"Budget: ${budget['budget_usd']:.2f}")
            report.append(f"Spent: ${budget['spent_usd']:.2f}")
            report.append(f"Usage: {budget['percentage_used']:.1f}%\n")

            # 7-day trends
            stats = trends.get('statistics', {})
            report.append("7-DAY TRENDS")
            report.append("-" * 70)
            report.append(f"Average Daily Cost: ${stats.get('average_daily_cost', 0):.2f}")
            report.append(f"Max Daily Cost: ${stats.get('max_daily_cost', 0):.2f}")
            report.append(f"Projected Monthly: ${stats.get('projected_monthly_cost', 0):.2f}\n")

            # Model analysis
            model_analysis = self.get_model_analysis()
            by_model = model_analysis.get('by_model', {})
            if by_model:
                report.append("MODEL USAGE (Last 30 days)")
                report.append("-" * 70)
                for model, data in by_model.items():
                    report.append(f"{model}:")
                    report.append(f"  Cost: ${data.get('total_cost', 0):.2f}")
                    report.append(f"  Calls: {data.get('api_calls', 0)}")
                    report.append(f"  Avg Cost/Call: ${data.get('avg_cost_per_call', 0):.4f}")

            # Opportunities
            opportunities = self.get_optimization_opportunities()
            if opportunities:
                report.append("\nCOST OPTIMIZATION OPPORTUNITIES")
                report.append("-" * 70)
                for opp in opportunities:
                    report.append(f"[{opp['severity'].upper()}] {opp['title']}")
                    report.append(f"  Potential Savings: ${opp.get('potential_savings', 0):.2f}")
                    report.append(f"  Action: {opp['action']}\n")

        report.append("=" * 70)
        return "\n".join(report)
