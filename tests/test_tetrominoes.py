from tetris.tetrominoes import list_of_tetrominoes, rotate, shape_str


def by_name(name):
    return next(t for t in list_of_tetrominoes if t.name == name)


def test_all_seven_tetrominoes_are_defined():
    assert len(list_of_tetrominoes) == 7
    assert {t.name for t in list_of_tetrominoes} == {
        "long",
        "square",
        "hat",
        "right_snake",
        "left_snake",
        "left_gun",
        "right_gun",
    }


def test_four_rotations_return_to_original():
    for tetromino in list_of_tetrominoes:
        assert rotate(tetromino.shape, 4) == tetromino.shape


def test_square_is_rotation_invariant():
    square = by_name("square")
    assert rotate(square.shape) == square.shape


def test_hat_rotations():
    hat = by_name("hat")
    assert rotate(hat.shape) == (
        (None, "X", None),
        (None, "X", "X"),
        (None, "X", None),
    )
    assert rotate(hat.shape, 2) == (
        (None, None, None),
        ("X", "X", "X"),
        (None, "X", None),
    )


def test_shape_str():
    hat = by_name("hat")
    assert shape_str(hat.shape) == "OXO\nXXX\nOOO"
