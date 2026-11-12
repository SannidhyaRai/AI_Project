"""Game history endpoints: a player's recent games, and finished games after a restart."""

from fastapi.testclient import TestClient

from dnb.server.app import GAMES, app

client = TestClient(app)


def play_out(player_id: str = "alice", **overrides) -> dict:
    body = {"rows": 2, "cols": 2, "bot": "random:seed=0", "player_id": player_id} | overrides
    game = client.post("/api/games", json=body).json()
    while not game["is_over"]:
        drawn = {m["edge"] for m in game["moves"]}
        edge = next(e for e in range(12) if e not in drawn)
        game = client.post(f"/api/games/{game['id']}/move", json={"edge": edge}).json()
    return game


def test_recent_games_are_newest_first_and_per_player():
    first = play_out()
    second = play_out(bot="greedy")
    play_out(player_id="bob")
    games = client.get("/api/players/alice/games").json()
    assert [g["id"] for g in games] == [second["id"], first["id"]]
    assert games[0]["bot"] == "greedy"
    assert games[0]["score_human"] == second["scores"][second["human_player"]]
    assert games[0]["score_human"] + games[0]["score_bot"] == 4
    assert games[0]["result"] in (0.0, 0.5, 1.0)


def test_recent_games_limit():
    for _ in range(3):
        play_out()
    assert len(client.get("/api/players/alice/games?limit=2").json()) == 2
    assert client.get("/api/players/alice/games?limit=0").status_code == 422


def test_unfinished_games_are_not_in_history():
    client.post("/api/games", json={"rows": 2, "cols": 2, "player_id": "carol"})
    assert client.get("/api/players/carol/games").json() == []


def test_finished_game_can_be_opened_after_a_restart():
    game = play_out()
    GAMES.clear()
    resp = client.get(f"/api/games/{game['id']}")
    assert resp.status_code == 200, resp.text
    assert resp.json() == game


def test_unknown_game_is_404():
    assert client.get("/api/games/nope").status_code == 404
