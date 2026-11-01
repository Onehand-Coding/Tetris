from tetris.game import (
    remove_full_lines,
    score_for_lines,
    should_level_up,
)

WIDTH = 10
HEIGHT = 22


def blank_matrix():
    return {(y, x): None for y in range(HEIGHT) for x in range(WIDTH)}


def test_remove_full_line_shifts_rows_down():
    matrix = blank_matrix()
    for x in range(WIDTH):
        matrix[(21, x)] = "block"
    matrix[(20, 0)] = "block"

    result, lines = remove_full_lines(matrix)

    assert lines == 1
    assert result[(21, 0)] == "block"
    assert all(result[(20, x)] is None for x in range(WIDTH))


def test_remove_multiple_lines():
    matrix = blank_matrix()
    for y in (20, 21):
        for x in range(WIDTH):
            matrix[(y, x)] = "block"

    _, lines = remove_full_lines(matrix)

    assert lines == 2


def test_partial_rows_are_not_cleared():
    matrix = blank_matrix()
    for x in range(WIDTH - 1):
        matrix[(21, x)] = "block"

    _, lines = remove_full_lines(matrix)

    assert lines == 0


def test_score_for_lines():
    assert score_for_lines(0, 1) == 0
    assert score_for_lines(1, 1) == 100
    assert score_for_lines(2, 1) == 400
    assert score_for_lines(4, 2) == 3200


def test_should_level_up():
    assert should_level_up(9, 1) is False
    assert should_level_up(10, 1) is True
    assert should_level_up(19, 2) is False
    assert should_level_up(20, 2) is True
