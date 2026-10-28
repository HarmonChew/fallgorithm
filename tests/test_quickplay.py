"""Menu flows and commands for Experiments 006 and 008."""

from __future__ import annotations

import pytest

from block_stack_ai import cli, quickplay, watchrecord
from block_stack_ai.engine import PROJECT_ROOT

REC006 = "experiments/006-level29-survival/records/run.json.gz"
REC008 = "experiments/008-benchmark-format/records/run.json.gz"


@pytest.fixture
def menu(monkeypatch):
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)

    def run(*answers):
        remaining = iter(answers)
        monkeypatch.setattr("builtins.input", lambda prompt: next(remaining))
        from block_stack_ai.menu import select_command
        return select_command(cli._experiments())

    return run


def _top_seed(path, **match):
    episodes = [e for e in watchrecord.load_record(PROJECT_ROOT / path)["episodes"]
                if all(e.get(k) == v for k, v in match.items())]
    return max(episodes, key=lambda e: e["result"]["lines"])["seed"]


def test_006_new_game_defaults(menu):
    # experiment 7, action 1, agent default, fresh seed, frame limit default, Start
    assert menu("7", "1", "", "", "", "") == [
        "play-game", "--experiment", "006", "--agent", "survival_plan",
        "--frame-limit", "400000"]


def test_006_new_game_chosen(menu):
    assert menu("7", "1", "1", "42", "5000", "") == [
        "play-game", "--experiment", "006", "--agent", "search_plan",
        "--frame-limit", "5000", "--seed", "42"]


def test_006_recorded_game_by_list_and_typed_seed(menu):
    seed = _top_seed(REC006, agent="survival_plan")
    assert menu("7", "2", "", "", "") == [
        "watch-record", REC006, "--seed", str(seed), "--agent", "survival_plan"]
    assert menu("7", "2", "1", "33713", "") == [
        "watch-record", REC006, "--seed", "33713", "--agent", "search_plan"]


def test_006_evaluation(menu):
    assert menu("7", "3", "") == ["evaluate", "--experiment", "006", "--jobs", "30"]


def test_008_new_game_defaults_and_typed_numbers(menu):
    assert menu("8", "1", "", "", "", "") == [
        "play-game", "--experiment", "008", "--tap-hz", "30", "--reaction-ms", "300"]
    # fixed seed, 15 Hz from the list, typed 200 ms
    assert menu("8", "1", "9", "3", "4", "200", "") == [
        "play-game", "--experiment", "008", "--tap-hz", "15", "--reaction-ms", "200", "--seed", "9"]
    # typed tap speed; 0 and 31 and nan are refused and asked again
    assert menu("8", "1", "", "5", "0", "31", "nan", "25", "1", "")[3:7] == [
        "--tap-hz", "25", "--reaction-ms", "0"]
    assert menu("8", "1", "", "1", "4", "-1", "inf", "10", "")[3:7] == [
        "--tap-hz", "30", "--reaction-ms", "10"]


def test_008_recorded_game(menu):
    seed = _top_seed(REC008, format=1)
    assert menu("8", "2", "", "", "") == [
        "watch-record", REC008, "--seed", str(seed), "--format", "30hz-300ms"]
    assert menu("8", "2", "3", "9103", "") == [
        "watch-record", REC008, "--seed", "9103", "--format", "15hz-300ms"]


def test_008_evaluation_and_choose_again(menu):
    assert menu("8", "3", "2", "8", "3", "") == ["evaluate", "--experiment", "008", "--jobs", "30"]


def test_new_subcommands_parse(monkeypatch):
    calls = []
    monkeypatch.setattr(quickplay, "play_game", lambda e, **k: calls.append((e, k)) or 0)
    monkeypatch.setattr(quickplay, "evaluate", lambda e, jobs: calls.append((e, jobs)) or 0)
    monkeypatch.setattr(watchrecord, "main", lambda argv: calls.append(argv) or 0)
    assert cli.main(["play-game", "--experiment", "008", "--seed", "3", "--tap-hz", "20",
                     "--reaction-ms", "150", "--export-only"]) == 0
    assert cli.main(["play-game", "--experiment", "006"]) == 0
    assert cli.main(["evaluate", "--experiment", "006", "--jobs", "4"]) == 0
    assert cli.main(["watch-record", "r.json.gz", "--seed", "5", "--format", "30hz-0ms", "--export-only"]) == 0
    assert cli.main(["watch-record", "r.json.gz", "--list"]) == 0
    assert calls[0] == ("008", {"seed": 3, "agent": None, "frame_limit": None, "tap_hz": 20.0,
                                "reaction_ms": 150.0, "export_only": True})
    assert calls[1][1]["seed"] is None and calls[1][1]["export_only"] is False
    assert calls[2] == ("006", 4)
    assert calls[3] == ["r.json.gz", "--seed", "5", "--format", "30hz-0ms", "--export-only"]
    assert calls[4] == ["r.json.gz", "--list"]


def test_watch_record_finds_the_record_from_another_directory(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["watch-record", REC006, "--list"]) == 0
    assert "agent survival_plan" in capsys.readouterr().out


@pytest.mark.parametrize("arguments, message", [
    (["--experiment", "008", "--tap-hz", "0"], "above 0"),
    (["--experiment", "008", "--tap-hz", "31"], "above 0"),
    (["--experiment", "008", "--tap-hz", "nan"], "above 0"),
    (["--experiment", "008", "--reaction-ms", "-1"], "0 ms or more"),
    (["--experiment", "008", "--reaction-ms", "inf"], "0 ms or more"),
    (["--experiment", "008", "--agent", "survival_plan"], "006 only"),
    (["--experiment", "006", "--tap-hz", "30"], "008 only"),
    (["--experiment", "006", "--reaction-ms", "0"], "008 only"),
])
def test_play_game_rejects_bad_or_inapplicable_options(arguments, message, capsys):
    assert cli.main(["play-game", *arguments]) == 1
    assert message in capsys.readouterr().err


def test_start_level_is_gone():
    with pytest.raises(SystemExit):
        cli.main(["play-game", "--experiment", "008", "--start-level", "18"])


def test_bad_experiment_is_reported(capsys):
    assert cli.main(["play-game", "--experiment", "001"]) == 1
    assert "choose 006 or 008" in capsys.readouterr().err


def test_experiments_lists_006_and_008(capsys):
    assert cli.main(["experiments"]) == 0
    output = capsys.readouterr().out
    assert "006-level29-survival: live agents: search_plan, survival_plan" in output
    assert "008-benchmark-format:" in output


@pytest.mark.integration
@pytest.mark.parametrize("arguments, label", [
    (["--experiment", "008", "--seed", "11", "--frame-limit", "1500"], "new-008-11-30hz-300ms"),
    (["--experiment", "006", "--seed", "11", "--frame-limit", "1500"], "new-006-11-survival_plan"),
])
def test_play_game_export_only_writes_a_checked_replay(capsys, arguments, label):
    # watchrecord.export refuses to write a replay that ends elsewhere than the game did.
    assert cli.main(["play-game", *arguments, "--export-only"]) == 0
    assert "frame_limit" in capsys.readouterr().out
    replay = watchrecord.WATCH_DIR / f"{label}-f1500.rep"
    assert replay.is_file() and replay.stat().st_size > 0
