# Tetris Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden Tetris by extracting testable game rules, fixing broken tetromino tests, moving high scores to user data, adding a real pytest suite and CI, and updating docs.

**Architecture:** Add a pygame-free `game.py` for line clearing, scoring, and level checks. Keep `Matris` as the pygame board/controller. Move score persistence to a user data directory. Tests use `Matris.__new__` and dummy SDL drivers, so no window is opened.

**Tech Stack:** Python 3.11+, pygame, pytest, pytest-mock, ruff, uv, GitHub Actions.

**Git policy:** Do not run `git commit`, `git push`, or `git add` unless the user explicitly asks.

---

## File Map

Create or replace:

- `src/tetris/game.py`
- `src/tetris/scores.py`
- `src/tetris/tetrominoes.py`
- `src/tetris/__main__.py` (small edits only)
- `pyproject.toml`
- `.github/workflows/ci.yml`
- `tests/conftest.py`
- `tests/test_game.py`
- `tests/test_scores.py`
- `tests/test_tetrominoes.py`
- `tests/test_matris.py`
- `README.md`
- `CONTEXT.md`

Do not touch:

- `LICENSE`
- Sound or image resources.
- The menu and rendering design.

---

## Task 1: Tooling, Test Bootstrap, and Score Storage

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_scores.py`
- Replace: `src/tetris/scores.py`
- Modify: `pyproject.toml`
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write the failing score tests**

Create `tests/conftest.py`:

```python
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pytest


@pytest.fixture(autouse=True)
def isolate_scores(monkeypatch, tmp_path):
    monkeypatch.setenv("TETRIS_DATA_DIR", str(tmp_path / "data"))
```

Create `tests/test_scores.py`:

```python
from tetris import scores


def test_default_data_dir_from_env(monkeypatch, tmp_path):
    monkeypatch.setenv("TETRIS_DATA_DIR", str(tmp_path))
    assert scores.get_data_dir() == tmp_path
    assert scores.get_score_file() == tmp_path / "highscores.txt"


def test_load_missing_file_returns_zero(tmp_path):
    path = tmp_path / "missing.txt"
    assert scores.load_score(path) == 0
    assert scores.load_high_scores(score_file=path) == []


def test_write_and_load_scores(tmp_path):
    path = tmp_path / "scores.txt"
    scores.write_score(100, path)
    scores.write_score(300, path)
    scores.write_score(200, path)

    assert scores.load_score(path) == 300
    assert scores.load_high_scores(2, path) == [300, 200]


def test_invalid_lines_are_ignored(tmp_path):
    path = tmp_path / "scores.txt"
    path.write_text("100\nnot-a-score\n\n50\n")

    assert scores.load_high_scores(score_file=path) == [100, 50]


def test_write_creates_parent_directories(tmp_path):
    path = tmp_path / "nested" / "scores.txt"
    scores.write_score(10, path)
    assert path.exists()
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv sync --extra dev
uv run pytest tests/test_scores.py -q
```

Expected: FAIL because `get_data_dir`, `get_score_file`, and the path arguments do not exist.

- [ ] **Step 3: Replace `scores.py`**

```python
from __future__ import annotations

import os
from pathlib import Path


