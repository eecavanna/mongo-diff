from typer.testing import CliRunner

from mongo_diff.mongo_diff import app

runner = CliRunner()


def test_help_option() -> None:
    """Verify that invoking the CLI with `--help` exits cleanly and displays usage info."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Compare two MongoDB collections." in result.output
