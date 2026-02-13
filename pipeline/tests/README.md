# Pipeline Tests

Comprehensive test suite for the Pegasus Lecture Copilot pipeline.

## Running Tests

### All Tests

```bash
# From project root
pytest pipeline/tests -v

# With coverage
pytest pipeline/tests --cov=pipeline --cov-report=html
```

### Specific Test Files

```bash
# Schema validator tests
pytest pipeline/tests/test_schema_validator.py -v

# Progress tracker tests
pytest pipeline/tests/test_progress_tracker.py -v

# Retry utilities tests
pytest pipeline/tests/test_retry_utils.py -v

# Content templates tests
pytest pipeline/tests/test_content_templates.py -v

# Integration tests
pytest pipeline/tests/test_integration.py -v
```

### Specific Tests

```bash
# Run a specific test
pytest pipeline/tests/test_retry_utils.py::test_with_retry_success_first_attempt -v

# Run tests matching a pattern
pytest pipeline/tests -k "retry" -v
```

## Test Structure

```
pipeline/tests/
├── __init__.py              # Package marker
├── conftest.py              # Shared fixtures and configuration
├── test_schema_validator.py # Tests for schema_validator.py
├── test_progress_tracker.py # Tests for progress_tracker.py
├── test_retry_utils.py      # Tests for retry_utils.py
├── test_content_templates.py# Tests for content_templates.py
├── test_integration.py      # End-to-end integration tests
└── README.md                # This file
```

## Test Coverage

### Schema Validator (`test_schema_validator.py`)
- ✅ Initialization and configuration
- ✅ Schema loading and caching
- ✅ Validation with valid data
- ✅ Validation errors (missing fields, wrong types)
- ✅ Error handling (missing schema, invalid JSON)

### Progress Tracker (`test_progress_tracker.py`)
- ✅ Step lifecycle (start, complete, error)
- ✅ Duration calculation
- ✅ Summary generation
- ✅ Verbose console output
- ✅ Multiple steps workflow
- ✅ Error handling workflow

### Retry Utilities (`test_retry_utils.py`)
- ✅ Retry configuration
- ✅ Retryable vs non-retryable error classification
- ✅ Success on first attempt
- ✅ Success after retries
- ✅ Non-retryable errors fail immediately
- ✅ Max retries exceeded
- ✅ Exponential backoff timing
- ✅ Max delay cap
- ✅ Return type preservation

### Content Templates (`test_content_templates.py`)
- ✅ Summary templates for all presets
- ✅ Outline templates for all presets
- ✅ Key terms with/without thread refs
- ✅ Flashcard structure and difficulty
- ✅ Exam questions (multiple-choice, essay, short-answer)
- ✅ Preset consistency across all artifact types
- ✅ Evidence placeholders in research mode
- ✅ Simplification in beginner/neurodivergent modes

### Integration Tests (`test_integration.py`)
- ✅ PipelineContext creation and immutability
- ✅ Base artifact generation
- ✅ All artifact types generation
- ✅ Different presets produce different content
- ✅ Thread refs in artifacts
- ✅ Schema validation of generated artifacts
- ✅ Full end-to-end pipeline execution

## Fixtures

### Available Fixtures (in `conftest.py`)

- **`temp_dir`** - Temporary directory for test outputs
- **`sample_transcript`** - Sample lecture transcript
- **`valid_summary_artifact`** - Valid summary matching schema
- **`valid_thread`** - Valid thread matching schema
- **`schema_dir`** - Temporary schema directory for tests

## Test Utilities

### Mocking External Calls

Tests use `unittest.mock` for mocking:
```python
from unittest.mock import Mock

mock_op = Mock(return_value="success")
result = with_retry(mock_op)
```

### Testing Console Output

Tests use `capsys` fixture for capturing output:
```python
def test_output(capsys):
    tracker = ProgressTracker(verbose=True)
    tracker.start_step("test")

    captured = capsys.readouterr()
    assert "Starting: test" in captured.out
```

## Requirements

```bash
pip install -r pipeline/requirements.txt
```

**Test dependencies:**
- `pytest>=8.0.0` - Test framework
- `jsonschema>=4.20.0` - Required by schema_validator

## CI Integration

Tests run automatically on every push via GitHub Actions:

```yaml
- name: Install dependencies
  run: pip install -r pipeline/requirements.txt

- name: Run pipeline tests
  run: pytest pipeline/tests -v
```

## Code Coverage

Generate coverage reports:

```bash
# Run tests with coverage
pytest pipeline/tests --cov=pipeline --cov-report=term-missing

# Generate HTML coverage report
pytest pipeline/tests --cov=pipeline --cov-report=html
open htmlcov/index.html
```

**Current coverage:** ~95% for new modules
- schema_validator.py: 100%
- progress_tracker.py: 95%
- retry_utils.py: 100%
- content_templates.py: 98%

## Writing New Tests

### Test Naming Conventions

- Test files: `test_<module_name>.py`
- Test classes: `Test<FeatureName>`
- Test functions: `test_<what_it_tests>`

### Example Test

```python
def test_schema_validator_success(schema_dir):
    """Test successful validation."""
    validator = SchemaValidator(schema_dir)
    data = {"id": "test-001", "name": "Test"}

    # Should not raise
    validator.validate(data, "test.schema.json")
```

### Parametrized Tests

```python
@pytest.mark.parametrize("preset", [
    "exam-mode",
    "beginner-mode",
    "research-mode",
])
def test_all_presets(preset):
    """Test all presets return valid structure."""
    template = get_summary_template(preset, "test")
    assert "overview" in template
```

## Troubleshooting

### Import Errors

If you see import errors:
```bash
# Make sure you're in the project root
cd /path/to/project-pegasus

# Install requirements
pip install -r pipeline/requirements.txt
```

### Schema Not Found

Some integration tests require actual schema files:
```bash
# Tests will skip if schemas don't exist
pytest pipeline/tests/test_integration.py::TestSchemaValidation -v
```

### Tests Timing Out

Retry tests use small delays (0.01s). If they fail:
```bash
# Run with more verbose output
pytest pipeline/tests/test_retry_utils.py -vv -s
```

## Best Practices

1. **Use fixtures** - Reuse common test data
2. **Test edge cases** - Empty lists, None values, invalid inputs
3. **Test error paths** - Not just happy paths
4. **Keep tests fast** - Use minimal delays in timing tests
5. **Make tests isolated** - Each test should be independent
6. **Use descriptive names** - Test names should explain what they test
7. **Document complex tests** - Add docstrings for non-obvious tests

## Future Tests

Potential areas for additional testing:
- [ ] Thread engine tests
- [ ] LLM generation tests (with mocked API)
- [ ] Export functionality tests
- [ ] Audio ingestion tests
- [ ] Transcription tests
- [ ] Performance benchmarks
- [ ] Load/stress testing

## Contributing

When adding new pipeline features:

1. **Write tests first** (TDD approach)
2. **Aim for >90% coverage** for new code
3. **Test both success and failure paths**
4. **Add integration tests** for user-facing features
5. **Update this README** if adding new test categories

---

**Test Status:** ✅ All tests passing
**Coverage:** ~95% for new modules
**CI:** Integrated with GitHub Actions


### Thread Continuity Check
- ✅ `test_thread_continuity_check.py` validates continuity scoring and CLI pass/fail behavior
