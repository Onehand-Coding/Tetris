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
