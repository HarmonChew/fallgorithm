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
    ["run"],
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


@pytest.fixture
def menu_input(monkeypatch):
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)

    def set_answers(*answers):
        remaining = iter(answers)

        def answer(prompt):
            print(prompt, end="")
            value = next(remaining)
            if isinstance(value, BaseException):
                raise value
            return value

        monkeypatch.setattr("builtins.input", answer)

    return set_answers


@pytest.fixture
def launched(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(cli, "play_live", lambda *args: calls.append(("play", args)))

    def run(path):
        calls.append(("run", path))
        config = json.loads(path.read_text())
        if "agents" in config:
            record = {"configuration": config, "episodes": [], "summary": {
                name: {"games": len(config["seeds"]), "stopping_reasons": {"game_over": len(config["seeds"])},
                       **{metric: {"mean": 0} for metric in ("score", "lines", "frames")}}
                for name in config["agents"]
            }}
        else:
            record = {"result": json.loads((PROJECT_ROOT / "experiments/000-connection/result.json").read_text())}
        record_path = tmp_path / "run.json"
        record_path.write_text(json.dumps(record))
        return record_path

    def watch(path):
        calls.append(("watch", path))
        return 0

    monkeypatch.setattr(cli, "run_and_save", run)
    monkeypatch.setattr(cli, "watch_run", watch)
    return calls


@pytest.mark.parametrize("arguments", [[], ["menu"]])
def test_menu_launches_selected_live_options(experiment_root, menu_input, launched, capsys, arguments):
    menu_input("2", "1", "1", "42", "5", "2", "1")
    assert cli.main(arguments) == 0
    config = experiment_root / "experiments/001-greedy-heuristic/config.json"
    assert launched == [("play", (config, "random", 42, "4", True))]
    output = capsys.readouterr().out
    assert "Agent: random; seed: 42; speed: 4x; start: paused" in output
    assert "Command: block-stack-ai play --experiment 001-greedy-heuristic" in output


def test_menu_requires_experiment_and_action_but_defaults_live_settings(experiment_root, menu_input, launched, capsys):
    menu_input("", "not a number", "99", "2", "", "1", "", "", "", "", "")
    assert cli.main([]) == 0
    config = experiment_root / "experiments/001-greedy-heuristic/config.json"
    assert launched == [("play", (config, "greedy", None, "1", False))]
    output = capsys.readouterr().out
    assert output.count("Please enter an option number") == 4
    assert "seed: fresh random" in output


@pytest.mark.parametrize("seed", ["0", "65535"])
def test_menu_uses_only_configured_agents_and_validates_seed(experiment_root, menu_input, launched, capsys, seed):
    path = experiment_root / "experiments/001-greedy-heuristic/config.json"
    config = json.loads(path.read_text())
    config["agents"] = ["random"]
    path.write_text(json.dumps(config))
    menu_input("2", "1", "", "-1", "65536", "1.5", seed, "", "", "")
    assert cli.main(["menu"]) == 0
    assert launched == [("play", (path, "random", int(seed), "1", False))]
    output = capsys.readouterr().out
    assert "greedy (default)" not in output
    assert output.count("Please enter a whole number") == 3


def test_menu_evaluation_uses_complete_saved_config(experiment_root, menu_input, launched, capsys):
    path = experiment_root / "experiments/001-greedy-heuristic/config.json"
    original = path.read_bytes()
    menu_input("2", "2", "")
    assert cli.main([]) == 0
    assert launched == [("run", path)]
    assert path.read_bytes() == original
    output = capsys.readouterr().out
    assert "Agents: random, greedy" in output
    assert "Seeds: 2, 4, 6, 8, 10, 12, 14, 16, 18, 20" in output
    assert "Games: 20" in output
    assert "Start the game" not in output


@pytest.mark.parametrize("action,watch", [("1", False), ("2", True)])
def test_menu_scripted_choices_run_and_optionally_watch(experiment_root, menu_input, launched, capsys, action, watch):
    menu_input("1", action, "")
    assert cli.main(["menu"]) == 0
    assert launched[0] == ("run", experiment_root / "experiments/000-connection/config.json")
    assert [call[0] for call in launched] == (["run", "watch"] if watch else ["run"])
    output = capsys.readouterr().out
    assert "Watch a fresh game" not in output
    assert "\nAgent\n" not in output


def test_menu_choose_again_discards_previous_selection(experiment_root, menu_input, launched):
    menu_input("2", "1", "1", "42", "5", "2", "2", "1", "1", "")
    assert cli.main([]) == 0
    assert launched == [("run", experiment_root / "experiments/000-connection/config.json")]


@pytest.mark.parametrize("answers,status", [
    (("q",), 0),
    (("2", "quit"), 0),
    (("2", "1", "", "q"), 0),
    (("2", "1", "", "", "", "", "q"), 0),
    ((EOFError(),), 0),
    (("2", "2", EOFError()), 0),
    (("2", KeyboardInterrupt()), 130),
])
def test_menu_cancellation_never_launches(experiment_root, menu_input, launched, answers, status):
    menu_input(*answers)
    assert cli.main([]) == status
    assert not launched


@pytest.mark.parametrize("arguments", [[], ["menu"]])
def test_menu_requires_terminal_without_reading_input(monkeypatch, launched, capsys, arguments):
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr("builtins.input", lambda _: pytest.fail("must not read redirected input"))
    with pytest.raises(SystemExit) as error:
        cli.main(arguments)
    assert error.value.code == 2
    assert not launched
    assert "interactive menu needs a terminal" in capsys.readouterr().err


def test_menu_empty_discovery_is_actionable(tmp_path, monkeypatch, menu_input, launched, capsys):
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    menu_input()
    assert cli.main([]) == 1
    assert not launched
    assert "No experiments found" in capsys.readouterr().err
