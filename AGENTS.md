# Project Goal

Provide a local CLI foundation for a Power BI editing agent with tool execution (including parallel tool calls) and report-template bootstrapping. All provider communication uses synchronous HTTP REST APIs via `urllib.request`:

| Provider | API Shape | Default Endpoint |
|---|---|---|
| **OpenAI** (default) | Responses API | `https://api.openai.com/v1/responses` |
| **xAI** | Responses API | `https://api.x.ai/v1/responses` |
| **Anthropic** | Messages API | `https://api.anthropic.com/v1/messages` |
| **Generic** (OpenAI-compatible) | Chat Completions API | `https://openrouter.ai/api/v1/chat/completions` |

## Running Tests

```bash
uv run pytest
uv run pytest tests/test_cli.py
uv run pytest tests/test_cli.py::DefaultWebCommandTests::test_main_defaults_to_web_for_global_options_only
uv run pytest -m slow
```

## Adding Tests

- Add new test modules under `tests/`.
- Name test files `test_*.py` so pytest discovers them automatically.
- Prefer pytest-style tests with plain `assert`; existing `unittest.TestCase` tests are still supported when needed.
- Import package code directly from `pbi_agent`; pytest is configured to add `src/` to `sys.path`, so new tests should not manually modify `sys.path`.
- Put shared fixtures in `tests/conftest.py` and use `@pytest.mark.parametrize(...)` for repeated input/output cases.
- Register any new custom markers in `pyproject.toml` under `tool.pytest.ini_options.markers` before using them.

Example:

```python
import pytest


@pytest.mark.parametrize(("value", "expected"), [("abc", 3), ("", 0)])
def test_string_length(value: str, expected: int) -> None:
    assert len(value) == expected
```

## Linting & Formatting

```bash
uvx ruff check . --fix && uvx ruff format .
```

## Project-Specific Tooling

```bash
uv run pbi-agent init --dest . --force
```

## Code Review

Every pull request must be reviewed before merging. The following guidelines ensure
consistent quality across the project.

### Test Coverage Requirements

- **Every new feature must include tests.** A feature PR without corresponding tests
  should not be approved.
- **Every bug fix must add a regression test** that fails without the fix and passes
  with it.
- **Modifications to existing behaviour require updating the affected tests.** If a
  change causes existing tests to fail, update those tests so they reflect the new
  expected behaviour rather than deleting them.
- Do not remove or weaken existing tests unless the tested functionality itself has
  been intentionally removed.

### What Reviewers Check

1. **Tests pass** – `uv run pytest` must exit cleanly. CI enforces this via the
   `tests.yml` workflow.
2. **Lint / format** – `uvx ruff check .` and `uvx ruff format --check .` must
   report no issues.
3. **Test quality** – new tests should follow the conventions listed in
   *Adding Tests* above:
   - Placed under `tests/` with a `test_*.py` filename.
   - Prefer pytest-style `assert` statements over `unittest` assertions for new
     tests.
   - Use `@pytest.mark.parametrize` for input/output variations.
   - Shared fixtures live in `tests/conftest.py`.
   - Custom markers are registered in `pyproject.toml` before use.
4. **Provider coverage** – changes touching a provider (OpenAI, xAI, Anthropic,
   Google, Generic) must include or update the matching `test_<provider>_provider.py`
   module.
5. **Tool coverage** – new or modified tools under `src/pbi_agent/tools/` must have
   tests in the corresponding `test_<tool>.py` file.
6. **No regressions in bundled assets** – changes to files under
   `src/pbi_agent/report/` or `src/pbi_agent/skills/` should be validated by
   `test_init_command.py` and `test_skill_knowledge_tool.py`.
7. **Security** – PRs must not introduce secrets, credentials, or new network calls
   without review. All HTTP communication goes through `urllib.request`.
8. **Minimal scope** – each PR should address a single concern. Unrelated changes
   should be split into separate PRs.

### Writing Good Tests for This Project

- **Mock HTTP calls** – use the `make_http_response` and `make_http_error` fixtures
  from `conftest.py` to simulate provider responses without hitting real APIs.
- **Use `DisplaySpy`** – capture display output through the `display_spy` fixture
  instead of asserting on stdout.
- **Isolate the file system** – use `tmp_path` (pytest built-in) for tests that
  create or modify files, as shown in `test_init_command.py`.
- **Mark slow / integration tests** – decorate with `@pytest.mark.slow` or
  `@pytest.mark.integration` so the default test run stays fast.
- **Keep tests focused** – each test should verify one behaviour. Use descriptive
  names that explain the scenario and expected outcome.

## Key Constraints

- Keep bundled PBIP template assets under `src/pbi_agent/report/`; packaging relies on `tool.hatch.build.targets.wheel.force-include`.
