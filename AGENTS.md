# Project Guidelines

## Project Structure

- Application code lives in `src/django_pydantic_ai/`.
- Tests live in `tests/` and use the Django project in `testproj/`.
- Keep public APIs consistent across synchronous and asynchronous flows when both exist.
- Whenever possible, create a Django sub-app for each Pydantic AI Harness utility, following the pattern `django_pydantic_ai.memory` for `pydantic_ai_harness.memory`.
- Each sub-app should own its models, app config, and migrations under its own package folder, such as `src/django_pydantic_ai/memory/`.
- Database schema changes require a new migration under the relevant sub-app's `migrations/` directory.
- Keep changes minimal and aligned with neighboring code and existing naming patterns.

## Development Commands

- Run the full test matrix with `hatch test`.
- Run focused tests with `hatch run pytest tests/<test_file>.py`.
- Run the local test suite via `hatch run pytest` when validating a broader change.
- Run linting with `hatch check code`.
- Verify formatting with `hatch check fmt`.
- Run strict type checks with `hatch check types`.
- Generate migrations with `hatch run python manage.py makemigrations django_pydantic_ai -n "friendly_name"`; never hand-write migrations.

## Python and Django Conventions

- Support the Python and Django versions declared in `pyproject.toml`.
- Preserve strict typing and existing type annotations; production code is checked with mypy and Pyrefly.
- Follow the existing Ruff configuration, including the 120-character line limit.
- Prefer Django ORM, models, and cache APIs over duplicating persistence or cache logic.
- Prefer a dedicated sub-app per Harness utility instead of placing unrelated logic at the package root.
- Use timezone-aware datetimes via `django.utils.timezone` for expiry or expiration-related logic.
- Keep sync and async public APIs behaviorally equivalent unless the API contract explicitly differs.
- Keep changes compatible with Django 6.1+ and Python 3.12+ as declared in the project metadata.
- Avoid `db_index=True` and `unique=True` on fields; declare uniqueness in `Meta.constraints` and add indexes in `Meta.indexes` only when a query truly needs them.
- Set `db_index=False` on ForeignKey fields and define any required index explicitly in `Meta.indexes` only when a real query pattern justifies it.

## Testing Expectations

- Add or update focused tests for every behavior change.
- Prefer synchronous tests in pytest; use `async_to_sync` only when it is necessary to invoke an async API from the synchronous test harness.
- Include synchronous and asynchronous coverage when changing paired APIs or behavior.
- Cover the relevant edge cases for each change, especially expiration and lifecycle conditions.
- Run the focused test file first, then the broader suite before finishing.
- Group tests for a class or module in a single `Test<Name>` class and prefix each test with `test_<method>_`.
- Order test classes and methods to match the definition order in the corresponding source file.

## Change Scope

- Keep changes minimal and consistent with neighboring code.
- Do not modify generated migration history or unrelated user changes.
- Use Conventional Commits for commit messages, such as `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, or `chore:`.
- Update `README.md` when a change affects documented behavior, public APIs, configuration, installation, or usage.
- Update `CHANGELOG.md` for user-visible changes that are not already part of a published release.

## Quality Bar

- Do not add broad refactors or unrelated cleanup in the same patch.
- Prefer targeted fixes that match the surrounding patterns and maintain compatibility.
- Ensure new code is covered by tests and remains compatible with the supported dependency matrix.
