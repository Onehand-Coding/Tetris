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
