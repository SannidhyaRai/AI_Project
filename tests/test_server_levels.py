"""Level-based games, the levels list and the stats endpoint (Person 5)."""

import pytest
from fastapi.testclient import TestClient

from dnb.difficulty.stats import PlayerStats
from dnb.server import app as app_module
from dnb.server.app import app, bot_available

client = TestClient(app)

TEST_LEVELS = {
    1: {"name": "Easy", "bot": "random:seed=1"},
    2: {"name": "Medium", "bot": "greedy"},
    3: {"name": "Unfinished", "bot": "montecarlo:sims=10"},
    4: {"name": "Typo", "bot": "nope"},
}


@pytest.fixture(autouse=True)
def fixed_levels(monkeypatch):
    """A fixed level table, so these tests don't break when Person 3 tunes the real one."""
    monkeypatch.setattr(app_module, "LEVELS", TEST_LEVELS)
    # MonteCarloBot is a stub today; pretend so explicitly in case Person 2 has shipped it.
    monkeypatch.setattr(app_module, "bot_available", lambda spec: spec_ok(spec))


def spec_ok(spec: str) -> bool:
    return not spec.startswith(("montecarlo", "nope"))


def test_levels_list_marks_unfinished_bots():
    resp = client.get("/api/levels")
    assert resp.status_code == 200, resp.text
    assert resp.json() == [
        {"level": 1, "name": "Easy", "bot": "random:seed=1", "available": True},
        {"level": 2, "name": "Medium", "bot": "greedy", "available": True},
        {"level": 3, "name": "Unfinished", "bot": "montecarlo:sims=10", "available": False},
        {"level": 4, "name": "Typo", "bot": "nope", "available": False},
    ]


def test_level_picks_the_bot_and_is_reported_back():
    resp = client.post("/api/games", json={"rows": 2, "cols": 2, "level": 2, "bot": "random"})
    assert resp.status_code == 200, resp.text
    game = resp.json()
    assert game["level"] == 2
    assert game["bot"] == "greedy"


def test_game_without_level_uses_the_bot_spec():
    game = client.post("/api/games", json={"rows": 2, "cols": 2, "bot": "greedy"}).json()
    assert game["level"] is None
    assert game["bot"] == "greedy"


def test_unknown_level_is_rejected():
    assert client.post("/api/games", json={"level": 99}).status_code == 400


def test_level_with_unfinished_bot_is_501_not_a_crash():
    assert client.post("/api/games", json={"level": 3}).status_code == 501


def test_bot_moving_first_works_with_levels():
    resp = client.post("/api/games", json={"rows": 2, "cols": 2, "level": 2, "human_first": False})
    game = resp.json()
    assert game["human_player"] == 1
    assert game["current_player"] == 1
    assert len(game["moves"]) >= 1


def test_stats_are_501_until_person3_ships_them(monkeypatch):
    def not_yet(player_id):
        raise NotImplementedError

    monkeypatch.setattr(app_module, "compute_stats", not_yet)
    assert client.get("/api/players/guest/stats").status_code == 501


def test_stats_pass_through(monkeypatch):
    stats = PlayerStats(
        games_played=4, win_rate=0.5, boxes_given_away_per_game=1.25, rating=1016.0, level=3
    )
    monkeypatch.setattr(app_module, "compute_stats", lambda player_id: stats)
    resp = client.get("/api/players/alice/stats")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "player_id": "alice",
        "games_played": 4,
        "win_rate": 0.5,
        "boxes_given_away_per_game": 1.25,
        "rating": 1016.0,
        "level": 3,
    }


def test_empty_player_id_is_rejected():
    assert client.post("/api/games", json={"player_id": ""}).status_code == 422


def test_bot_available_probes_real_bots():
    assert bot_available("random")
    assert bot_available("greedy")
    assert bot_available("minimax:depth=2")
    assert not bot_available("nope")
    assert not bot_available("greedy:not_an_option=1")
