import pytest
from fastapi.testclient import TestClient

from dnb.bots import make_bot
from dnb.coach.hints import hint
from dnb.coach.review import review_game
from dnb.engine import GameState
from dnb.server.app import GAMES, app


@pytest.mark.parametrize("spec", ["greedy:seed=0,randomness=0.3", "minimax:depth=3"])
@pytest.mark.parametrize("human_first", [True, False])
def test_existing_http_contract_can_play_full_games_with_person1_bots(spec, human_first):
    with TestClient(app) as client:
        response = client.post(
            "/api/games",
            json={"rows": 2, "cols": 2, "bot": spec, "human_first": human_first},
        )
        assert response.status_code == 200, response.text
        game = response.json()
        try:
            while not game["is_over"]:
                assert game["current_player"] == game["human_player"]
                drawn = {m["edge"] for m in game["moves"]}
                edge = next(e for e in range(12) if e not in drawn)
                response = client.post(f"/api/games/{game['id']}/move", json={"edge": edge})
                assert response.status_code == 200, response.text
                game = response.json()
            assert sum(game["scores"]) == 4
            assert len(game["moves"]) == 12
        finally:
            GAMES.pop(game["id"], None)


def test_person4_hint_and_review_accept_minimax_without_interface_changes():
    state = GameState.new(1, 2)
    for edge in (0, 2, 4, 1, 3):
        state = state.apply(edge)
    bot = make_bot("minimax:depth=7")
    assert hint(state, bot=bot).move == 5
    moves = [(0, 0), (1, 2), (0, 4), (1, 1), (0, 3), (1, 6), (0, 5)]
    review = review_game(1, 2, moves, human=1, bot=bot)[-1]
    assert review.label == "mistake"
    assert review.score == -1.0
    assert review.best_score == 1.0


@pytest.mark.parametrize("spec", ["greedy:randomness=1.1", "minimax:depth=0"])
def test_invalid_bot_settings_use_the_existing_http_error_contract(spec):
    with TestClient(app) as client:
        response = client.post("/api/games", json={"bot": spec})
        assert response.status_code == 400
