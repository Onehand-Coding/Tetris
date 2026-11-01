from unittest.mock import MagicMock

import pytest

from tetris import __main__ as tetris_main
from tetris import scores
from tetris.tetrominoes import list_of_tetrominoes


def by_name(name):
    return next(t for t in list_of_tetrominoes if t.name == name)


def blank_matrix():
    return {
        (y, x): None
        for y in range(tetris_main.MATRIX_HEIGHT)
        for x in range(tetris_main.MATRIX_WIDTH)
    }


def make_matris(piece="square", position=(0, 0)):
    matris = tetris_main.Matris.__new__(tetris_main.Matris)
    matris.matrix = blank_matrix()
    matris.current_tetromino = by_name(piece)
    matris.tetromino_rotation = 0
    matris.tetromino_position = position
    matris.tetromino_block = object()
    matris.shadow_block = object()
    matris.lateralmove_sound = MagicMock()
    matris.rotate_sound = MagicMock()
    matris.needs_redraw = False
    return matris


def test_fits_in_matrix_accepts_empty_board():
    matris = make_matris()
    shape = matris.current_tetromino.shape
    assert matris.fits_in_matrix(shape, (0, 0)) == (0, 0)


def test_fits_in_matrix_rejects_out_of_bounds():
    matris = make_matris()
    shape = matris.current_tetromino.shape
    assert matris.fits_in_matrix(shape, (21, 0)) is False


def test_blend_places_piece():
    matris = make_matris()
    blended = matris.blend(shape=matris.current_tetromino.shape, position=(0, 0))
    assert blended[(0, 0)][0] == "block"


def test_blend_rejects_collision():
    matris = make_matris()
    matris.matrix[(1, 0)] = ("block", object())
    assert matris.blend(shape=matris.current_tetromino.shape, position=(0, 0)) is False


def test_request_movement_left_right_down():
    matris = make_matris()
    assert matris.request_movement("right") == (0, 1)
    assert matris.request_movement("left") == (0, 0)
    assert matris.request_movement("down") == (1, 0)
    assert matris.lateralmove_sound.play.called
    assert matris.needs_redraw is True


def test_request_movement_rejects_out_of_bounds():
    matris = make_matris(position=(0, 0))
    assert matris.request_movement("left") is False


def test_request_movement_rejects_blocked_cell():
    matris = make_matris()
    matris.matrix[(0, 1)] = ("block", object())
    assert matris.request_movement("right") is False


def test_request_rotation_rejects_blocked_shape():
    matris = make_matris("square", (0, 0))
    matris.blend = MagicMock(return_value=False)

    assert matris.request_rotation() is False
    assert matris.rotate_sound.play.called is False


def test_request_rotation_square():
    matris = make_matris("square", (0, 0))
    assert matris.request_rotation() == 1
    assert matris.tetromino_rotation == 1
    assert matris.rotate_sound.play.called
    assert matris.needs_redraw is True


def test_remove_lines_clears_full_row():
    matris = make_matris()
    for x in range(tetris_main.MATRIX_WIDTH):
        matris.matrix[(21, x)] = ("block", object())

    assert matris.remove_lines() == 1
    assert all(matris.matrix[(21, x)] is None for x in range(tetris_main.MATRIX_WIDTH))


def test_place_shadow_stops_above_floor():
    matris = make_matris("square", (0, 0))
    shadow = matris.place_shadow()

    assert shadow[(21, 0)][0] == "shadow"


def make_lock_matris():
    matris = make_matris()
    matris.blend = MagicMock(return_value=matris.matrix)
    matris.remove_lines = MagicMock(return_value=2)
    matris.set_tetrominoes = MagicMock()
    matris.gameover = MagicMock()
    matris.clear_sound = MagicMock()
    matris.tetris_sound = MagicMock()
    matris.drop_sound = MagicMock()
    matris.levelup_sound = MagicMock()
    matris.highscorebeaten_sound = MagicMock()
    matris.lines = 0
    matris.score = 0
    matris.combo = 1
    matris.level = 1
    matris.highscore = 1000
    matris.played_highscorebeaten_sound = False
    matris.hard_drop_occurred = False
    matris.needs_redraw = False
    return matris


def test_lock_tetromino_scores_and_advances():
    matris = make_lock_matris()

    matris.lock_tetromino()

    assert matris.score == 400
    assert matris.lines == 2
    assert matris.combo == 2
    matris.set_tetrominoes.assert_called_once()
    assert matris.needs_redraw is True


def test_gameover_writes_score():
    matris = make_matris()
    matris.score = 321

    with pytest.raises(tetris_main.GameOver):
        matris.gameover()

    assert scores.load_score() == 321


def test_gameover_ignores_write_failure(monkeypatch):
    matris = make_matris()
    matris.score = 1
    monkeypatch.setattr(
        tetris_main, "write_score", MagicMock(side_effect=OSError("read-only"))
    )

    with pytest.raises(tetris_main.GameOver):
        matris.gameover()
