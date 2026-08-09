from __future__ import annotations

from pathlib import Path

import pytest

from scripts import clean_dev_data


def _create_targets(root: Path) -> None:
    for relative_path in clean_dev_data.RUNTIME_DIRECTORIES:
        (root / relative_path).mkdir()
    for relative_path in clean_dev_data.ARTIFACT_DIRECTORIES:
        (root / relative_path).mkdir()
    for relative_path in clean_dev_data.ARTIFACT_FILES:
        (root / relative_path).write_text("artifact", encoding="utf-8")
    (root / ".coverage.worker-1").write_text("artifact", encoding="utf-8")


def test_clean_dev_data_dry_run_preserves_targets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_targets(tmp_path)
    monkeypatch.setattr(clean_dev_data, "_repository_root", lambda: tmp_path)

    processed = clean_dev_data.clean_dev_data(apply=False, include_artifacts=True)

    expected_count = (
        len(clean_dev_data.RUNTIME_DIRECTORIES)
        + len(clean_dev_data.ARTIFACT_DIRECTORIES)
        + len(clean_dev_data.ARTIFACT_FILES)
        + 1
    )
    assert processed == expected_count
    assert (tmp_path / "data").exists()
    assert (tmp_path / "dist").exists()
    assert (tmp_path / ".coverage.worker-1").exists()


def test_clean_dev_data_apply_removes_runtime_and_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_targets(tmp_path)
    monkeypatch.setattr(clean_dev_data, "_repository_root", lambda: tmp_path)

    processed = clean_dev_data.clean_dev_data(apply=True, include_artifacts=True)

    expected_count = (
        len(clean_dev_data.RUNTIME_DIRECTORIES)
        + len(clean_dev_data.ARTIFACT_DIRECTORIES)
        + len(clean_dev_data.ARTIFACT_FILES)
        + 1
    )
    assert processed == expected_count
    assert not (tmp_path / "data").exists()
    assert not (tmp_path / "dist").exists()
    assert not (tmp_path / ".coverage.worker-1").exists()


def test_validate_target_rejects_path_outside_repository(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="outside repository"):
        clean_dev_data._validate_target(tmp_path, tmp_path.parent / "outside")
