"""
Schema validation and completeness checking for historical letters schema
"""

import json
import logging
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class HistoricalLettersValidator:
    """
    Validates enriched documents against historical letters schema
    Calculates completeness percentage and identifies missing fields
    """

    def __init__(self, schema_path: str):
        """
        Initialize validator with schema

        Args:
            schema_path: Path to JSON schema file
        """
        self.schema_path = schema_path
        self.schema: Dict[str, Any] = self._load_schema()
        self.required_fields: List[str] = self._extract_required_fields()

        logger.info(f"Schema validator initialized with {len(self.required_fields)} required fields")

    def _load_schema(self) -> Dict[str, Any]:
        """Load and parse schema JSON"""
        try:
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            logger.info(f"Loaded schema from {self.schema_path}")
            return schema
        except FileNotFoundError:
            logger.error(f"Schema file not found: {self.schema_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in schema: {e}")
            raise

    def _extract_required_fields(self, schema: Optional[Dict] = None, prefix: str = "") -> List[str]:
        """
        Recursively extract all required field paths from schema

        Returns list of field paths like:
            ['metadata.id', 'metadata.collection_id', 'document.date.creation_date', ...]
        """
        if schema is None:
            schema = self.schema

        required_fields = []

        if schema.get("type") == "object":
            required = schema.get("required", [])
            properties = schema.get("properties", {})

            for field in required:
                # Build full path
                field_path = f"{prefix}.{field}" if prefix else field
                required_fields.append(field_path)

                # Recurse into nested objects
                if field in properties:
                    nested_schema = properties[field]
                    if nested_schema.get("type") == "object":
                        nested_fields = self._extract_required_fields(
                            nested_schema,
                            prefix=field_path
                        )
                        required_fields.extend(nested_fields)

        return required_fields

    def validate(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate document against schema

        Args:
            document: Document to validate

        Returns:
            Validation result with errors
        """
        try:
            import jsonschema
            jsonschema.validate(instance=document, schema=self.schema)
            return {
                "valid": True,
                "errors": [],
                "warnings": []
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": []
            }

    def check_field_exists(self, data: Dict, field_path: str) -> Tuple[bool, Any]:
        """
        Check if a field path exists and has a non-empty value

        Args:
            data: Document to check
            field_path: Dot-separated field path (e.g., 'metadata.id')

        Returns:
            Tuple of (exists: bool, value: Any)
        """
        parts = field_path.split(".")
        current = data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False, None

        # Check if value is "empty"
        if current is None or current == "" or current == [] or current == {}:
            return False, None

        return True, current

    def calculate_completeness(self, enriched_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate completeness score and identify missing fields

        Args:
            enriched_data: Enriched document data

        Returns:
            Completeness report
        """
        present_fields = []
        missing_fields = []
        low_confidence_fields = []

        # Check each required field
        for field_path in self.required_fields:
            exists, value = self.check_field_exists(enriched_data, field_path)

            if exists:
                present_fields.append(field_path)

                # Check confidence score if available
                confidence_key = f"_confidence_{field_path}"
                has_confidence, confidence = self.check_field_exists(
                    enriched_data.get("_metadata", {}),
                    confidence_key
                )

                if has_confidence and confidence < 0.7:
                    low_confidence_fields.append({
                        "field": field_path,
                        "value": value if not isinstance(value, dict) else f"<{type(value).__name__}>",
                        "confidence": confidence
                    })
            else:
                missing_fields.append(field_path)

        # Calculate scores
        total_required = len(self.required_fields)
        total_present = len(present_fields)
        completeness_score = total_present / total_required if total_required > 0 else 0

        return {
            "completeness_score": round(completeness_score, 4),
            "total_required_fields": total_required,
            "present_fields": total_present,
            "missing_fields": missing_fields,
            "low_confidence_fields": low_confidence_fields,
            "passes_threshold": completeness_score >= 0.95,
            "requires_review": completeness_score < 0.95,
            "review_reason": self._get_review_reason(completeness_score, missing_fields, low_confidence_fields)
        }

    def _get_review_reason(
        self,
        score: float,
        missing: List[str],
        low_conf: List[Dict[str, Any]]
    ) -> str:
        """Generate human-readable review reason"""
        reasons = []

        if score < 0.95:
            reasons.append(f"Completeness score {score:.1%} below threshold")

        if len(missing) <= 5:
            reasons.append(f"Missing fields: {', '.join(missing)}")
        else:
            reasons.append(f"Missing {len(missing)} fields")

        if len(low_conf) > 0:
            low_conf_fields = [f["field"] for f in low_conf[:3]]
            reasons.append(f"Low confidence fields: {', '.join(low_conf_fields)}")

        return "; ".join(reasons)

    def generate_report(self, enriched_data: Dict[str, Any]) -> str:
        """
        Generate human-readable completeness report

        Args:
            enriched_data: Document to analyze

        Returns:
            Formatted report string
        """
        result = self.calculate_completeness(enriched_data)

        report = f"""
╔════════════════════════════════════════════════════════════╗
║           ENRICHMENT COMPLETENESS REPORT                   ║
╚════════════════════════════════════════════════════════════╝

Completeness Score: {result['completeness_score']:.1%}
Status: {'✓ PASS' if result['passes_threshold'] else '⚠ REVIEW REQUIRED'}

Fields Present:   {result['present_fields']}/{result['total_required_fields']}

{f"Missing Fields ({len(result['missing_fields'])}):" if result['missing_fields'] else ""}
{chr(10).join(f"  • {f}" for f in result['missing_fields'][:5]) if result['missing_fields'] else ""}
{f"  ... and {len(result['missing_fields']) - 5} more" if len(result['missing_fields']) > 5 else ""}

{f"Low Confidence Fields ({len(result['low_confidence_fields'])}):" if result['low_confidence_fields'] else ""}
{chr(10).join(f"  • {f['field']} (confidence: {f['confidence']:.1%})" for f in result['low_confidence_fields'][:3]) if result['low_confidence_fields'] else ""}

Review Reason: {result['review_reason']}
"""
        return report

    def get_summary_statistics(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary statistics for a batch of documents

        Args:
            documents: List of enriched documents

        Returns:
            Summary statistics
        """
        if not documents:
            return {
                "total_documents": 0,
                "avg_completeness": 0.0,
                "documents_passing": 0,
                "documents_requiring_review": 0,
                "most_common_missing_fields": []
            }

        results = [self.calculate_completeness(doc) for doc in documents]
        all_missing_fields: Dict[str, int] = {}

        for result in results:
            for field in result["missing_fields"]:
                all_missing_fields[field] = all_missing_fields.get(field, 0) + 1

        # Sort by frequency
        most_common = sorted(all_missing_fields.items(), key=lambda x: x[1], reverse=True)

        return {
            "total_documents": len(documents),
            "avg_completeness": round(
                sum(r["completeness_score"] for r in results) / len(results),
                4
            ),
            "min_completeness": round(min(r["completeness_score"] for r in results), 4),
            "max_completeness": round(max(r["completeness_score"] for r in results), 4),
            "documents_passing": sum(1 for r in results if r["passes_threshold"]),
            "documents_requiring_review": sum(1 for r in results if r["requires_review"]),
            "pass_rate": round(sum(1 for r in results if r["passes_threshold"]) / len(results), 4),
            "most_common_missing_fields": [f[0] for f in most_common[:10]],
            "missing_field_distribution": dict(most_common[:10])
        }


# Alias for import compatibility
SchemaValidator = HistoricalLettersValidator
