from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def test_cli_import_does_not_import_nonebot_plugin_package() -> None:
    project_root = Path(__file__).parents[2]
    env = os.environ.copy()
    module_root = project_root / "src" / "plugins"
    env.pop("PYTHONPATH", None)
    script = (
        f"import sys; sys.path.insert(0, {str(module_root)!r}); "
        "import _lingchu_bot_cli.app; "
        "assert 'nonebot_plugin_lingchu_bot' not in sys.modules"
    )

    result = subprocess.run(
        [sys.executable, "-I", "-c", script],
        cwd=project_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
