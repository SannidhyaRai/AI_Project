import pytest

from dnb.engine import GameState, IllegalMoveError, edge_coords, h_edge, layout, v_edge


def test_edge_counts():
    lay = layout(3, 3)
    assert lay.num_edges == 24
    assert lay.num_boxes == 9
    assert len(GameState.new(3, 3).legal_moves()) == 24


def test_edge_coords_round_trip():
    rows, cols = 2, 3
    for e in range(layout(rows, cols).num_edges):
        kind, r, c = edge_coords(rows, cols, e)
        assert (h_edge if kind == "h" else v_edge)(rows, cols, r, c) == e


def test_turn_passes_when_no_box_completed():
    s = GameState.new(2, 2).apply(0)
    assert s.current_player == 1


def test_completing_a_box_gives_an_extra_turn():
    # 2x2 board, box 0 has edges top=0, bottom=2, left=6, right=7
    s = GameState.new(2, 2)
    for e in (0, 2, 6):  # players alternate: 0, 1, 0
        s = s.apply(e)
    assert s.current_player == 1
    s = s.apply(7)
    assert s.scores == (0, 1)
    assert s.owners[0] == 1
    assert s.current_player == 1  # same player moves again


def test_one_edge_can_complete_two_boxes():
    # The example from the brief: 1x2 board, middle edge (5) finishes both boxes.
    s = GameState.new(1, 2)
    for e in (0, 1, 2, 3, 4, 6):
        s = s.apply(e)
    mover = s.current_player
    s = s.apply(5)
    assert s.scores[mover] == 2
    assert s.is_over()
    assert s.winner() == mover


def test_illegal_moves():
    s = GameState.new(2, 2).apply(0)
    with pytest.raises(IllegalMoveError):
        s.apply(0)
    with pytest.raises(IllegalMoveError):
        s.apply(99)


def test_state_is_immutable():
    s = GameState.new(2, 2)
    s.apply(0)
    assert s.drawn == 0


@pytest.mark.parametrize("rows,cols", [(1, 1), (1, 7), (7, 1), (2, 3), (7, 7)])
def test_geometry_and_every_move_in_a_full_game(rows, cols):
    state = GameState.new(rows, cols)
    lay = state.layout
    assert lay.num_edges == (rows + 1) * cols + rows * (cols + 1)
    for edge in range(lay.num_edges):
        kind, r, c = edge_coords(rows, cols, edge)
        assert (h_edge if kind == "h" else v_edge)(rows, cols, r, c) == edge
        assert len(lay.edge_boxes[edge]) in (1, 2)
        before = state
        mover = before.current_player
        completed = before.boxes_completed_by(edge)
        state = before.apply(edge)
        assert not before.is_drawn(edge)
        assert state.is_drawn(edge)
        assert state.scores[mover] == before.scores[mover] + completed
        assert state.scores[1 - mover] == before.scores[1 - mover]
        assert state.current_player == (mover if completed else 1 - mover)
        assert sum(state.scores) == sum(owner != -1 for owner in state.owners)
        for box, owner in enumerate(state.owners):
            assert (owner != -1) == (state.sides(box) == 4)
        assert len(state.legal_moves()) + len(state.drawn_edges()) == lay.num_edges
    assert state.is_over()
    assert sum(state.scores) == rows * cols
    assert state.legal_moves() == []
    with pytest.raises(IllegalMoveError):
        state.apply(0)


@pytest.mark.parametrize("size", [(0, 1), (1, 0), (-1, 2), (2, -1)])
def test_invalid_board_dimensions(size):
    with pytest.raises(ValueError):
        GameState.new(*size)


def test_negative_edge_is_illegal():
    with pytest.raises(IllegalMoveError):
        GameState.new().apply(-1)


def test_tied_game_has_no_winner_and_single_box_is_won():
    state = GameState.new(1, 2)
    assert state.winner() is None
    for move in (0, 2, 4, 1, 5, 3, 6):
        state = state.apply(move)
    assert state.scores == (1, 1)
    assert state.is_over()
    assert state.winner() is None
    state = GameState.new(1, 1)
    for move in (0, 1, 2, 3):
        state = state.apply(move)
    assert state.scores == (0, 1)
    assert state.winner() == 1