def get_data_dir() -> Path:
    override = os.getenv("TETRIS_DATA_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".local" / "share" / "tetris"


def get_score_file() -> Path:
    return get_data_dir() / "highscores.txt"


def _score_path(score_file: Path | None) -> Path:
    return Path(score_file) if score_file is not None else get_score_file()


def load_scores(score_file: Path | None = None) -> list[int]:
    path = _score_path(score_file)
    try:
        with path.open(encoding="utf-8") as file:
            return sorted(
                (int(line.strip()) for line in file if line.strip().isdigit()),
                reverse=True,
            )
    except OSError:
        return []


def load_score(score_file: Path | None = None) -> int:
    scores = load_scores(score_file)
    return scores[0] if scores else 0


def load_high_scores(count: int = 5, score_file: Path | None = None) -> list[int]:
    return load_scores(score_file)[:count]


def write_score(score: int, score_file: Path | None = None) -> None:
    path = _score_path(score_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(f"{score}\n")
```

- [ ] **Step 4: Update `pyproject.toml`**

Add a dev dependency group after the main dependencies:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.4",
    "pytest-mock>=3.14",
    "ruff>=0.6",
]
```

Add pytest configuration:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"
```

Replace the old `[tool.black]` and Ruff blocks with:

```toml
[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
ignore = ["E501"]
```

Keep the Hatch build and console-script sections.

- [ ] **Step 5: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    env:
      SDL_VIDEODRIVER: dummy
      SDL_AUDIODRIVER: dummy
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Set up uv
        uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Lint
        run: uv run ruff check .

      - name: Format check
        run: uv run ruff format --check .

      - name: Test
        run: uv run pytest

      - name: Build wheel
        run: uv build

      - name: Check wheel contents
        run: |
          python -m zipfile -l dist/*.whl | grep tetris/resources/sounds/background.wav
```

- [ ] **Step 6: Run the score tests**

Run:

```bash
uv run pytest tests/test_scores.py -q
```

Expected: 5 passed.

---

## Task 2: Pure Game Rules

**Files:**
- Create: `src/tetris/game.py`
- Create: `tests/test_game.py`

- [ ] **Step 1: Write the failing rule tests**

Create `tests/test_game.py`:

```python
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
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/test_game.py -q
```

Expected: FAIL because `tetris.game` does not exist.

- [ ] **Step 3: Create `game.py`**

```python
from __future__ import annotations

MATRIX_WIDTH = 10
MATRIX_HEIGHT = 22


def remove_full_lines(
    matrix: dict[tuple[int, int], object],
    width: int = MATRIX_WIDTH,
    height: int = MATRIX_HEIGHT,
) -> tuple[dict[tuple[int, int], object], int]:
    lines = [y for y in range(height) if all(matrix.get((y, x)) for x in range(width))]
    for line in sorted(lines):
        for x in range(width):
            matrix[(line, x)] = None
        for y in range(line, -1, -1):
            for x in range(width):
                matrix[(y, x)] = matrix.get((y - 1, x), None)
    return matrix, len(lines)


def score_for_lines(lines_cleared: int, combo: int) -> int:
    if lines_cleared <= 0:
        return 0
    return 100 * (lines_cleared**2) * combo


def should_level_up(total_lines: int, current_level: int) -> bool:
    return total_lines >= current_level * 10
```

- [ ] **Step 4: Run the rule tests**

Run:

```bash
uv run pytest tests/test_game.py -q
```

Expected: 5 passed.

---

## Task 3: Tetromino Fixes

**Files:**
- Replace: `src/tetris/tetrominoes.py`
- Create: `tests/test_tetrominoes.py`

- [ ] **Step 1: Write the failing tetromino tests**

Create `tests/test_tetrominoes.py`:

```python
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
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/test_tetrominoes.py -q
```

Expected: FAIL because the self-test references undefined names and the rotation
expectations have not been verified.

- [ ] **Step 3: Replace `tetrominoes.py`**

```python
from __future__ import annotations

from collections import namedtuple

X, O = "X", None
Tetromino = namedtuple("Tetromino", "name color shape")
list_of_tetrominoes = [
    Tetromino(
        name="long",
        color="blue",
        shape=((O, O, O, O), (X, X, X, X), (O, O, O, O), (O, O, O, O)),
    ),
    Tetromino(name="square", color="yellow", shape=((X, X), (X, X))),
    Tetromino(
        name="hat",
        color="pink",
        shape=((O, X, O), (X, X, X), (O, O, O)),
    ),
    Tetromino(
        name="right_snake",
        color="green",
        shape=((O, X, X), (X, X, O), (O, O, O)),
    ),
    Tetromino(
        name="left_snake",
        color="red",
        shape=((X, X, O), (O, X, X), (O, O, O)),
    ),
    Tetromino(
        name="left_gun",
        color="cyan",
        shape=((X, O, O), (X, X, X), (O, O, O)),
    ),
    Tetromino(
        name="right_gun",
        color="orange",
        shape=((O, O, X), (X, X, X), (O, O, O)),
    ),
]


def rotate(shape, times=1):
    """Rotate a shape to the right."""
    return shape if times == 0 else rotate(tuple(zip(*shape[::-1])), times - 1)


def shape_str(shape):
    """Return a human-readable string of a shape."""
    return "\n".join(
        "".join({"X": "X", None: "O"}.get(cell) for cell in line) for line in shape
    )


def shape(shape):
    """Print a shape in human-readable form."""
    print(shape_str(shape))
```

- [ ] **Step 4: Run the tetromino tests**

Run:

```bash
uv run pytest tests/test_tetrominoes.py -q
```

Expected: 5 passed.

## Task 4: Wire the Pure Rules into Matris and Test the Board

**Files:**
- Modify: `src/tetris/__main__.py`
- Create: `tests/test_matris.py`

- [ ] **Step 1: Write the failing Matris tests**

Create `tests/test_matris.py`:

```python
from unittest.mock import MagicMock

from tetris import __main__ as tetris_main
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


def test_fits_in_matrix_rejects_collision():
    matris = make_matris()
    matris.matrix[(1, 0)] = ("block", object())
    shape = matris.current_tetromino.shape
    assert matris.fits_in_matrix(shape, (0, 0)) is False


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
```

- [ ] **Step 2: Run the tests and verify they fail or expose coupling**

Run:

```bash
uv run pytest tests/test_matris.py -q
```

Expected: tests reach the board methods; `remove_lines` may pass because it is
still inline. The tests establish the interface before the refactor.

- [ ] **Step 3: Update `__main__.py`**

Add the import near the other local imports:

```python
from .game import remove_full_lines, score_for_lines, should_level_up
```

Replace `Matris.remove_lines`:

```python
    def remove_lines(self):
        self.matrix, lines_cleared = remove_full_lines(
            self.matrix, MATRIX_WIDTH, MATRIX_HEIGHT
        )
        return lines_cleared
```

In `Matris.lock_tetromino`, replace the inline score:

```python
            self.score += score_for_lines(lines_cleared, self.combo)
```

and the inline level check:

```python
        if should_level_up(self.lines, self.level):
            self.levelup_sound.play()
            self.level += 1
```

Do not change any other rendering, sound, or event behavior.

- [ ] **Step 4: Run the Matris tests**

Run:

```bash
uv run pytest tests/test_matris.py -q
```

Expected: all Matris tests pass.

---

## Task 5: Documentation and Final Verification

**Files:**
- Modify: `README.md`
- Create: `CONTEXT.md`

- [ ] **Step 1: Add the CI badge and high score documentation**

Add after the title:

```markdown
[![CI](https://github.com/Onehand-Coding/Tetris/actions/workflows/ci.yml/badge.svg)](https://github.com/Onehand-Coding/Tetris/actions/workflows/ci.yml)
```

Add a section after the sound system:

```markdown
## High Scores and Data

High scores are stored outside the package:

- Default: `~/.local/share/tetris/highscores.txt`
- Override: `TETRIS_DATA_DIR=/path/to/data`

The directory is created on the first score write. No score file is written
inside the installed package.
```

Replace the development section with:

```markdown
## Development

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Tests use the dummy SDL driver, so no window is required. CI runs the same
commands plus a wheel build and a resource check.
```

Keep the existing installation, controls, menu, and troubleshooting content.
Update the install command to `uv sync --extra dev` when developing.

- [ ] **Step 2: Create `CONTEXT.md`**

```markdown
# Project Context

## Purpose

A local pygame Tetris game with menus, sound, high scores, and a Pygame-based
board.

## Architecture

- `tetris/__main__.py` owns the pygame loop, menu integration, rendering, input,
  and the `Matris` board/controller.
- `tetris/game.py` owns pure line clearing, scoring, and level checks.
- `tetris/tetrominoes.py` owns the seven shapes and rotation.
- `tetris/scores.py` owns high score storage under a user data directory.
- `kezmenu` is the vendored menu library.

## Game Rules

- A full row is cleared and rows above it shift down.
- Line score is `100 * lines_cleared**2 * combo`.
- A level up occurs when total lines reach `current_level * 10`.
- Hard drops award ten points per cell.

## Data

High scores default to `~/.local/share/tetris/highscores.txt`.
`TETRIS_DATA_DIR` overrides the directory.

## Commands

```bash
uv sync --extra dev
uv run tetris
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

## Decisions

- Extract only the pure rules; keep the pygame view and menu intact.
- Keep score formulas identical to the pre-refactor behavior.
- Use a user data directory instead of the package directory.
- Use dummy SDL drivers in tests and CI.
- Keep the vendored kezmenu library.

## Gotchas

- `Matris` expects pygame surfaces for block sprites; tests use `Matris.__new__`
  with dummy objects.
- Pygame needs `SDL_VIDEODRIVER=dummy` in headless tests.
- `remove_full_lines` mutates the matrix and returns it with the line count.
- The score file is append-only; invalid lines are ignored on read.
- Do not create `.highscores` in `src`.

## Known Limitations

- Tests cover rules and board operations, not the menu or rendering loop.
- Sound playback is mocked or absent in headless tests.
- Existing package-local high scores are not migrated.
```

- [ ] **Step 3: Run the full verification**

Run:

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run pytest -q -W error
rm -rf dist build
uv build
python3 -m zipfile -l dist/*.whl | grep tetris/resources/sounds/background.wav
test ! -e src/tetris/.highscores && echo "no package score file"
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run python -c "import tetris.__main__; print('import ok')"
```

Expected:

- Ruff and format checks pass.
- All tests pass, including with warnings as errors.
- The wheel contains the background sound resource.
- No `.highscores` file exists in the package.
- The module imports cleanly with dummy SDL.

- [ ] **Step 4: Report status**

Summarize files changed, test and lint results, and any unverified item with the
exact command needed to verify it.

Do not commit or push unless the user explicitly asks.

---

## Implementation Notes

Deviations made during execution:

- Ruff format and `ruff check --fix` were applied to the whole repository,
  including the vendored `kezmenu` package. This is a mechanical formatting diff;
  game behavior is unchanged.
- Bare `except:` blocks were replaced with `except Exception:`.
- The tetromino `rotate` call uses an explicit `zip(..., strict=...)` argument.
- The vendored menu package declares `__all__` to satisfy the unused-import
  check.
- The collision check stays in `Matris.blend`; `fits_in_matrix` only checks
  bounds, so the misleading collision test was removed.
- A stale package-local `src/tetris/.highscores` file was deleted.
- The unused Hatch lint environment (Black and mypy) was removed; CI uses Ruff
  and pytest.
- The suite has 24 tests.

