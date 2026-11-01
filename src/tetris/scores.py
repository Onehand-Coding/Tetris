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
