from __future__ import annotations

import json
import hashlib
import importlib
import subprocess
from pathlib import Path

import pytest


capture = importlib.import_module("tools.capture_canonical_golden")


def test_source_capture_is_bound_to_pinned_head_and_relevant_file_hashes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        capture,
        "_source_head",
        lambda: capture.SOURCE_BASELINE_SHA,
    )
    monkeypatch.setattr(capture, "_changed_relevant_files", lambda: [])
    receipt = capture.verify_source_baseline()

    assert receipt["source_baseline_sha"] == capture.SOURCE_BASELINE_SHA
    assert receipt["changed_relevant_files"] == []
    assert set(receipt["source_file_sha256"]) == set(capture.SOURCE_FILES)
    assert all(len(value) == 64 for value in receipt["source_file_sha256"].values())


def test_capture_can_reproduce_the_pinned_git_object_without_current_checkout() -> None:
    result = subprocess.run(
        [
            "python3",
            "tools/capture_canonical_golden.py",
            "--source-ref",
            capture.SOURCE_BASELINE_SHA,
        ],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["source_baseline_sha"] == capture.SOURCE_BASELINE_SHA
    assert set(payload["source_file_sha256"]) == set(capture.SOURCE_FILES)
    fixture = (Path(__file__).parent / "fixtures" / "canonical_golden.json").read_text(
        encoding="utf-8"
    )
    assert result.stdout == fixture
    receipt = json.loads(
        (Path(__file__).parent / "fixtures" / "canonical_golden.receipt.json").read_text(
            encoding="utf-8"
        )
    )
    assert receipt["source_baseline_sha"] == capture.SOURCE_BASELINE_SHA
    assert receipt["source_file_sha256"] == payload["source_file_sha256"]
    assert receipt["fixture_sha256"] == hashlib.sha256(fixture.encode()).hexdigest()


def test_source_capture_rejects_a_different_head() -> None:
    with pytest.raises(RuntimeError, match="source HEAD mismatch"):
        capture.validate_source_baseline(
            actual_head="not-the-pinned-head",
            changed_relevant_files=[],
        )


def test_source_capture_rejects_relevant_worktree_drift() -> None:
    with pytest.raises(RuntimeError, match="relevant source files are dirty"):
        capture.validate_source_baseline(
            actual_head=capture.SOURCE_BASELINE_SHA,
            changed_relevant_files=["services/dca_plan.py"],
        )
