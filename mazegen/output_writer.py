"""Serialize a generated maze to the project's output file format.

File layout (see subject IV.5):
    one uppercase hex digit per cell, rows top-to-bottom, one row per line
    a blank line
    entry coordinates as "x,y"
    exit coordinates as "x,y"
    the shortest entry->exit path as N/E/S/W letters
Every line, including the blank one, is terminated by '\\n'.

This module only serializes whatever the generator hands it. It does
NOT check that the maze is semantically valid (connectivity, the path
actually reaching the exit, etc.) -- that is the generator's job and
the validation script's job. It only guarantees the *format* is correct.
"""
from __future__ import annotations


def _format_grid(grid: list[list[int]]) -> list[str]:
    """Turn grid[y][x] of closed-wall bitmasks into hex-digit row strings.

    Args:
        grid: Rectangular grid; each cell is an int in range 0..15.

    Returns:
        One string per row, each character a single uppercase hex digit.

    Raises:
        ValueError: If the grid is empty, ragged, or holds a value that
            does not fit in a single hex digit.
    """
    if not grid or not grid[0]:
        raise ValueError("grid is empty")
    width = len(grid[0])
    rows: list[str] = []
    for y, row in enumerate(grid):
        if len(row) != width:
            raise ValueError(
                f"row {y} has length {len(row)}, expected {width}"
            )
        for x, cell in enumerate(row):
            if not 0 <= cell <= 15:
                raise ValueError(
                    f"cell ({x},{y}) = {cell} is not a single hex digit"
                )
        rows.append("".join(format(cell, "X") for cell in row))
    return rows


def write_maze(
    filename: str,
    grid: list[list[int]],
    entry: tuple[int, int],
    exit: tuple[int, int],
    solution: str,
) -> None:
    """Write a maze to ``filename`` in the project output format.

    Args:
        filename: Destination path (overwritten if it exists).
        grid: grid[y][x] = bitmask of closed walls (N=1 E=2 S=4 W=8).
        entry: Entry coordinates as (x, y).
        exit: Exit coordinates as (x, y).
        solution: Shortest entry->exit path as N/E/S/W letters.

    Raises:
        ValueError: If the grid data is malformed (see ``_format_grid``).
        OSError: If the file cannot be written; left for the caller to
            report to the user.
    """
    lines = _format_grid(grid)
    lines.append("")  # the mandatory blank separator line
    lines.append(f"{entry[0]},{entry[1]}")
    lines.append(f"{exit[0]},{exit[1]}")
    lines.append(solution)
    content = "\n".join(lines) + "\n"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
