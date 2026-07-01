"""mazegen - a small, reusable maze generator.

This module provides a single class, :class:`MazeGenerator`, that builds
a rectangular maze with a depth-first search (the "recursive
backtracker") and solves it with a breadth-first search.

Wall encoding
-------------
Each cell is an integer bitmask. A *set* bit means the wall on that side
is **closed**:

=========  ===  =====
Direction  Bit  Value
=========  ===  =====
North      0    1
East       1    2
South      2    4
West       3    8
=========  ===  =====

So a cell equal to ``15`` (``0b1111``) is fully closed, and ``0`` is
fully open. This is the same scheme used by the project's output file,
so the shell can write a cell with ``format(cell, "x")``.

Basic usage
-----------
>>> from mazegen import MazeGenerator
>>> gen = MazeGenerator(width=20, height=15, entry=(0, 0),
...                     exit=(19, 14), perfect=True, seed=42)
>>> gen.generate()
>>> grid = gen.grid      # grid[y][x] -> bitmask of closed walls
>>> path = gen.solve()   # e.g. "ESSEEN..."

Custom parameters
-----------------
* ``width`` / ``height``: maze size in cells.
* ``entry`` / ``exit``: ``(x, y)`` coordinates; must differ and be in
  bounds.
* ``perfect``: ``True`` for a perfect maze — exactly one path between
  entry and exit. ``False`` guarantees at least one extra route reaches
  the exit (and may add further loops elsewhere).
* ``seed``: an integer for a reproducible maze, or ``None`` to let the
  generator pick a random one. The seed actually used is always readable
  afterwards via :attr:`seed`, so a "random" maze can still be replayed.

Accessing the result
---------------------
* :attr:`grid` - the 2D list of cell bitmasks.
* :attr:`entry` / :attr:`exit` - the coordinates given back.
* :attr:`seed` - the integer seed that produced this maze.
* :meth:`solve` - shortest path from entry to exit as a string made of
  the letters ``N``, ``E``, ``S`` and ``W``.
"""

import random
from collections import deque
from typing import Optional

# Wall bits. A set bit means the wall is closed.
N, E, S, W = 1, 2, 4, 8

# One tuple per direction: (letter, dx, dy, wall_bit, opposite_bit).
# Moving in a direction clears `wall_bit` on this cell and
# `opposite_bit` on the neighbour, so the two sides always agree.
_MOVES = (
    ("N", 0, -1, N, S),
    ("E", 1, 0, E, W),
    ("S", 0, 1, S, N),
    ("W", -1, 0, W, E),
)

Coord = tuple[int, int]

# 3x6 shape templates for the "42" pattern, read only at import time to
# decide WHICH cells belong to it: "#" = a pattern cell, "." = not.
# These characters are internal only -- they never appear in the grid,
# the output file, or any display. A pattern cell simply becomes an
# isolated cell (value 15, all walls closed); how that cell is *drawn*
# is entirely the display's choice. Every stroke is one cell thick.
_DIGIT_4 = (
    "#.#",
    "#.#",
    "###",
    "..#",
    "..#",
    "..#",
)
_DIGIT_2 = (
    "###",
    "..#",
    "###",
    "#..",
    "#..",
    "###",
)
_DIGIT_W = 3                              # width of each digit
_DIGIT_H = 6                              # height of each digit
_PATTERN_GAP = 1                            # empty columns between digits
_PATTERN_W = _DIGIT_W + _PATTERN_GAP + _DIGIT_W   # total pattern width  (7)
_PATTERN_H = _DIGIT_H                            # total pattern height (6)


