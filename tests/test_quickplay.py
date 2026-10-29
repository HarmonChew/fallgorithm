"""Menu flows and commands for Experiments 006 and 008-014."""

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
    (["--experiment", "006", "--tap-hz", "30"], "008-014 only"),
    (["--experiment", "006", "--reaction-ms", "0"], "008-014 only"),
])
def test_play_game_rejects_bad_or_inapplicable_options(arguments, message, capsys):
    assert cli.main(["play-game", *arguments]) == 1
    assert message in capsys.readouterr().err


def test_start_level_is_gone():
    with pytest.raises(SystemExit):
        cli.main(["play-game", "--experiment", "008", "--start-level", "18"])


def test_bad_experiment_is_reported(capsys):
    assert cli.main(["play-game", "--experiment", "001"]) == 1
    assert "choose 006, 008, 009, 010, 011, 012, 013 or 014" in capsys.readouterr().err


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


REC009 = "experiments/009-cem-score/records/run.json.gz"


def test_009_is_wired_into_the_launcher(menu, monkeypatch):
    assert quickplay.experiment_id("9") == "009"
    assert quickplay.record_path("009").name == "run.json.gz"
    assert menu("9", "1", "", "", "", "") == [
        "play-game", "--experiment", "009", "--tap-hz", "30", "--reaction-ms", "300"]
    assert menu("9", "1", "9", "3", "4", "200", "") == [
        "play-game", "--experiment", "009", "--tap-hz", "15", "--reaction-ms", "200", "--seed", "9"]
    assert menu("9", "3", "") == ["evaluate", "--experiment", "009", "--jobs", "30"]
    calls = []
    monkeypatch.setattr(quickplay.experiment009, "main", lambda argv: calls.append(argv) or 0)
    assert quickplay.evaluate("009", 5) == 0
    assert calls == [["evaluate", "--jobs", "5"]]


def test_009_recorded_game_in_the_menu(menu):
    seed = _top_seed(REC009, format=0)
    assert menu("9", "2", "", "", "") == [
        "watch-record", REC009, "--seed", str(seed), "--format", "30hz-300ms"]


def test_009_is_listed_and_new_game_needs_trained_parameters(capsys, monkeypatch, tmp_path):
    assert cli.main(["experiments"]) == 0
    assert "009-cem-score: tuned_plan in 1 tap/reaction formats" in capsys.readouterr().out
    monkeypatch.setattr(quickplay.experiment009, "FINAL_PARAMS", tmp_path / "missing.json")
    assert cli.main(["play-game", "--experiment", "009", "--seed", "3"]) == 1
    assert "no trained parameters" in capsys.readouterr().err


@pytest.mark.integration
def test_watch_record_exports_a_009_game(tmp_path):
    seed = _top_seed(REC009, format=0)
    record = watchrecord.load_record(PROJECT_ROOT / REC009)
    episode = watchrecord.select_episode(record, seed, format_value="30hz-300ms")
    assert watchrecord.export(record, episode, tmp_path / "game.rep").exists()


REC010 = "experiments/010-complete-reach/records/run.json.gz"


def test_010_is_wired_into_the_launcher(menu, monkeypatch):
    assert quickplay.experiment_id("10") == "010"
    assert quickplay.record_path("010").name == "run.json.gz"
    assert menu("10", "1", "", "", "", "") == [
        "play-game", "--experiment", "010", "--tap-hz", "30", "--reaction-ms", "300"]
    assert menu("10", "3", "") == ["evaluate", "--experiment", "010", "--jobs", "30"]
    calls = []
    monkeypatch.setattr(quickplay.experiment010, "main", lambda argv: calls.append(argv) or 0)
    assert quickplay.evaluate("010", 5) == 0
    assert calls == [["evaluate", "--jobs", "5"]]


def test_010_recorded_game_in_the_menu(menu):
    seed = _top_seed(REC010, format=0)
    assert menu("10", "2", "", "", "") == [
        "watch-record", REC010, "--seed", str(seed), "--format", "30hz-300ms"]


