# Enrichment Service Tests

Comprehensive test suite for the MCP agent-based enrichment pipeline.

## Test Structure

```
tests/
├── conftest.py                    # Pytest fixtures and configuration
├── test_cost_tracking.py          # Cost tracking and budget management tests
├── test_integration.py            # End-to-end integration tests
├── pytest.ini                     # Pytest configuration
├── requirements-test.txt          # Testing dependencies
└── README.md                      # This file
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)

Fast, isolated tests for individual components:

- **test_cost_tracking.py**
  - `TestCostTracker`: Pricing, estimation, recording, retrieval
  - `TestBudgetManager`: Budget enforcement, recommendations
  - `TestCostAnalysis`: Cost calculations and breakdowns
  - `TestBudgetConstraints`: Daily/monthly limits
  - `TestMetricsIntegration`: Cost tracking with metrics

### Integration Tests (`@pytest.mark.integration`)

Multi-component tests with realistic scenarios:

- **test_integration.py**
  - `TestEnrichmentPipeline`: Complete enrichment workflow
  - `TestSampleLetterProcessing`: Real historical letter processing
  - `TestDataMapper`: OCR + enriched data merging
  - `TestEndToEndScenarios`: Full pipeline scenarios
  - `TestErrorHandling`: Error cases and recovery

## Setup

### Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### Install Development Dependencies

```bash
pip install -r ../requirements.txt
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run by Category

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests only (slower)
pytest -m integration

# Exclude slow tests
pytest -m "not slow"
```

### Run Specific Test File

```bash
pytest test_cost_tracking.py
```

### Run Specific Test Class

```bash
pytest test_cost_tracking.py::TestCostTracker
```

### Run Specific Test

```bash
pytest test_cost_tracking.py::TestCostTracker::test_estimate_task_cost
```

### Parallel Execution (faster)

```bash
pytest -n auto  # Uses all CPU cores
```

### Verbose Output

```bash
pytest -v          # Verbose
pytest -vv         # Very verbose with full diffs
```

### With Coverage Report

```bash
pytest --cov=enrichment_service --cov-report=html
# Open htmlcov/index.html in browser
```

### With Timeout

```bash
pytest --timeout=30  # 30 second timeout per test
```

## Test Fixtures

All fixtures are defined in `conftest.py`:

### Database Fixtures

- `mock_db`: Mock MongoDB database with test collections
- `mock_config`: Test configuration

### Client Fixtures

- `mock_mcp_client`: Mock MCP client for agent communication

### Data Fixtures

- `sample_ocr_data`: Typical OCR output from a letter
- `sample_enriched_data`: Complete enriched letter data
- `sample_collection_metadata`: Collection-level metadata
- `historical_letter_sample_1`: Invitation letter sample
- `historical_letter_sample_2`: Personal letter sample

### Component Fixtures

- `cost_tracker_fixture`: Initialized CostTracker
- `budget_manager_fixture`: Initialized BudgetManager
- `review_queue_fixture`: Initialized ReviewQueue

## Test Examples

### Testing Cost Estimation

```python
def test_estimate_document_cost(self, cost_tracker_fixture):
    estimate = cost_tracker_fixture.estimate_document_cost(
        doc_length_chars=2000,
        enable_context_agent=True
    )

    assert estimate['total_usd'] > 0
    assert estimate['phase1_ollama'] == 0.0  # Free
    assert estimate['phase2_sonnet'] > 0
    assert estimate['phase3_opus'] > 0
```

### Testing Budget Enforcement

```python
def test_should_disable_context_agent(self, budget_manager_fixture):
    should_enable = budget_manager_fixture.should_enable_context_agent()
    assert should_enable is True  # When within budget

    # After spending 85% of daily budget
    # should_enable would be False
```

### Testing Review Queue Workflow

```python
def test_review_workflow(self, review_queue_fixture):
    # Create review task
    review_id = review_queue_fixture.create_task(...)

    # Assign to reviewer
    review_queue_fixture.assign_task(review_id, 'reviewer_001')

    # Approve with corrections
    review_queue_fixture.approve_task(review_id, 'reviewer_001', ...)
```

## Continuous Integration

Tests are designed to work in CI environments:

1. **No External Dependencies**: Uses mock database (mongomock)
2. **Async Support**: pytest-asyncio for async tests
3. **Parallel Execution**: Tests can run in parallel with `-n auto`
4. **Coverage Reports**: Generates HTML coverage reports

### CI Pipeline Example

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - run: pip install -r requirements-test.txt
      - run: pytest --cov=enrichment_service --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Coverage Goals

- **Unit Tests**: >90% coverage of core logic
- **Integration Tests**: >70% coverage of workflows
- **Overall**: >80% coverage target

Current coverage status can be checked with:

```bash
pytest --cov=enrichment_service --cov-report=term-missing
```

## Debugging Tests

### Print Debug Info

```python
def test_something(self):
    result = function_to_test()
    print(result)  # Will show with pytest -s
    assert result == expected
```

Run with `-s` to see print statements:

```bash
pytest -s
```

### Use PDB Debugger

```python
def test_something(self):
    import pdb; pdb.set_trace()  # Breakpoint
    result = function_to_test()
```

Run and interact:

```bash
pytest --pdb
```

### Log Inspection

```bash
# View test logs
cat test_results.log
```

## Common Issues

### MongoDB Connection Errors

Tests use mongomock (in-memory database). If you see MongoDB errors:
- Ensure you're using the `mock_db` fixture
- Don't create real MongoDB connections in tests

### Async Test Failures

If async tests fail:
- Ensure pytest-asyncio is installed
- Mark async tests with `@pytest.mark.asyncio`
- Use `async def` for test functions

### Import Errors

If imports fail:
- Ensure enrichment_service is in PYTHONPATH
- Run tests from project root directory
- Check sys.path includes enrichment_service package

## Performance Optimization

### Skip Slow Tests During Development

```bash
pytest -m "not slow"
```

### Run Tests in Parallel

```bash
pytest -n 4  # Use 4 processes
```

### Only Run Changed Tests

```bash
pytest --lf  # Last failed
pytest --ff  # Failed first
```

## Adding New Tests

1. Create test file: `test_component.py`
2. Add marker: `@pytest.mark.unit` or `@pytest.mark.integration`
3. Use fixtures from `conftest.py`
4. Run to verify: `pytest test_component.py`
5. Check coverage: `pytest --cov`

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [mongomock](https://github.com/mongomock/mongomock)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
