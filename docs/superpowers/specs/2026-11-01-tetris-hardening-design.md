# Tetris Hardening Design

Date: 2026-11-01
Status: Draft for user review
Repo: https://github.com/Onehand-Coding/Tetris

## Context

The repository is an inactive public Pygame Tetris game from September 2025. The
game is complete enough to play, but it has no real test suite and several
maintenance defects.

Known defects:

- `pyproject.toml` points Hatch's test script at `tests`, but the directory does
  not exist.
- `src/tetrominoes.py` contains a `test()` function that references undefined
  names (`T_left_snake`, `T_square`, `T_right_snake`, `T_hat`), so the self-test
  crashes.
- `scores.py` writes `.highscores` inside the installed package directory. That
  fails for read-only site-packages and mixes user data with source.
- Game rules, rendering, event handling, and scoring live in a 977-line
  `__main__.py`. Line clearing and scoring cannot be tested without a pygame
  display.
- There is no CI, no pytest configuration, and no `dev` dependency group.
- The README mentions Hatch and Black while the npm-style scripts and CI are not
  present.

## Goals

1. Extract testable game rules: line clearing, scoring, and level progression.
2. Fix the broken tetromino definitions and self-test.
3. Move high scores to a user-writable directory with an environment override.
4. Add a real pytest suite for tetrominoes, scores, rules, and board operations.
5. Add CI, pytest/Ruff configuration, and accurate documentation.

## Non-goals

- Rewriting the menu or rendering layer.
- Replacing pygame or the kezmenu library.
- Adding new gameplay features, modes, or art.
- Changing the visual design or sound system.
- Achieving pixel-perfect visual regression tests.

## Architecture

Target files:

```
src/tetris/
  __main__.py       # pygame loop, Matris view/controller, menu integration
  game.py           # pure line-clear, scoring, and level helpers
  tetrominoes.py    # shapes and rotation (self-test removed)
  scores.py         # user data directory and high score persistence
tests/
  conftest.py
  test_game.py
  test_tetrominoes.py
  test_scores.py
  test_matris.py
.github/workflows/ci.yml
README.md
CONTEXT.md
```

Responsibilities:

- `game.py`: no pygame imports. Owns line clearing, scoring, and level checks.
- `tetrominoes.py`: shape definitions and rotation only.
- `scores.py`: user data path resolution and score file I/O.
- `__main__.py`: pygame rendering, input, and `Matris` state. It calls the pure
  helpers in `game.py` and the score helpers.
- Tests: pure rules and board operations. Pygame tests use the dummy SDL driver
  and avoid opening a window.

## Line clearing

Extract the existing algorithm into `game.py`:

```python
def remove_full_lines(matrix, width=MATRIX_WIDTH, height=MATRIX_HEIGHT):
    lines = [y for y in range(height) if all(matrix.get((y, x)) for x in range(width))]
    for line in sorted(lines):
        for x in range(width):
            matrix[(line, x)] = None
        for y in range(line, -1, -1):
            for x in range(width):
                matrix[(y, x)] = matrix.get((y - 1, x), None)
    return matrix, len(lines)
```

The returned matrix preserves the existing mutation behavior. Tests cover zero,
one, two, and four cleared lines, partial rows, and rows shifting down.

## Scoring and levels

Extract:

```python
def score_for_lines(lines_cleared: int, combo: int) -> int:
    if lines_cleared <= 0:
        return 0
    return 100 * (lines_cleared**2) * combo


def should_level_up(total_lines: int, current_level: int) -> bool:
    return total_lines >= current_level * 10
```

`Matris.lock_tetromino` uses both helpers. The existing hard-drop score of ten
points per row remains in `hard_drop`.

## Tetrominoes

- Keep the seven tetrominoes and their names/colors.
- Remove the broken `test()` function.
- Add pytest tests for shape definitions, four-rotation identity, square
  invariance, hat rotation, and `shape_str` output.
- Keep `rotate` and `shape_str` behavior unchanged.

## High scores

`scores.py` gains:

```python
def get_data_dir() -> Path:
    override = os.getenv("TETRIS_DATA_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".local" / "share" / "tetris"


def get_score_file() -> Path:
    return get_data_dir() / "highscores.txt"
```

- `load_score(score_file=None)`, `load_high_scores(count=5, score_file=None)`,
  and `write_score(score, score_file=None)` accept an optional path for tests.
- `write_score` creates parent directories lazily and appends one score per
  line.
- Missing or unreadable files return `0` or an empty list.
- Non-numeric lines are ignored.
- Scores are sorted descending.
- No score file is written into the package.
- `Matris` continues to call `load_score()` and `write_score(self.score)` with
  the default path.

## Matris tests

Use `Matris.__new__` to avoid creating a display. Set the matrix,
current tetromino, position, rotation, dummy block surfaces, and mock sounds.

Tests:

- `fits_in_matrix` accepts an empty board and rejects out-of-bounds shapes.
- `blend` places a piece and rejects collisions.
- `request_movement` moves left, right, and down; rejects blocked and
  out-of-bounds moves.
- `request_rotation` rotates a square, updates state, and rejects collisions.
- `remove_lines` delegates to `remove_full_lines`.
- `place_shadow` returns the column at the lowest valid row.

## Tooling and CI

`pyproject.toml`:

- Add a `dev` optional dependency group with `pytest`, `pytest-mock`, and `ruff`.
- Add `[tool.pytest.ini_options]` with `testpaths = ["tests"]`.
- Replace the legacy Ruff configuration with:

```toml
[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
ignore = ["E501"]
```

- Keep the Hatch build configuration and console script.
- Remove the Black-oriented README instructions; Ruff format is the formatter.

`.github/workflows/ci.yml`:

1. Checkout.
2. Set up Python 3.12.
3. Set up uv.
4. Set `SDL_VIDEODRIVER=dummy` and `SDL_AUDIODRIVER=dummy`.
5. `uv sync --extra dev`.
6. `uv run ruff check .`.
7. `uv run ruff format --check .`.
8. `uv run pytest`.
9. `uv build` and verify the wheel contains `tetris/resources/sounds/background.wav`.

## Documentation

- README:
  - Add a CI badge.
  - Document high score location and `TETRIS_DATA_DIR`.
  - Replace Hatch/Black development instructions with uv, Ruff, and pytest.
  - Keep controls, features, screenshots, and install steps.
- `CONTEXT.md`: architecture, rules, score storage, commands, gotchas.

## Acceptance criteria

1. The broken tetromino self-test is removed and tetromino behavior is covered by
   pytest.
2. Line clearing, scoring, and level checks are pure helpers with tests.
3. High scores are stored under `~/.local/share/tetris` by default and honor
   `TETRIS_DATA_DIR`.
4. No score file is written inside the package.
5. `ruff check`, `ruff format --check`, and `pytest` pass locally and in CI.
6. The wheel contains the sound resources used by `get_sound`.
7. README and CONTEXT match the implementation.
8. The game still launches through `uv run tetris`.

## Risks and mitigations

- Pygame needs a dummy SDL driver in tests. Set it in `conftest.py` and CI.
- Refactoring scoring could change gameplay. Keep the formulas identical and
  test the existing thresholds.
- The 977-line `__main__.py` is risky to edit broadly. Limit changes to the
  import and three helper calls.
- User data migration is not required; existing package-local scores are not
  migrated.