def test_010_is_listed_and_new_game_uses_the_009_parameters(capsys, monkeypatch, tmp_path):
    assert cli.main(["experiments"]) == 0
    assert "010-complete-reach: reach_plan in 1 tap/reaction formats" in capsys.readouterr().out
    assert quickplay.experiment010.FINAL_PARAMS == quickplay.experiment009.FINAL_PARAMS
    monkeypatch.setattr(quickplay.experiment010, "FINAL_PARAMS", tmp_path / "missing.json")
    assert cli.main(["play-game", "--experiment", "010", "--seed", "3"]) == 1
    assert "no trained parameters" in capsys.readouterr().err


@pytest.mark.integration
def test_watch_record_exports_a_010_game(tmp_path):
    seed = _top_seed(REC010, format=0)
    record = watchrecord.load_record(PROJECT_ROOT / REC010)
    episode = watchrecord.select_episode(record, seed, format_value="30hz-300ms")
    assert watchrecord.export(record, episode, tmp_path / "game.rep").exists()


REC011 = "experiments/011-native-speed/records/run.json.gz"


def test_011_is_wired_into_the_launcher(menu, monkeypatch):
    assert quickplay.experiment_id("11") == "011"
    assert quickplay.record_path("011").name == "run.json.gz"
    assert menu("11", "1", "", "", "", "") == [
        "play-game", "--experiment", "011", "--tap-hz", "30", "--reaction-ms", "300"]
    assert menu("11", "3", "") == ["evaluate", "--experiment", "011", "--jobs", "30"]
    calls = []
    monkeypatch.setattr(quickplay.experiment011, "main", lambda argv: calls.append(argv) or 0)
    assert quickplay.evaluate("011", 5) == 0
    assert calls == [["evaluate", "--jobs", "5"]]


def test_011_recorded_game_in_the_menu(menu):
    seed = _top_seed(REC011, format=0)
    assert menu("11", "2", "", "", "") == [
        "watch-record", REC011, "--seed", str(seed), "--format", "30hz-300ms"]


def test_011_is_listed_and_new_game_uses_the_009_parameters(capsys, monkeypatch, tmp_path):
    assert cli.main(["experiments"]) == 0
    assert "011-native-speed: reach_plan in 1 tap/reaction formats" in capsys.readouterr().out
    assert quickplay.experiment011.FINAL_PARAMS == quickplay.experiment009.FINAL_PARAMS
    monkeypatch.setattr(quickplay.experiment011, "FINAL_PARAMS", tmp_path / "missing.json")
    assert cli.main(["play-game", "--experiment", "011", "--seed", "3"]) == 1
    assert "no trained parameters" in capsys.readouterr().err


@pytest.mark.integration
def test_a_new_011_game_is_the_010_game(monkeypatch):
    shown = []
    monkeypatch.setattr(quickplay.watchrecord, "show",
                        lambda record, episode, path, export_only: shown.append(episode) or 0)
    assert quickplay.play_game("011", seed=12043, frame_limit=3000, export_only=True) == 0
    config = dict(quickplay.experiment011._load(quickplay.experiment011.CONFIG), frame_cap=3000,
                  params=quickplay.experiment011._load(quickplay.experiment011.FINAL_PARAMS)["resolved"])
    python = quickplay.experiment010._play((0, {"tap_hz": 30, "reaction_ms": 300}, 12043, config))
    assert quickplay.experiment011.compare(shown, [python]) == []


REC012 = "experiments/012-native-cem/records/run.json.gz"


def test_012_is_wired_into_the_launcher(menu, monkeypatch):
    assert quickplay.experiment_id("12") == "012"
    assert quickplay.record_path("012").name == "run.json.gz"
    assert menu("12", "1", "", "", "", "") == [
        "play-game", "--experiment", "012", "--tap-hz", "30", "--reaction-ms", "300"]
    assert menu("12", "3", "") == ["evaluate", "--experiment", "012", "--jobs", "30"]
    calls = []
    monkeypatch.setattr(quickplay.experiment012, "main", lambda argv: calls.append(argv) or 0)
    assert quickplay.evaluate("012", 5) == 0
    assert calls == [["evaluate", "--jobs", "5"]]


