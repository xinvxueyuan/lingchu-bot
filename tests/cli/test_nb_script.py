from importlib.metadata import entry_points


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
