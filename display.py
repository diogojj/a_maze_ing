"""Terminal ASCII rendering of a maze, with an interactive loop.

Two layers, deliberately separate:

* ``render()`` is a pure function: maze data in, a string out. No I/O,
  no global state, so it is trivial to eyeball and unit-test.
* ``MazeDisplay`` wraps a generator and adds the interactive menu the
  subject requires (regenerate / show-hide path / change colours / quit).

The renderer depends only on a small read-only slice of the generator
contract, captured by the ``MazeLike`` Protocol below. Anything that
exposes ``grid``/``entry``/``exit``/``solve()`` works -- the mock today,
the real engine tomorrow.
"""
from __future__ import annotations

from typing import Callable, Protocol

# Wall bit masks: N=bit0, E=bit1, S=bit2, W=bit3.
_N, _E, _S, _W = 1, 2, 4, 8
_CLOSED = 0xF  # a fully-walled (isolated) cell -- e.g. the "42" pattern.

# ANSI colours. Walls cycle through this palette; markers are fixed.
_RESET = "\033[0m"
_WALL_PALETTE = ["37", "36", "33", "32", "35"]  # white cyan yellow grn mag
_ENTRY_COLOR = "32"   # green
_EXIT_COLOR = "31"    # red
_PATH_COLOR = "36"    # cyan
_PATTERN_COLOR = "35"  # magenta

_MENU = (
    "=== A-Maze-ing ===\n"
    "1. Re-generate a new maze\n"
    "2. Show/hide path from entry to exit\n"
    "3. Rotate maze colours\n"
    "4. Quit"
)

_MOVES = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}


class MazeLike(Protocol):
    """The read-only slice of the generator contract the display needs."""

    @property
    def grid(self) -> list[list[int]]: ...
    @property
    def entry(self) -> tuple[int, int]: ...
    @property
    def exit(self) -> tuple[int, int]: ...
    def solve(self) -> str: ...


def path_cells(
    entry: tuple[int, int], solution: str
) -> list[tuple[int, int]]:
    """Walk the N/E/S/W solution string into a list of (x, y) cells.

    Args:
        entry: Starting cell as (x, y).
        solution: Path letters, e.g. "EEESWWW".

    Returns:
        Every cell on the path, including entry and exit.

    Raises:
        ValueError: If the string contains a letter other than N/E/S/W.
    """
    x, y = entry
    cells = [(x, y)]
    for ch in solution:
        if ch not in _MOVES:
            raise ValueError(f"bad move {ch!r} in solution path")
        dx, dy = _MOVES[ch]
        x, y = x + dx, y + dy
        cells.append((x, y))
    return cells


def _wrap(text: str, code: str, use_color: bool) -> str:
    """Wrap text in an ANSI colour code, or return it plain."""
    if not use_color:
        return text
    return f"\033[{code}m{text}{_RESET}"


def _interior(
    x: int,
    y: int,
    grid: list[list[int]],
    entry: tuple[int, int],
    exit: tuple[int, int],
    path: set[tuple[int, int]],
    use_color: bool,
) -> str:
    """Return the 3-character interior of one cell, with its marker."""
    if (x, y) == entry:
        return _wrap(" E ", _ENTRY_COLOR, use_color)
    if (x, y) == exit:
        return _wrap(" X ", _EXIT_COLOR, use_color)
    if grid[y][x] == _CLOSED:
        return _wrap("\u2588\u2588\u2588", _PATTERN_COLOR, use_color)
    if (x, y) in path:
        return _wrap(" * ", _PATH_COLOR, use_color)
    return "   "


def render(
    grid: list[list[int]],
    entry: tuple[int, int],
    exit: tuple[int, int],
    *,
    show_path: bool = True,
    solution: str = "",
    wall_color_idx: int = 0,
    use_color: bool = True,
) -> str:
    """Render a maze to a multi-line ASCII string.

    A wall is drawn whenever *either* of the two cells sharing it claims
    it, so the picture is correct even if the generator's coherence is
    slightly off. Border handling falls out of the same rule.

    Args:
        grid: grid[y][x] = bitmask of closed walls.
        entry: Entry cell (x, y).
        exit: Exit cell (x, y).
        show_path: Whether to overlay the solution path.
        solution: N/E/S/W path string (used only if show_path).
        wall_color_idx: Index into the wall colour palette.
        use_color: Emit ANSI colour codes when True.

    Returns:
        The maze as a string with no trailing newline.
    """
    if not grid or not grid[0]:
        return ""
    height, width = len(grid), len(grid[0])
    path = set(path_cells(entry, solution)) if show_path else set()
    code = _WALL_PALETTE[wall_color_idx % len(_WALL_PALETTE)]
    corner = _wrap("+", code, use_color)
    lines: list[str] = []

    for y in range(height + 1):
        # Horizontal wall line: boundary above row y (y == height = floor).
        cells = [corner]
        for x in range(width):
            above = grid[y - 1][x] & _S if y > 0 else 0
            below = grid[y][x] & _N if y < height else 0
            wall = above or below
            cells.append(_wrap("---", code, use_color) if wall else "   ")
            cells.append(corner)
        lines.append("".join(cells))
        if y == height:
            break
        # Content line: vertical walls + cell interiors for row y.
        row: list[str] = []
        for x in range(width + 1):
            left = grid[y][x - 1] & _E if x > 0 else 0
            right = grid[y][x] & _W if x < width else 0
            wall = left or right
            row.append(_wrap("|", code, use_color) if wall else " ")
            if x < width:
                row.append(
                    _interior(x, y, grid, entry, exit, path, use_color)
                )
        lines.append("".join(row))

    return "\n".join(lines)


class MazeDisplay:
    """Interactive terminal display driven by a generator factory."""

    def __init__(
        self,
        make_maze: Callable[[], MazeLike],
        initial: MazeLike | None = None
    ) -> None:
        """Store a factory that returns a freshly *generated* maze.

        Args:
            make_maze: Callable producing a ready-to-read MazeLike, used
                each time the user regenerates. For the real engine this
                builds a new random maze; for the mock it returns the
                same fixed maze.
            initial: Maze to show first. When given (e.g. the maze the
                shell already wrote to the output file) it is displayed
                before any regeneration; otherwise ``make_maze`` is
                called once to produce the opening frame.
        """
        self._make_maze = make_maze
        self._maze: MazeLike = initial if initial is not None else make_maze()
        self._show_path = True
        self._color_idx = 0

    def _frame(self) -> str:
        """Render the current maze with the current view settings."""
        m = self._maze
        return render(
            m.grid,
            m.entry,
            m.exit,
            show_path=self._show_path,
            solution=m.solve(),
            wall_color_idx=self._color_idx,
            use_color=True,
        )

    def run(self) -> None:
        """Run the menu loop until the user quits or input closes."""
        while True:
            print("\033[2J\033[H", end="")  # clear screen, cursor home
            print(self._frame())
            print(_MENU)
            try:
                choice = input("Choice? (1-4): ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if choice == "1":
                self._maze = self._make_maze()
            elif choice == "2":
                self._show_path = not self._show_path
            elif choice == "3":
                self._color_idx += 1
            elif choice == "4":
                return
            else:
                print("Please choose a number from 1 to 4.")


if __name__ == "__main__":
    sample = [
        [0xD, 0x5, 0x5, 0x3],
        [0x9, 0x5, 0x5, 0x6],
        [0xC, 0x5, 0x5, 0x3],
        [0xD, 0x5, 0x5, 0x6],
    ]
    print(render(sample, (0, 0), (3, 3), solution="EEESWWWSEEES",
                 use_color=False))