class MazeGenerator:
    """Generate and solve a rectangular maze.

    Args:
        width: Maze width in cells (number of columns).
        height: Maze height in cells (number of rows).
        entry: ``(x, y)`` entry coordinates.
        exit: ``(x, y)`` exit coordinates.
        perfect: ``True`` for exactly one entry-exit path; ``False`` for
            more than one path reaching the exit.
        seed: Integer seed for a reproducible maze, or ``None`` to
            generate a random one (readable afterwards via :attr:`seed`).

    Raises:
        ValueError: If the size is not positive, a coordinate is out of
            bounds, or entry and exit are equal.
    """

    def __init__(
        self,
        width: int,
        height: int,
        entry: Coord,
        exit: Coord,
        perfect: bool = True,
        seed: Optional[int] = None,
    ) -> None:
        if width < 1 or height < 1:
            raise ValueError("width and height must be positive")
        for name, point in (("entry", entry), ("exit", exit)):
            x, y = point
            if not (0 <= x < width and 0 <= y < height):
                raise ValueError(f"{name} {point} is out of bounds")
        if entry == exit:
            raise ValueError("entry and exit must be different")

        self.width = width
        self.height = height
        self.perfect = perfect
        self._entry = entry
        self._exit = exit
        # If no seed is given, pick a concrete random one and keep it,
        # so even a "random" maze can be reproduced later via .seed.
        if seed is None:
            seed = random.randrange(100000)
        self._seed = seed
        self._rng = random.Random(seed)
        self._grid: list[list[int]] = self._closed_grid()
        self._pattern: set[Coord] = set()

    @property
    def grid(self) -> list[list[int]]:
        """The maze as a 2D list; ``grid[y][x]`` is a wall bitmask."""
        return self._grid

    @property
    def entry(self) -> Coord:
        """Entry coordinates as ``(x, y)``."""
        return self._entry

    @property
    def exit(self) -> Coord:
        """Exit coordinates as ``(x, y)``."""
        return self._exit

    @property
    def seed(self) -> int:
        """The integer seed actually used.

        If ``None`` was passed to the constructor, this is the random
        seed the generator chose. Save it (or write it to the config)
        to reproduce the exact same maze later.
        """
        return self._seed

    def generate(self) -> None:
        """Build the maze in place.

        Stamps the "42" pattern (when it fits) and carves a spanning tree
        with DFS, giving exactly one path between entry and exit. When
        ``perfect`` is ``False`` it then opens a guaranteed detour around
        the entry-exit path (so more than one path reaches the exit) plus
        a few extra loops elsewhere.
        """
        self._grid = self._closed_grid()
        try:
            self._place_pattern()
        except ValueError as e:
            print(e)
            exit(1)
        self._carve_dfs()
        if not self.perfect:
            self._add_alternative_path()
            self._add_loops()

    def solve(self) -> str:
        """Return the shortest path from entry to exit.

        The path is a string of the letters ``N``, ``E``, ``S`` and
        ``W``. Returns an empty string if no path exists.
        """
        cells = self._shortest_path_cells()
        letters: list[str] = []
        for (ax, ay), (bx, by) in zip(cells, cells[1:]):
            if bx == ax + 1:
                letters.append("E")
            elif bx == ax - 1:
                letters.append("W")
            elif by == ay + 1:
                letters.append("S")
            else:
                letters.append("N")
        return "".join(letters)

    def _shortest_path_cells(self) -> list[Coord]:
        """Shortest entry-to-exit path as a list of cells (BFS).

        Returns ``[entry, ..., exit]`` or ``[]`` if no path exists.
        """
        start, goal = self._entry, self._exit
        came_from: dict[Coord, Optional[Coord]] = {start: None}
        queue: deque[Coord] = deque([start])
        while queue:
            cur = queue.popleft()
            if cur == goal:
                break
            x, y = cur
            for _, dx, dy, bit, _opp in _MOVES:
                if self._grid[y][x] & bit:
                    continue  # the wall on that side is closed
                nb = (x + dx, y + dy)
                if self._is_free(*nb) and nb not in came_from:
                    came_from[nb] = cur
                    queue.append(nb)
        if goal not in came_from:
            return []
        cells: list[Coord] = []
        node: Optional[Coord] = goal
        while node is not None:
            cells.append(node)
            node = came_from[node]
        cells.reverse()
        return cells

    def _closed_grid(self) -> list[list[int]]:
        """Return a fresh grid with every wall of every cell closed."""
        full = N | E | S | W
        return [
            [full for _ in range(self.width)]
            for _ in range(self.height)
        ]

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def _is_free(self, x: int, y: int) -> bool:
        """A cell that may be carved: in bounds and not part of "42"."""
        return self._in_bounds(x, y) and (x, y) not in self._pattern

    def _first_free_cell(self) -> Coord:
        for y in range(self.height):
            for x in range(self.width):
                if self._is_free(x, y):
                    return (x, y)
        raise ValueError("no free cell available")

    def _place_pattern(self) -> None:
        """Mark the cells of a centred "42" as isolated, if it fits.

        The pattern needs a one-cell margin on every side. It is skipped
        (with a printed message) when the maze is too small, when it
        would cover the entry or exit, or when it would split the free
        cells into more than one region. Skipping keeps the maze valid;
        the subject allows omitting the pattern when it cannot be placed.
        """
        self._pattern = set()
        if self.width < _PATTERN_W + 2 or self.height < _PATTERN_H + 2:
            print("maze too small for the '42' pattern; skipping it")
            return
        ox = (self.width - _PATTERN_W) // 2
        oy = (self.height - _PATTERN_H) // 2
        cells = self._digit_cells(_DIGIT_4, ox, oy)
        cells |= self._digit_cells(
            _DIGIT_2, ox + _DIGIT_W + _PATTERN_GAP, oy
        )
        if self._entry in cells or self._exit in cells:
            raise ValueError("Entry and/or Exit cannot be in the 42 pattern")
        if not self._region_connected_without(cells):
            print("'42' pattern would split the maze; skipping it")
            return
        self._pattern = cells
        full = N | E | S | W
        for x, y in cells:
            self._grid[y][x] = full  # isolated: all walls closed

    def _region_connected_without(self, blocked: set[Coord]) -> bool:
        """True if every non-blocked cell forms one connected region.

        Only 4-neighbour adjacency is checked (walls are carved later),
        so a ``True`` result guarantees the DFS can reach every free
        cell around the pattern from any side.
        """
        free: set[Coord] = {
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if (x, y) not in blocked
        }
        if not free:
            return False
        start = next(iter(free))
        seen: set[Coord] = {start}
        stack: list[Coord] = [start]
        while stack:
            x, y = stack.pop()
            for _, dx, dy, _bit, _opp in _MOVES:
                nb = (x + dx, y + dy)
                if nb in free and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        return len(seen) == len(free)

    @staticmethod
    def _digit_cells(
        bitmap: tuple[str, ...], ox: int, oy: int
    ) -> set[Coord]:
        """Return the absolute cells set in ``bitmap`` at (ox, oy)."""
        cells: set[Coord] = set()
        for dy, row in enumerate(bitmap):
            for dx, char in enumerate(row):
                if char == "#":
                    cells.add((ox + dx, oy + dy))
        return cells

    def _carve_dfs(self) -> None:
        """Carve a spanning tree over all free cells (iterative DFS).

        An explicit stack is used instead of recursion so that large
        mazes never hit Python's recursion limit.
        """
        start = self._entry
        if not self._is_free(*start):
            start = self._first_free_cell()
        stack: list[Coord] = [start]
        visited: set[Coord] = {start}
        while stack:
            x, y = stack[-1]
            choices: list[tuple[int, int, int, int]] = []
            for _, dx, dy, bit, opp in _MOVES:
                nx, ny = x + dx, y + dy
                if self._is_free(nx, ny) and (nx, ny) not in visited:
                    choices.append((nx, ny, bit, opp))
            if not choices:
                stack.pop()
                continue
            nx, ny, bit, opp = self._rng.choice(choices)
            self._grid[y][x] &= ~bit       # open this side ...
            self._grid[ny][nx] &= ~opp     # ... and the neighbour's
            visited.add((nx, ny))
            stack.append((nx, ny))

    def _add_alternative_path(self) -> bool:
        """Force a second route to the exit.

        Builds a small parallel detour beside one edge of the unique
        entry-exit path. That edge then lies on a loop, so at least two
        distinct paths reach the exit. Returns ``True`` if a detour was
        added (it can only fail on a maze too cramped to fit one).
        """
        path = self._shortest_path_cells()
        edges = list(zip(path, path[1:]))
        self._rng.shuffle(edges)
        for a, b in edges:
            if self._try_bypass(a, b):
                return True
        return False

    def _try_bypass(self, a: Coord, b: Coord) -> bool:
        """Open a 2x2 detour beside the open edge ``a``-``b``.

        Cells ``a`` and ``b`` are adjacent and already connected. We add
        the two cells alongside them and open the three walls that form
        the parallel route ``a -> c -> d -> b``, unless that would create
        a forbidden fully open 3x3 area.
        """
        ax, ay = a
        bx, by = b
        if ay == by:                       # a-b is horizontal
            offsets = ((0, -1), (0, 1))    # the cells above / below
        else:                              # a-b is vertical
            offsets = ((-1, 0), (1, 0))    # the cells left / right
        for ox, oy in offsets:
            c = (ax + ox, ay + oy)
            d = (bx + ox, by + oy)
            if not (self._is_free(*c) and self._is_free(*d)):
                continue
            snapshot = {p: self._grid[p[1]][p[0]] for p in (a, b, c, d)}
            self._open_between(a, c)
            self._open_between(c, d)
            self._open_between(d, b)
            if self._any_open_3x3((a, b, c, d)):
                for p, value in snapshot.items():
                    self._grid[p[1]][p[0]] = value   # revert
                continue
            return True
        return False

    def _add_loops(self) -> None:
        """Open extra interior walls to create more loops.

        A wall is only opened when it does not create a fully open 3x3
        block, i.e. it never makes a corridor wider than two cells.
        """
        walls: list[tuple[int, int, int, int, int, int]] = []
        for y in range(self.height):
            for x in range(self.width):
                if not self._is_free(x, y):
                    continue
                if self._is_free(x + 1, y):
                    walls.append((x, y, x + 1, y, E, W))
                if self._is_free(x, y + 1):
                    walls.append((x, y, x, y + 1, S, N))
        self._rng.shuffle(walls)
        target = max(1, len(walls) // 10)  # open about 10% of the walls
        opened = 0
        for ax, ay, bx, by, bit, opp in walls:
            if opened >= target:
                break
            if not self._grid[ay][ax] & bit:
                continue  # already open
            self._grid[ay][ax] &= ~bit
            self._grid[by][bx] &= ~opp
            if self._any_open_3x3(((ax, ay), (bx, by))):
                self._grid[ay][ax] |= bit   # revert: keep it narrow
                self._grid[by][bx] |= opp
            else:
                opened += 1

    def _dir_bits(self, a: Coord, b: Coord) -> tuple[int, int]:
        """Wall bit on ``a`` facing ``b`` and the matching bit on ``b``."""
        ax, ay = a
        bx, by = b
        if bx == ax + 1:
            return E, W
        if bx == ax - 1:
            return W, E
        if by == ay + 1:
            return S, N
        return N, S                         # b is north of a

    def _open_between(self, a: Coord, b: Coord) -> None:
        """Open the shared wall between adjacent cells ``a`` and ``b``."""
        bit_a, bit_b = self._dir_bits(a, b)
        self._grid[a[1]][a[0]] &= ~bit_a
        self._grid[b[1]][b[0]] &= ~bit_b

    def _any_open_3x3(self, cells: tuple[Coord, ...]) -> bool:
        """True if any 3x3 block touching ``cells`` is fully open."""
        xs = [x for x, _ in cells]
        ys = [y for _, y in cells]
        for cy in range(min(ys) - 2, max(ys) + 1):
            for cx in range(min(xs) - 2, max(xs) + 1):
                if self._is_open_block(cx, cy):
                    return True
        return False

    def _is_open_block(self, cx: int, cy: int) -> bool:
        """True if the 3x3 block at top-left (cx, cy) is fully open."""
        for y in range(cy, cy + 3):
            for x in range(cx, cx + 3):
                if not self._is_free(x, y):
                    return False
                cell = self._grid[y][x]
                if x < cx + 2 and cell & E:
                    return False
                if y < cy + 2 and cell & S:
                    return False
        return True
