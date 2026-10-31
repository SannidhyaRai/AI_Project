import threading
import time

import pytest
from fastapi.testclient import TestClient

from dnb.bots import Bot
from dnb.coach import review as review_module
from dnb.engine import GameState
from dnb.server import app as app_module
from dnb.server.app import GAMES, REVIEWS, app

client = TestClient(app)


@pytest.fixture(autouse=True)
def no_real_llm(monkeypatch):
    """Tests never call a real LLM, even on a machine with a key set."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


class HatesLowestEdge(Bot):
    """Scores the lowest legal edge as a blunder, so a player who always plays it always errs."""

    def evaluate_moves(self, state: GameState) -> dict[int, float]:
        legal = state.legal_moves()
        return {m: -1.0 if m == legal[0] else 1.0 for m in legal}


def new_game(**overrides) -> dict:
    body = {"rows": 2, "cols": 2, "bot": "random:seed=0"} | overrides
    return client.post("/api/games", json=body).json()


def finish(game: dict) -> dict:
    """Play the lowest legal edge until the game ends."""
    while not game["is_over"]:
        drawn = {m["edge"] for m in game["moves"]}
        edge = next(e for e in range(12) if e not in drawn)
        game = client.post(f"/api/games/{game['id']}/move", json={"edge": edge}).json()
    return game


def test_hint_returns_a_legal_move():
    game = new_game()
    resp = client.get(f"/api/games/{game['id']}/hint")
    assert resp.status_code == 200, resp.text
    assert resp.json()["move"] in range(12)
    assert resp.json()["score"] == 0.0


def test_no_hint_after_the_game_ends():
    game = finish(new_game())
    assert client.get(f"/api/games/{game['id']}/hint").status_code == 409


def test_danger_lists_moves_that_leave_a_three_sided_box():
    game = new_game()
    state = GameState.new(2, 2)
    for edge in (0, 6):
        state = state.apply(edge)
    GAMES[game["id"]].state = state
    resp = client.get(f"/api/games/{game['id']}/danger")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"edges": [2, 7]}


def test_danger_is_empty_when_the_game_is_over():
    game = finish(new_game())
    assert client.get(f"/api/games/{game['id']}/danger").json() == {"edges": []}


@pytest.mark.parametrize("path", ["hint", "danger", "review"])
def test_unknown_game_is_404(path):
    assert client.get(f"/api/games/nope/{path}").status_code == 404


def test_no_review_until_the_game_ends():
    game = new_game()
    assert client.get(f"/api/games/{game['id']}/review").status_code == 409


def test_review_covers_only_the_humans_moves():
    game = finish(new_game())
    resp = client.get(f"/api/games/{game['id']}/review")
    assert resp.status_code == 200, resp.text
    review = resp.json()
    human_plies = [i for i, m in enumerate(game["moves"]) if m["player"] == game["human_player"]]
    assert review["game_id"] == game["id"]
    assert [m["ply"] for m in review["moves"]] == human_plies
    assert {m["label"] for m in review["moves"]} == {"good"}  # the random bot scores all moves 0
    assert all(m["explanation"] is None for m in review["moves"])


def test_review_explains_only_the_biggest_mistakes(monkeypatch):
    monkeypatch.setattr(review_module, "make_bot", lambda spec: HatesLowestEdge())
    game = finish(new_game())
    moves = client.get(f"/api/games/{game['id']}/review").json()["moves"]
    assert {m["label"] for m in moves} == {"mistake"}
    assert 0 < sum(m["explanation"] is not None for m in moves) <= 3


def test_review_works_after_a_server_restart():
    game = finish(new_game())
    before = client.get(f"/api/games/{game['id']}/review").json()
    GAMES.clear()
    REVIEWS.clear()
    assert client.get(f"/api/games/{game['id']}/review").json() == before


def test_a_game_is_only_reviewed_once(monkeypatch):
    calls = []

    def slow_review(*args):
        calls.append(args)
        time.sleep(0.05)
        return []

    monkeypatch.setattr(app_module, "review_game", slow_review)
    game = finish(new_game())
    url = f"/api/games/{game['id']}/review"
    threads = [threading.Thread(target=client.get, args=(url,)) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert client.get(url).status_code == 200
    assert len(calls) == 1
