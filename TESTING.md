# Testing Guide

This document explains how to write, run, and maintain tests for the NBA Digest project.

## Quick Start

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=nba_digest --cov-report=term-missing

# Run a specific test file
pytest tests/test_models.py -v

# Run a specific test
pytest tests/test_models.py::TestGame::test_valid_game -v
```

## Test Structure

```
tests/
├── conftest.py              # Pytest fixtures (shared test data)
├── test_models.py           # Pydantic model validation tests
├── test_api.py              # API client tests (mocked)
├── test_builders.py         # HTML builder output tests
├── test_services.py         # Service integration tests
└── test_config.py           # Configuration validation tests
```

## Writing Tests

### Using Fixtures

Fixtures provide reusable test data. Define fixtures in `tests/conftest.py`:

```python
import pytest
from nba_digest.models import Game

@pytest.fixture
def sample_game() -> Game:
    """Return a valid Game instance for testing."""
    return Game(
        winner_abbr="ATL",
        winner_name="Hawks",
        winner_score=107,
        loser_abbr="NYK",
        loser_name="Knicks",
        loser_score=106,
        game_number=3,
        venue="State Farm Arena",
        series_status="ATL leads 2-1",
        pts_leader="McCollum 23",
        reb_leader="Johnson 10",
        ast_leader="Barnes 11"
    )
```

Then use in tests:

```python
def test_game_validation(sample_game):
    """Test that valid game data passes validation."""
    assert sample_game.winner_abbr == "ATL"
    assert sample_game.winner_score == 107
```

### Mocking External APIs

Use `unittest.mock` to mock external API calls (never call real APIs in tests):

```python
from unittest.mock import patch, MagicMock

@patch("urllib.request.urlopen")
def test_reddit_fetch(mock_urlopen):
    """Test Reddit client with mocked HTTP response."""
    # Setup mock response
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"data": {"children": [...]}}'
    mock_urlopen.return_value.__enter__.return_value = mock_resp
    
    # Test
    client = RedditClient()
    posts = client.fetch_posts()
    
    # Assert
    assert isinstance(posts, str)
    assert len(posts) > 0
```

### Testing Error Paths

Always test both success and failure:

```python
def test_invalid_game_number():
    """Test that game number must be 1-7."""
    with pytest.raises(ValueError):
        Game(
            winner_abbr="ATL",
            winner_name="Hawks",
            winner_score=100,
            loser_abbr="NYK",
            loser_name="Knicks",
            loser_score=90,
            game_number=8,  # Invalid!
            venue="Stadium",
            series_status="ATL leads",
            pts_leader="P1 10",
            reb_leader="P2 5",
            ast_leader="P3 3",
        )
```

## Test Categories

### 1. Model Tests (`test_models.py`)

**Purpose**: Validate Pydantic models

- Valid data passes validation
- Invalid data raises `ValueError`
- Markdown fence handling in Claude responses
- JSON parsing from raw strings
- Serialization to dict/JSON

**Example**:

```python
class TestDigest:
    def test_valid_digest(self, sample_digest):
        """Valid digest passes validation."""
        assert sample_digest.main_headline == "Hawks Stun Knicks"
        assert len(sample_digest.games) == 1
    
    def test_parse_from_claude_response(self, sample_claude_response):
        """Parse and validate Claude JSON response."""
        digest = Digest.from_claude_response(sample_claude_response)
        assert digest.main_headline == "Hawks Stun Knicks"
    
    def test_parse_with_markdown_fences(self):
        """Handle Claude response with markdown code fences."""
        response = """```json
{
    "date": "Thursday, April 25, 2026",
    ...
}
```"""
        digest = Digest.from_claude_response(response)
        assert digest.date == "Thursday, April 25, 2026"
```

### 2. API Tests (`test_api.py`)

**Purpose**: Test API clients with mocked external calls

Never call real APIs in tests. Always mock:

```python
@patch("anthropic.Anthropic")
def test_claude_generation(mock_anthropic_class):
    """Test Claude client with mocked API."""
    # Setup mock
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text='{"date": "...", ...}')]
    mock_client.messages.create.return_value = mock_response
    
    # Test
    claude = ClaudeClient(api_key="test-key")
    digest = claude.generate_digest("Test prompt")
    
    # Assert
    assert digest.main_headline is not None