def test_012_recorded_game_in_the_menu(menu):
    seed = _top_seed(REC012, format=0, agent="cem")
    command = menu("12", "2", "", "", "")
    assert command == ["watch-record", REC012, "--seed", str(seed),
                       "--format", "30hz-300ms", "--agent", "cem"]
    record = watchrecord.load_record(PROJECT_ROOT / REC012)
    episode = watchrecord.select_episode(record, seed, agent="cem", format_value="30hz-300ms")
    assert episode["agent"] == "cem"


def test_012_is_listed_and_new_game_uses_its_own_parameters(capsys, monkeypatch, tmp_path):
    assert cli.main(["experiments"]) == 0
    assert "012-native-cem: reach_plan" in capsys.readouterr().out
    assert "012" in quickplay.TRAINED
    monkeypatch.setattr(quickplay.experiment012, "FINAL_PARAMS", tmp_path / "missing.json")
    assert cli.main(["play-game", "--experiment", "012", "--seed", "3"]) == 1
    assert "no trained parameters" in capsys.readouterr().err


def test_a_new_012_game_plays_its_final_parameters(monkeypatch):
    played = []
    monkeypatch.setattr(quickplay.experiment012, "_play", lambda job: played.append(job) or {
        "seed": job[2], "result": {"lines": 0, "score": 0, "stopping_reason": "test"}})
    monkeypatch.setattr(quickplay.watchrecord, "show", lambda record, episode, path, export_only: 0)
    assert quickplay.play_game("012", seed=5, export_only=True) == 0
    assert played[0][3]["params"] == quickplay.experiment012._load(
        quickplay.experiment012.FINAL_PARAMS)["resolved"]


def test_013_is_wired_into_the_launcher(menu, monkeypatch):
    assert quickplay.experiment_id("13") == "013"
    assert "013" in quickplay.TRAINED and quickplay.RECORD_AGENT["013"] == "deep"
    calls = []
    monkeypatch.setattr(quickplay.experiment013, "main", lambda argv: calls.append(argv) or 0)
    assert quickplay.evaluate("013", 5) == 0
    assert calls == [["evaluate", "--jobs", "5"]]


def test_a_new_013_game_plays_the_deep_agent_with_its_parameters():
    config = quickplay.experiment013._load(quickplay.experiment013.CONFIG)
    params = quickplay.experiment013.cem_params()
    fmt = {"tap_hz": 30, "reaction_ms": 300}
    episode = quickplay.experiment013._play((0, fmt, 7, dict(config, frame_cap=1500,
                                                             params=params)))
    expected = quickplay.experiment013.play_native(
        ("deep", 7, dict(config, frame_cap=1500, deep_params=params, formats=[fmt])))
    assert episode["inputs"] == expected["inputs"] and episode["result"]["frames"] == 1500


def test_014_is_wired_into_the_launcher(menu, monkeypatch):
    assert quickplay.experiment_id("14") == "014"
    assert "014" in quickplay.TRAINED and quickplay.RECORD_AGENT["014"] == "points"
    calls = []
    monkeypatch.setattr(quickplay.experiment014, "main", lambda argv: calls.append(argv) or 0)
    assert quickplay.evaluate("014", 5) == 0
    assert calls == [["evaluate", "--jobs", "5"]]


def test_a_new_014_game_plays_the_points_agent_with_its_parameters():
    e14 = quickplay.experiment014
    config = e14._load(e14.CONFIG)
    params = e14._load(e14.FINAL_PARAMS)["resolved"]
    fmt = {"tap_hz": 30, "reaction_ms": 300}
    episode = e14._play((0, fmt, 7, dict(config, frame_cap=1500, params=params)))
    expected = e14.play_native(
        ("points", 7, dict(config, frame_cap=1500, points_params=params, formats=[fmt])))
    assert episode["inputs"] == expected["inputs"] and episode["result"]["frames"] == 1500
