"""Adaptive timeout configuration per tool"""

from typing import Dict

# Tool-specific timeout values (in seconds)
# Based on complexity and expected runtime
TOOL_TIMEOUTS: Dict[str, int] = {
    # Phase 1: Fast extraction tools (30s)
    "extract_document_type": 30,

    # Phase 1: Medium extraction tools (120s)
    "extract_people": 120,
    "extract_locations": 120,
    "extract_organizations": 120,

    # Phase 1: Slow structure parsing (180s)
    "parse_letter_body": 180,
    "parse_letter_structure": 180,

    # Phase 2: Content analysis (90-150s)
    "generate_summary": 120,
    "extract_keywords": 90,
    "classify_subjects": 90,
    "analyze_sentiment": 90,

    # Phase 3: Historical context (240s for Opus)
    "research_historical_context": 240,
    "generate_biographies": 240,
    "assess_significance": 240,
    "extract_relationships": 240,

    # Default timeout for unknown tools (120s)
    "_default": 120
}


def get_tool_timeout(tool_name: str, default_seconds: int = 120) -> int:
    """
    Get timeout for a specific tool

    Args:
        tool_name: Name of the tool
        default_seconds: Default timeout if tool not found

    Returns:
        Timeout in seconds
    """
    return TOOL_TIMEOUTS.get(tool_name, TOOL_TIMEOUTS.get("_default", default_seconds))


def get_phase_timeout(phase: int, tool_name: str) -> int:
    """
    Get timeout for a tool in a specific phase

    Phase 1 (extraction): Fast tools run in parallel
    Phase 2 (analysis): Slower tools run sequentially
    Phase 3 (context): Slowest tools with Claude Opus

    Args:
        phase: Pipeline phase (1, 2, or 3)
        tool_name: Name of the tool

    Returns:
        Timeout in seconds
    """
    tool_timeout = get_tool_timeout(tool_name)

    # Apply phase multipliers if needed
    # Phase 1: As-is (parallel execution)
    # Phase 2: As-is (sequential but faster)
    # Phase 3: As-is (uses Opus, can be slower)

    return tool_timeout