```

**Test coverage**:
- Successful API calls
- API errors (rate limit, auth, etc.)
- Retry logic
- Network failures (non-fatal)

### 3. Builder Tests (`test_builders.py`)

**Purpose**: Validate HTML output from builders

```python
def test_email_builder_output(sample_digest):
    """EmailBuilder.build() returns valid HTML."""
    builder = EmailBuilder()
    html = builder.build(sample_digest, iso_date="2026-04-25")
    
    # Check structure
    assert "<html>" in html
    assert "<body>" in html
    
    # Check content
    assert sample_digest.main_headline in html
    assert len(html) > 1000
```

**Test coverage**:
- HTML structure is valid
- All digest content is present
- HTML is escaped (XSS protection)
- CSS styling applied
- Links are correct

### 4. Service Tests (`test_services.py`)

**Purpose**: Test service orchestration

```python
@patch("nba_digest.api.reddit.RedditClient.fetch_posts")
@patch("nba_digest.api.claude.ClaudeClient.generate_digest")
def test_digest_service(mock_claude, mock_reddit, sample_digest):
    """DigestService.generate() coordinates workflow."""
    # Setup mocks
    mock_reddit.return_value = "Top posts..."
    mock_claude.return_value = sample_digest
    
    # Test
    config = Config.from_env()
    service = DigestService(config)
    digest = service.generate(season_mode="playoffs")
    
    # Assert
    assert digest.main_headline == sample_digest.main_headline
    mock_reddit.assert_called_once()
    mock_claude.assert_called_once()
```

### 5. Config Tests (`test_config.py`)

**Purpose**: Validate configuration loading and validation

```python
def test_config_from_env(monkeypatch):
    """Config.from_env() loads environment variables."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "test-password")
    
    config = Config.from_env()
    
    assert config.anthropic_api_key == "test-key-123"
    assert config.gmail_app_password == "test-password"

def test_config_missing_required(monkeypatch):
    """Config.from_env() raises ValueError if required fields missing."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    
    with pytest.raises(ValueError):
        Config.from_env()
```

## Mocking Strategies

### Strategy 1: Patch at Import Location

Mock where the object is **used**, not where it's defined:

```python
# ✅ Correct: Patch where urllib is used
@patch("nba_digest.api.reddit.urllib.request.urlopen")
def test_reddit(mock_urlopen):
    ...

# ❌ Wrong: Patch where urllib is defined
@patch("urllib.request.urlopen")
def test_reddit(mock_urlopen):
    ...
```

### Strategy 2: Patch Classes, Not Modules

```python
# ✅ Correct: Patch the Anthropic class
@patch("anthropic.Anthropic")
def test_claude(mock_anthropic_class):
    ...

# ❌ Wrong: Patching the module doesn't affect class instantiation
@patch("anthropic")
def test_claude(mock_anthropic):
    ...
```

### Strategy 3: Use monkeypatch for Environment Variables

```python
def test_with_env(monkeypatch):
    """Use pytest's monkeypatch for env vars."""
    monkeypatch.setenv("KEY", "value")
    monkeypatch.delenv("KEY", raising=False)
```

## Coverage Goals

Target >80% code coverage:

```bash
pytest tests/ --cov=nba_digest --cov-report=html
# Open htmlcov/index.html to see coverage breakdown
```

**Key files to cover**:
- ✅ `models.py` — All validators (100%)
- ✅ `api/` — All clients (95%+)
- ✅ `builders/` — HTML generation (90%+)
- ✅ `services/` — Orchestration logic (90%+)
- ⚠️ `config.py` — Config loading (85%+)

**Low priority**:
- Error messages (not critical to functionality)
- Type hints in comments (not executable)
- __init__.py files (usually empty)

## Running Tests in CI/CD

The `.github/workflows/lint.yml` workflow runs tests on every push:

```yaml
- name: Run tests
  run: pytest tests/ -v --tb=short

- name: Test coverage
  run: pytest tests/ --cov=nba_digest --cov-report=term-missing
