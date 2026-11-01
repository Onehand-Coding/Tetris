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
