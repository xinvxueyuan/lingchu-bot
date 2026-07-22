from importlib.metadata import entry_points
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


def test_nb_plugin_entry_point_is_declared() -> None:
    plugins = {entry.name: entry.value for entry in entry_points(group="nb")}

    assert plugins["lingchu"] == "_lingchu_bot_cli.nb_plugin:install"


def test_nb_plugin_runs_one_child_and_preserves_exit_code() -> None:
    from subprocess import CompletedProcess
    import sys
    from unittest.mock import patch

    from _lingchu_bot_cli.nb_plugin import lingchu
    from click.testing import CliRunner

    with patch(
        "_lingchu_bot_cli.nb_plugin.subprocess.run",
        return_value=CompletedProcess((), 7),
    ) as run:
        result = CliRunner().invoke(lingchu, ["doctor", "--json"])

    assert result.exit_code == 7
    run.assert_called_once_with(
        (
            sys.executable,
            "-m",
            "_lingchu_bot_cli",
            "doctor",
            "--json",
        ),
        check=False,
    )


def test_nb_plugin_install_registers_lingchu_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from _lingchu_bot_cli import nb_plugin

    cli = MagicMock()
    import_module = MagicMock(return_value=SimpleNamespace(cli=cli))
    monkeypatch.setattr(nb_plugin, "import_module", import_module)

    nb_plugin.install()

    import_module.assert_called_once_with("nb_cli.cli")
    cli.add_command.assert_called_once_with(nb_plugin.lingchu)
