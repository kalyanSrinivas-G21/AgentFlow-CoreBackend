from pathlib import Path


def test_test_database_configuration_is_explicit_and_separate():
    source = Path("backend/tests/conftest.py").read_text(encoding="utf-8")
    assert "TEST_DATABASE_URL" in source
    assert "must be different from DATABASE_URL" in source
    assert "sovereign_ai_test" in source


def test_pytest_sandbox_resources_have_controlled_namespace():
    source = Path("backend/app/sandbox/runner.py").read_text(encoding="utf-8")
    assert "pytest-sandbox-" in source