```

**Fix CI failures**:

1. Check test output: `git push` and review Actions tab
2. Run locally: `pytest tests/ -v` to reproduce
3. Fix code or test
4. Commit and push
5. Verify CI passes

## Common Testing Patterns

### Testing Retry Logic

```python
@patch("anthropic.Anthropic")
def test_retry_on_rate_limit(mock_anthropic_class):
    """Test that rate limit (429) triggers retry."""
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client
    
    # First call: rate limit, second call: success
    rate_limit_error = Exception("429")
    success_response = MagicMock()
    success_response.content = [MagicMock(type="text", text='{"date": "...", ...}')]
    
    mock_client.messages.create.side_effect = [
        rate_limit_error,
        success_response,
    ]
    
    with patch("time.sleep"):  # Don't actually sleep
        claude = ClaudeClient(api_key="test", rate_limit_backoff=1)
        digest = claude.generate_digest("Test")
    
    # Second call should have succeeded
    assert digest.main_headline is not None
    assert mock_client.messages.create.call_count == 2
```

### Testing Non-Fatal Failures

```python
@patch("urllib.request.urlopen")
def test_reddit_failure_graceful(mock_urlopen):
    """Test that Reddit fetch failure doesn't break digest."""
    mock_urlopen.side_effect = Exception("Connection error")
    
    client = RedditClient()
    posts = client.fetch_posts()
    
    # Should return empty string, not raise
    assert posts == ""
```

### Testing Data Parsing

```python
def test_digest_from_json():
    """Test parsing Claude's JSON response."""
    json_str = """{
        "date": "Thursday, April 25, 2026",
        "round": "First Round",
        "main_headline": "Hawks Win",
        "sub_headline": "ATL takes 2-1 lead",
        "games": [
            {
                "winner_abbr": "ATL",
                "winner_name": "Hawks",
                ...
            }
        ],
        "active_series": [],
        "recaps": [],
        "headlines": [],
        "standout_performances": []
    }"""
    
    digest = Digest.from_claude_response(json_str)
    
    assert digest.date == "Thursday, April 25, 2026"
    assert len(digest.games) == 1
    assert digest.games[0].winner_abbr == "ATL"
```

## Debugging Tests

### Print Debug Info

```python
def test_something(sample_digest):
    """Use -s flag to see prints."""
    print(f"Digest: {sample_digest.dict()}")
    assert sample_digest.main_headline is not None
```

Run with: `pytest tests/ -s -v`

### Drop into Debugger

```python
def test_something(sample_digest):
    """Use pdb breakpoint."""
    import pdb; pdb.set_trace()
    assert sample_digest.main_headline is not None
```

Run with: `pytest tests/ -s -v` (stops at breakpoint)

### Check Mock Calls

```python
@patch("urllib.request.urlopen")
def test_mock_calls(mock_urlopen):
    """Inspect mock calls."""
    # Call the function
    client = RedditClient()
    posts = client.fetch_posts()
    
    # Check what the mock was called with
    print(mock_urlopen.call_args)      # Last call
    print(mock_urlopen.call_args_list) # All calls
    print(mock_urlopen.call_count)     # Number of calls
    
    mock_urlopen.assert_called_once()  # Assert called exactly once
```

## Best Practices

1. **One assertion per test** when possible (easier to debug)
2. **Use descriptive names** (`test_valid_game` not `test_1`)
3. **Test both paths** (success and failure)
4. **Mock external calls** (never use real APIs)
5. **Use fixtures** for shared data (DRY principle)
6. **Keep tests fast** (should run in <1s per test)
7. **Make tests independent** (no shared state between tests)
8. **Group related tests** in classes (`TestGame`, `TestDigest`, etc.)

## Troubleshooting

### "ModuleNotFoundError: No module named 'nba_digest'"

The tests need the package to be importable. Fix:

```bash
cd /path/to/nba-digest
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/ -v
```

### "Fixtures not found"

Pytest looks for `conftest.py` in the same directory or parent directories. Make sure `tests/conftest.py` exists.

### "Mock not being used"

Check patch path — must match where the object is **used**, not defined:

```python
# If nba_digest.api.claude imports from anthropic:
# from anthropic import Anthropic

# Then patch where it's used:
@patch("nba_digest.api.claude.Anthropic")
def test_foo(mock_anthropic):
    ...
```

### Tests timeout

Some tests may hang if mocks aren't set up correctly. Use pytest timeout:

```bash
pip install pytest-timeout
pytest tests/ --timeout=5  # 5 second timeout per test
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html)
- [Pydantic Testing Guide](https://docs.pydantic.dev/latest/concepts/testing/)
