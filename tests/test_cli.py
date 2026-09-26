from __future__ import annotations

import json
from pathlib import Path

import pytest

from block_stack_ai import cli
from block_stack_ai.engine import PROJECT_ROOT


@pytest.fixture
def experiment_root(tmp_path, monkeypatch):
    for name in ("000-connection", "001-greedy-heuristic"):
        directory = tmp_path / "experiments" / name
        directory.mkdir(parents=True)
        directory.joinpath("config.json").write_bytes(
            (PROJECT_ROOT / "experiments" / name / "config.json").read_bytes()
        )
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    return tmp_path


def test_experiments_lists_live_and_scripted_choices_without_engine(experiment_root, monkeypatch, capsys):
    monkeypatch.setenv("BLOCKS_NATIVE_LIB", str(experiment_root / "missing.so"))
    assert cli.main(["experiments"]) == 0
    output = capsys.readouterr().out
    assert "000-connection: scripted" in output
    assert "001-greedy-heuristic: live agents: random, greedy" in output


@pytest.mark.parametrize("selection", ["001", "1", "001-greedy-heuristic"])
def test_play_resolves_experiment_from_project_not_current_directory(experiment_root, monkeypatch, capsys, selection):
    calls = []
    monkeypatch.setattr(cli, "play_live", lambda *args: calls.append(args))
    elsewhere = experiment_root / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert cli.main(["play", "--experiment", selection, "--agent", "random", "--seed", "2"]) == 0
    config = experiment_root / "experiments/001-greedy-heuristic/config.json"
    assert calls == [(config, "random", 2, "1", False)]
    assert "Experiment: 001-greedy-heuristic" in capsys.readouterr().out


def test_run_uses_selected_experiment(experiment_root, monkeypatch):
    record = experiment_root / "run.json"
    result = json.loads((PROJECT_ROOT / "experiments/000-connection/result.json").read_text())
    record.write_text(json.dumps({"result": result}), encoding="utf-8")
    calls = []

    def run(path):
        calls.append(path)
        return record

    monkeypatch.setattr(cli, "run_and_save", run)
    assert cli.main(["run", "--experiment", "000"]) == 0
    assert calls == [experiment_root / "experiments/000-connection/config.json"]


def test_explicit_config_remains_available(experiment_root, monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "play_live", lambda *args: calls.append(args))
    config = experiment_root / "experiments/001-greedy-heuristic/config.json"
    assert cli.main(["play", "--config", str(config)]) == 0
    assert calls[0][0] == config


@pytest.mark.parametrize("arguments", [
    ["play"],
    ["play", "--experiment", "001", "--config", "custom.json"],
])
def test_selection_is_explicit_and_unambiguous(arguments):
    with pytest.raises(SystemExit) as error:
        cli.main(arguments)
    assert error.value.code == 2


def test_unknown_experiment_never_falls_back_to_default(experiment_root, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(cli, "play_live", lambda *args: calls.append(args))
    assert cli.main(["play", "--experiment", "999"]) == 1
    assert not calls
    error = capsys.readouterr().err
    assert "Unknown experiment" in error
    assert "001-greedy-heuristic" in error


def test_duplicate_number_requires_full_directory_name(experiment_root, monkeypatch, capsys):
    source = experiment_root / "experiments/001-greedy-heuristic/config.json"
    alternate = experiment_root / "experiments/001-alternative/config.json"
    alternate.parent.mkdir()
    alternate.write_bytes(source.read_bytes())
    calls = []
    monkeypatch.setattr(cli, "play_live", lambda *args: calls.append(args))
    assert cli.main(["play", "--experiment", "001"]) == 1
    assert not calls
    assert "ambiguous" in capsys.readouterr().err
    assert cli.main(["play", "--experiment", "001-alternative"]) == 0
    assert calls[0][0] == alternate


def test_scripted_experiment_explains_how_to_watch_it(experiment_root, monkeypatch, capsys):
    monkeypatch.setenv("BLOCKS_NATIVE_LIB", str(experiment_root / "missing.so"))
    assert cli.main(["play", "--experiment", "000"]) == 1
    error = capsys.readouterr().err
    assert "scripted experiment" in error
    assert "--watch" in error
