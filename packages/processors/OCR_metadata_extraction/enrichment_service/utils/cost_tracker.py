"""
Cost Tracker - Tracks API costs and token usage for enrichment pipeline

Monitors costs for Claude API calls (Opus, Sonnet, Haiku)
Logs Ollama usage (free) for comparison
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

logger = logging.getLogger(__name__)


class CostTracker:
    """
    Tracks costs and token usage for enrichment operations

    Claude API pricing (as of 2025-01-17):
    - Claude Opus 4.5: $15/$75 per 1M tokens (input/output)
    - Claude Sonnet 4: $3/$15 per 1M tokens (input/output)
    - Claude Haiku 4: $0.25/$1.25 per 1M tokens (input/output)
    - Ollama: Free (local)
    """

    # Updated pricing in USD per 1M tokens
    PRICING = {
        'claude-opus-4-5': {'input': 15.00, 'output': 75.00},
        'claude-sonnet-4': {'input': 3.00, 'output': 15.00},
        'claude-haiku-4': {'input': 0.25, 'output': 1.25},
        'ollama': {'input': 0.0, 'output': 0.0}
    }

    # Typical token estimates per operation (for cost estimation)
    TASK_TOKEN_ESTIMATES = {
        # Phase 1 - Ollama (free)
        'extract_document_type': {'model': 'ollama', 'input': 800, 'output': 300},
        'extract_storage_info': {'model': 'ollama', 'input': 900, 'output': 250},
        'extract_digitization_metadata': {'model': 'ollama', 'input': 700, 'output': 200},
        'determine_access_level': {'model': 'ollama', 'input': 800, 'output': 150},

        # Phase 1 - Entity extraction (Ollama + optional Claude)
        'extract_people': {'model': 'ollama', 'input': 1000, 'output': 300},
        'extract_organizations': {'model': 'ollama', 'input': 1000, 'output': 250},
        'extract_locations': {'model': 'ollama', 'input': 900, 'output': 250},
        'extract_events': {'model': 'ollama', 'input': 900, 'output': 300},
        'generate_relationships': {'model': 'ollama', 'input': 1200, 'output': 400},

        # Phase 1 - Structure (Ollama)
        'extract_salutation': {'model': 'ollama', 'input': 800, 'output': 100},
        'parse_letter_body': {'model': 'ollama', 'input': 2000, 'output': 500},
        'extract_closing': {'model': 'ollama', 'input': 800, 'output': 100},
        'extract_signature': {'model': 'ollama', 'input': 800, 'output': 150},
        'identify_attachments': {'model': 'ollama', 'input': 900, 'output': 200},
        'parse_correspondence': {'model': 'ollama', 'input': 1500, 'output': 400},

        # Phase 2 - Content (Claude Sonnet)
        'generate_summary': {'model': 'claude-sonnet-4', 'input': 1200, 'output': 400},
        'extract_keywords': {'model': 'ollama', 'input': 900, 'output': 300},
        'classify_subjects': {'model': 'ollama', 'input': 1000, 'output': 250},

        # Phase 3 - Context (Claude Opus)
        'research_historical_context': {'model': 'claude-opus-4-5', 'input': 2500, 'output': 1500},
        'assess_significance': {'model': 'claude-opus-4-5', 'input': 2000, 'output': 800},
        'generate_biographies': {'model': 'claude-opus-4-5', 'input': 1800, 'output': 800},

        # Optional Claude disambiguation
        'disambiguate_entities': {'model': 'claude-haiku-4', 'input': 1500, 'output': 400}
    }

    def __init__(self, db=None, config: Optional[Dict[str, Any]] = None):
        """
        Initialize CostTracker

        Args:
            db: MongoDB database instance
            config: Optional configuration dict
        """
        self.db = db
        self.config = config or self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        return {
            'MONGO_URI': os.getenv('MONGO_URI', 'mongodb://localhost:27017/gvpocr'),
            'DB_NAME': os.getenv('DB_NAME', 'gvpocr'),
            'MAX_COST_PER_DOC': float(os.getenv('MAX_COST_PER_DOC', '0.50')),
            'DAILY_BUDGET_USD': float(os.getenv('DAILY_BUDGET_USD', '100.00')),
            'MONTHLY_BUDGET_USD': float(os.getenv('MONTHLY_BUDGET_USD', '2000.00')),
            'COST_ALERT_THRESHOLD': float(os.getenv('COST_ALERT_THRESHOLD', '80.00'))
        }

    def estimate_task_cost(self, task_name: str) -> Dict[str, Any]:
        """
        Estimate cost for a single task using Decimal for precision

        Args:
            task_name: Name of the task (e.g., 'generate_summary')

        Returns:
            Dict with estimated cost breakdown
        """
        if task_name not in self.TASK_TOKEN_ESTIMATES:
            logger.warning(f"Unknown task {task_name}, returning zero cost")
            return {'estimated_usd': 0.0, 'model': 'unknown'}

        task_info = self.TASK_TOKEN_ESTIMATES[task_name]
        model = task_info.get('model', 'ollama')
        input_tokens = task_info.get('input', 0)
        output_tokens = task_info.get('output', 0)

        if model not in self.PRICING:
            return {'estimated_usd': 0.0, 'model': model}

        pricing = self.PRICING[model]

        # Use Decimal for precise financial calculation to avoid floating point errors
        input_cost = (Decimal(input_tokens) / Decimal('1000000')) * Decimal(str(pricing['input']))
        output_cost = (Decimal(output_tokens) / Decimal('1000000')) * Decimal(str(pricing['output']))
        total_cost = input_cost + output_cost

        # Convert back to float with rounding to 6 decimal places (precision to 0.000001 USD)
        cost_usd = float(total_cost.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP))

        return {
            'estimated_usd': cost_usd,
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens
        }

    def estimate_document_cost(self, doc_length_chars: int = 2000, enable_context_agent: bool = True) -> Dict[str, Any]:
        """
        Estimate total cost for enriching one document

        Args:
            doc_length_chars: Approximate document length in characters (default: 2000)
            enable_context_agent: Whether to include expensive context agent (Claude Opus)

        Returns:
            Cost estimation dict
        """
        # Phase 1: Ollama agents (free)
        phase1_cost = 0.0

        # Phase 2: Claude Sonnet for summary
        summary_cost = self.estimate_task_cost('generate_summary')
        phase2_cost = summary_cost.get('estimated_usd', 0.0)

        # Phase 3: Claude Opus for context (optional)
        phase3_cost = 0.0
        if enable_context_agent:
            context_cost = self.estimate_task_cost('research_historical_context')
            bio_cost = self.estimate_task_cost('generate_biographies')
            phase3_cost = (
                context_cost.get('estimated_usd', 0.0) +
                bio_cost.get('estimated_usd', 0.0)
            )

        total_cost = phase1_cost + phase2_cost + phase3_cost

        return {
            'phase1_ollama': phase1_cost,
            'phase2_sonnet': phase2_cost,
            'phase3_opus': phase3_cost,
            'total_usd': total_cost,
            'document_length_chars': doc_length_chars,
            'context_agent_enabled': enable_context_agent,
            'breakdown': {
                'ollama': phase1_cost,
                'claude_sonnet': phase2_cost,
                'claude_opus': phase3_cost
            }
        }

    def estimate_collection_cost(
        self,
        num_documents: int,
        avg_doc_length: int = 2000,
        enable_context_agent: bool = True
    ) -> Dict[str, Any]:
        """
        Estimate total cost for enriching collection

        Args:
            num_documents: Number of documents to process
            avg_doc_length: Average document length in characters
            enable_context_agent: Whether to include context agent

        Returns:
            Collection-level cost estimation
        """
        single_doc_cost = self.estimate_document_cost(avg_doc_length, enable_context_agent)
        total_cost = single_doc_cost['total_usd'] * num_documents

        return {
            'num_documents': num_documents,
            'cost_per_document': single_doc_cost['total_usd'],
            'total_cost_usd': total_cost,
            'daily_estimate': min(total_cost, 100),  # Assuming ~100/day batch
            'monthly_estimate': min(total_cost * 30, 2000),
            'breakdown_per_doc': single_doc_cost['breakdown'],
            'breakdown_total': {
                'ollama': single_doc_cost['breakdown']['ollama'] * num_documents,
                'claude_sonnet': single_doc_cost['breakdown']['claude_sonnet'] * num_documents,
                'claude_opus': single_doc_cost['breakdown']['claude_opus'] * num_documents
            }
        }

    def record_api_call(
        self,
        enrichment_job_id: str,
        document_id: str,
        model: str,
        task_name: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float
    ) -> bool:
        """
        Record actual API call with token usage and cost

        Args:
            enrichment_job_id: Parent enrichment job ID
            document_id: Document being processed
            model: Model used (claude-opus-4-5, claude-sonnet-4, ollama, etc.)
            task_name: Task name (generate_summary, research_historical_context, etc.)
            input_tokens: Actual input tokens
            output_tokens: Actual output tokens
            cost_usd: Actual cost in USD

        Returns:
            True if recorded successfully
        """
        if self.db is None:
            logger.warning(f"Database connection not available, cost record cannot be saved")
            return False

        # Validate database connection before use
        try:
            self.db.client.admin.command('ping')
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False

        try:
            record = {
                'enrichment_job_id': enrichment_job_id,
                'document_id': document_id,
                'model': model,
                'task_name': task_name,
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': input_tokens + output_tokens,
                'cost_usd': cost_usd,
                'timestamp': datetime.utcnow()
            }

            self.db.cost_records.insert_one(record)
            logger.debug(f"Recorded cost: {cost_usd:.4f} USD for {task_name}")

            return True

        except ConnectionFailure as e:
            logger.error(f"Database connection lost while recording cost: {e}")
            return False
        except Exception as e:
            logger.error(f"Error recording API call: {e}", exc_info=True)
            return False

    def get_document_costs(self, document_id: str) -> Dict[str, Any]:
        """
        Get all costs associated with enriching a document

        Args:
            document_id: Document ID

        Returns:
            Dict with cost breakdown by model and task
        """
        if self.db is None:
            logger.warning("Database not available, cannot retrieve document costs")
            return {}

        try:
            # Validate database connection
            self.db.client.admin.command('ping')

            records = list(self.db.cost_records.find({'document_id': document_id}))

            breakdown_by_model = {}
            breakdown_by_task = {}
            total_cost = 0.0
            total_tokens = 0

            for record in records:
                model = record.get('model', 'unknown')
                task = record.get('task_name', 'unknown')
                cost = record.get('cost_usd', 0.0)
                tokens = record.get('total_tokens', 0)

                # Aggregate by model
                if model not in breakdown_by_model:
                    breakdown_by_model[model] = {'cost': 0.0, 'tokens': 0}
                breakdown_by_model[model]['cost'] += cost
                breakdown_by_model[model]['tokens'] += tokens

                # Aggregate by task
                if task not in breakdown_by_task:
                    breakdown_by_task[task] = {'cost': 0.0, 'tokens': 0}
                breakdown_by_task[task]['cost'] += cost
                breakdown_by_task[task]['tokens'] += tokens

                total_cost += cost
                total_tokens += tokens

            return {
                'document_id': document_id,
                'total_cost_usd': total_cost,
                'total_tokens': total_tokens,
                'breakdown_by_model': breakdown_by_model,
                'breakdown_by_task': breakdown_by_task,
                'api_calls': len(records)
            }

        except ConnectionFailure as e:
            logger.error(f"Database connection failed retrieving document costs: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error getting document costs: {e}", exc_info=True)
            return {}

    def get_job_costs(self, enrichment_job_id: str) -> Dict[str, Any]:
        """
        Get all costs for an enrichment job

        Args:
            enrichment_job_id: Enrichment job ID

        Returns:
            Job-level cost summary
        """
        if self.db is None:
            logger.warning("Database not available, cannot retrieve job costs")
            return {}

        try:
            # Validate database connection
            self.db.client.admin.command('ping')

            records = list(self.db.cost_records.find({'enrichment_job_id': enrichment_job_id}))

            if not records:
                return {
                    'enrichment_job_id': enrichment_job_id,
                    'total_cost_usd': 0.0,
                    'total_tokens': 0,
                    'num_documents': 0
                }

            breakdown_by_model = {}
            total_cost = 0.0
            total_tokens = 0
            documents_processed = set()

            for record in records:
                model = record.get('model', 'unknown')
                cost = record.get('cost_usd', 0.0)
                tokens = record.get('total_tokens', 0)
                doc_id = record.get('document_id')

                if model not in breakdown_by_model:
                    breakdown_by_model[model] = {'cost': 0.0, 'tokens': 0}
                breakdown_by_model[model]['cost'] += cost
                breakdown_by_model[model]['tokens'] += tokens

                total_cost += cost
                total_tokens += tokens
                documents_processed.add(doc_id)

            return {
                'enrichment_job_id': enrichment_job_id,
                'total_cost_usd': total_cost,
                'total_tokens': total_tokens,
                'num_documents': len(documents_processed),
                'cost_per_document': total_cost / len(documents_processed) if documents_processed else 0.0,
                'breakdown_by_model': breakdown_by_model,
                'api_calls': len(records)
            }

        except ConnectionFailure as e:
            logger.error(f"Database connection failed retrieving job costs: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error getting job costs: {e}", exc_info=True)
            return {}

    def get_daily_costs(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get costs for a specific day

        Args:
            date: Date to query (default: today UTC). Should be timezone-aware or UTC.

        Returns:
            Daily cost summary
        """
        if self.db is None:
            logger.warning("Database not available, cannot retrieve daily costs")
            return {}

        if date is None:
            date = datetime.now(timezone.utc)
        elif date.tzinfo is None:
            # If timezone-naive, assume UTC
            date = date.replace(tzinfo=timezone.utc)

        try:
            # Validate database connection
            self.db.client.admin.command('ping')

            # Get start and end of day (in UTC)
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
            end_of_day = start_of_day + timedelta(days=1)

            records = list(self.db.cost_records.find({
                'timestamp': {'$gte': start_of_day, '$lt': end_of_day}
            }))

            if not records:
                return {
                    'date': start_of_day.isoformat(),
                    'total_cost_usd': 0.0,
                    'total_tokens': 0
                }

            breakdown_by_model = {}
            total_cost = 0.0
            total_tokens = 0

            for record in records:
                model = record.get('model', 'unknown')
                cost = record.get('cost_usd', 0.0)
                tokens = record.get('total_tokens', 0)

                if model not in breakdown_by_model:
                    breakdown_by_model[model] = {'cost': 0.0, 'tokens': 0}
                breakdown_by_model[model]['cost'] += cost
                breakdown_by_model[model]['tokens'] += tokens

                total_cost += cost
                total_tokens += tokens

            return {
                'date': start_of_day.isoformat(),
                'total_cost_usd': total_cost,
                'total_tokens': total_tokens,
                'breakdown_by_model': breakdown_by_model,
                'api_calls': len(records)
            }

        except ConnectionFailure as e:
            logger.error(f"Database connection failed retrieving daily costs: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error getting daily costs: {e}", exc_info=True)
            return {}

    def check_budget(self, time_period: str = 'daily') -> Dict[str, Any]:
        """
        Check budget status and alerts

        Args:
            time_period: 'daily' or 'monthly'

        Returns:
            Budget status dict
        """
        if time_period == 'daily':
            costs = self.get_daily_costs()
            budget = self.config['DAILY_BUDGET_USD']
        elif time_period == 'monthly':
            # Get costs for current month
            today = datetime.utcnow()
            start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            try:
                if self.db is not None:
                    # Validate database connection
                    self.db.client.admin.command('ping')

                    records = list(self.db.cost_records.find({
                        'timestamp': {'$gte': start_of_month}
                    }))

                    breakdown_by_model = {}
                    total_cost = 0.0
                    for record in records:
                        model = record.get('model', 'unknown')
                        cost = record.get('cost_usd', 0.0)
                        if model not in breakdown_by_model:
                            breakdown_by_model[model] = 0.0
                        breakdown_by_model[model] += cost
                        total_cost += cost

                    costs = {
                        'total_cost_usd': total_cost,
                        'breakdown_by_model': breakdown_by_model
                    }
                else:
                    costs = {'total_cost_usd': 0.0}
            except ConnectionFailure as e:
                logger.error(f"Database connection failed checking monthly budget: {e}")
                costs = {'total_cost_usd': 0.0}
            except Exception as e:
                logger.error(f"Error checking monthly budget: {e}", exc_info=True)
                costs = {'total_cost_usd': 0.0}

            budget = self.config['MONTHLY_BUDGET_USD']
        else:
            return {'error': 'Invalid time_period'}

        total_spent = costs.get('total_cost_usd', 0.0)
        remaining = budget - total_spent
        percentage_used = (total_spent / budget * 100) if budget > 0 else 0

        alert = None
        if total_spent > budget:
            alert = f"CRITICAL: Budget exceeded by ${total_spent - budget:.2f}"
        elif total_spent > self.config['COST_ALERT_THRESHOLD']:
            alert = f"WARNING: Spent ${total_spent:.2f} (${budget - total_spent:.2f} remaining)"

        return {
            'time_period': time_period,
            'budget_usd': budget,
            'spent_usd': total_spent,
            'remaining_usd': remaining,
            'percentage_used': percentage_used,
            'alert': alert,
            'breakdown': costs.get('breakdown_by_model', {})
        }
