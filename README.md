*This project has been created as part of the 42 curriculum by dide-jes, mgracio-.*
 
# A-Maze-ing
 
## Description
 
A-Maze-ing is a maze generator and interactive terminal visualiser written
in Python 3.10+. It reads a plain-text configuration file, generates a
rectangular maze (optionally *perfect* — exactly one path between entry and
exit), writes the maze to an output file using a hexadecimal wall encoding,
and opens an interactive ASCII display in the terminal.
 
Every maze contains a "42" drawn with fully closed cells, has solid outer
walls, no fully open 3×3 area (corridors are never wider than two cells), and
is reproducible from a seed. The maze-generation logic lives in its own
standalone, pip-installable module (`mazegen`) so it can be reused in a future
project without any of this program's shell code.
 
## Instructions
 
The project ships a `Makefile` that drives a local virtual environment. From
the repository root:
 
```bash
make install      # create .venv and install dev tools (flake8, mypy, build)
make run          # run the program on config.txt
make debug        # run under pdb
make lint         # flake8 + mypy with the project flags
make lint-strict  # flake8 + mypy --strict
make build        # build the mazegen package (sdist + wheel)
make clean        # remove caches and build artifacts
```
 
To run it directly, without the Makefile:
 
```bash
python3 a_maze_ing.py config.txt
```
 
`a_maze_ing.py` is the entry point and `config.txt` is the only argument (you
may use a different filename). On start-up the program writes the maze to the
file named by `OUTPUT_FILE`, prints a one-line confirmation, then opens the
display.
 
### Interactive controls
 
When the display is open:
 
| Key | Action |
|-----|--------|
| `1` | Re-generate a new maze (fresh random seed) and redraw |
| `2` | Show / hide the shortest path from entry to exit |
| `3` | Rotate the wall colours |
| `4` | Quit |
 
Entry is shown as `E`, exit as `X`, the "42" cells as filled blocks, and the
solution path (when shown) as `*`.
 
## Configuration file format
 
One `KEY=VALUE` pair per line. Blank lines and lines starting with `#` are
ignored. Keys are matched case-insensitively. Values may contain `=` (only the
first `=` separates key from value).
 
**Mandatory keys**
 
| Key           | Meaning                          | Example               |
|---------------|----------------------------------|-----------------------|
| `WIDTH`       | Maze width in cells (integer)    | `WIDTH=20`            |
| `HEIGHT`      | Maze height in cells (integer)   | `HEIGHT=15`           |
| `ENTRY`       | Entry as `x,y` (0-indexed)       | `ENTRY=0,0`           |
| `EXIT`        | Exit as `x,y` (0-indexed)        | `EXIT=19,14`          |
| `OUTPUT_FILE` | Output filename (non-empty)      | `OUTPUT_FILE=maze.txt`|
| `PERFECT`     | One path entry↔exit? (boolean)   | `PERFECT=True`        |
 
**Optional key**
 
| Key    | Meaning                                              | Example     |
|--------|-----------------------------------------------------|-------------|
| `SEED` | Integer seed for a reproducible maze. **Omit** the line for a random maze (the seed actually used is still recoverable via the generator). | `SEED=999` |
 
`PERFECT` accepts `true/1/yes/on` and `false/0/no/off` (case-insensitive).
`ENTRY` and `EXIT` must be two integers separated by a comma.
 
A working default `config.txt` is included at the repository root.
 
### Validation boundary
 
The parser checks **syntax only**: that every mandatory key is present and that
each value has the right shape and type. It raises `ConfigError` (reported to
the user as `Configuration error: ...`) for a missing key, a line without `=`,
an empty or duplicate key, a non-integer number, a malformed coordinate, or an
invalid boolean.
 
It deliberately does **not** check whether coordinates are inside the maze or
whether entry differs from exit — those *semantic* rules belong to the
generator, which raises `ValueError` (reported as `Invalid maze parameters:
...`). Keeping each rule in exactly one place avoids duplicated, drifting
validation.
 
## Output file format
 
The maze is written to `OUTPUT_FILE` as follows (subject §IV.5):
 
- `HEIGHT` lines of `WIDTH` characters; one uppercase hexadecimal digit per
  cell, rows top to bottom.
- a blank line.
- the entry coordinates as `x,y`.
- the exit coordinates as `x,y`.
- the shortest entry→exit path as the letters `N`, `E`, `S`, `W`.
Every line, including the blank separator, ends with `\n`.
 
Each hex digit is a bitmask where a **set bit means the wall is closed**:
 
| Direction | Bit | Value |
|-----------|-----|-------|
| North     | 0   | 1     |
| East      | 1   | 2     |
| South     | 2   | 4     |
| West      | 3   | 8     |
 
So `F` (`0b1111`) is a fully closed cell and `0` is fully open. Because the
generator already stores cells in this exact scheme, the writer is just
`format(cell, "X")` per cell — no translation layer. The provided
`output_validator.py` can be used to check wall coherence of a generated file.
 
## Maze generation algorithm
 
- **Generation — depth-first search (recursive backtracker).** From a starting
  cell, the algorithm repeatedly carves into a random unvisited neighbour,
  backtracking when it hits a dead end, until every reachable cell is visited.
  This produces a spanning tree, i.e. a *perfect* maze with exactly one path
  between any two cells. An explicit stack is used instead of recursion so
  large mazes never hit Python's recursion limit.
- **Solving — breadth-first search.** BFS over the carved graph returns a
  *shortest* entry→exit path, which the subject requires, expressed as
  `N`/`E`/`S`/`W` letters.
**Why these algorithms.** The recursive backtracker is simple, well
documented, and *naturally* yields a perfect maze — the spanning-tree property
the subject asks for comes for free, with no post-processing needed when
`PERFECT=True`. BFS is the standard, correct way to get a guaranteed shortest
path on an unweighted grid graph, so the solver matches the output-format
requirement exactly.
 
**The "42" pattern.** Before carving, the two digits are stamped as fully
closed (isolated) cells and excluded from the carve. The DFS then connects
every remaining cell around them. Each digit is 3×6 with one-cell-thick
strokes and a one-cell gap, centred, needing a one-cell margin on every side
(so a maze smaller than 9×8 cannot fit it). Before stamping, the generator
checks that removing those cells keeps the rest of the grid connected; if it
would split the maze, cover the entry/exit, or not fit, the glyph is skipped
with a printed message — which the subject explicitly allows.
 
**Imperfect mazes (`PERFECT=False`).** The generator first opens a small
parallel detour beside one edge of the entry→exit path, guaranteeing a second
route reaches the exit, then opens a few more interior walls to add loops.
Every candidate opening is rejected if it would create a fully open 3×3 block,
so corridors stay at most two cells wide.
 
## Reusable module (`mazegen`)
 
The maze generation is a single class, `MazeGenerator`, in a single file,
`mazegen.py`, packaged as `mazegen-1.0.0-py3-none-any.whl`. It depends only on
the Python standard library and knows nothing about this project's config
format, output file, or display — so it can be dropped into any future project.
 
### Basic usage
 
```python
from mazegen import MazeGenerator
 
gen = MazeGenerator(width=20, height=15, entry=(0, 0),
                    exit=(19, 14), perfect=True, seed=42)
gen.generate()
 
grid = gen.grid     # grid[y][x] -> bitmask of closed walls (N=1 E=2 S=4 W=8)
start = gen.entry   # (x, y)
goal = gen.exit     # (x, y)
path = gen.solve()  # shortest path, e.g. "EESENEE..."
```
 
### Custom parameters
 
- `width` / `height`: maze size in cells.
- `entry` / `exit`: `(x, y)` coordinates; must differ and be in bounds.
- `perfect`: `True` for exactly one path between entry and exit; `False` for at
  least one extra route to the exit, plus a few loops.
- `seed`: an integer for a reproducible maze, or `None` to let the generator
  choose one. **The same seed always produces the same maze.** When `None` is
  passed, the chosen seed is still readable afterwards via `gen.seed`, so a
  "random" maze can be replayed.
### Accessing the result
 
- `gen.grid` — the 2D list of cell bitmasks (`grid[y][x]`).
- `gen.entry` / `gen.exit` — the coordinates back.
- `gen.seed` — the integer seed that produced this maze.
- `gen.solve()` — the shortest path as a string of `N`, `E`, `S`, `W`.
### Building and installing the package
 
```bash
python3 -m build            # produces dist/mazegen-1.0.0-py3-none-any.whl (+ sdist)
pip install dist/mazegen-1.0.0-py3-none-any.whl
```
 
`make build` does the same and moves the wheel to the repository root.
 
## What is reusable, and how
 
`mazegen.py` is the reusable unit. It is the only file in the wheel, contains
the single `MazeGenerator` class, and has zero project-specific dependencies.
A future project reuses it by installing the wheel and importing the class —
the five members above (`__init__`, `generate`, `grid`, `entry`/`exit`,
`solve`) are the whole contract. The shell of *this* project
(`config_parser.py`, `output_writer.py`, `display.py`, `a_maze_ing.py`) treats
the generator as a black box and is **not** part of the reusable package.
 
## Team and project management
 
### Roles
 
- **mgracio- :** Configuration parser, output writer,
  ASCII terminal display, main entry point (`a_maze_ing.py`), `Makefile`.
- **dide-jes :** The `mazegen` module: DFS carve,
  BFS solver, "42" pattern placement, imperfect-maze loops, and packaging.
### Planning and how it evolved
 
On day one we agreed a small **data-structure contract** — the cell bitmask
scheme (`N=1 E=2 S=4 W=8`, set bit = closed wall), the `grid[y][x]` layout, and
the `generate()` / `grid` / `entry` / `exit` / `solve()` interface — so both
halves could be built in parallel. To work before the engine existed, the shell
was developed against a hard-coded mock generator that satisfied the same
contract. When the real `mazegen` arrived, integration required **no changes**
to the shell code; the only issue was a stale local display file missing a
parameter, fixed by replacing it. Late effort went into packaging (a clean
single-file wheel) and the defence-ready documentation.
 
### What worked well / what could be improved
 
- **Worked well:** the contract-first agreement and the mock generator made the
  two workstreams genuinely independent, so integration was near-instant.
  Running `flake8` and `mypy` (strict flags) after every module kept quality
  high throughout.
- **To improve:** the seed documentation briefly drifted between the engine and
  shell notes before being reconciled; the output write was momentarily
  duplicated during a refactor; and the Git repository should have been set up
  earlier. Tightening the shared docs and adding a tiny integration smoke-test
  to the Makefile would catch these sooner.
### Tools
 
Python 3.10+, `flake8`, `mypy` (with the project flags and `--strict`),
`pytest` for development-only tests, `hatchling` + `build` for packaging,
`make` for task automation, and `venv` for isolation.
 
## Resources
 
- Jamis Buck, *Maze Generation: Recursive Backtracking* — the canonical
  description of the DFS carving algorithm.
- Wikipedia, *Maze generation algorithm* and *Breadth-first search* — overview
  of generation strategies and shortest-path search.
- The relationship between perfect mazes and spanning trees in graph theory.
- Python standard-library docs for `random`, `collections.deque`, and `typing`.
- Python Packaging User Guide and the Hatchling documentation for building the
  pip-installable module.

### Use of AI
 
Structuring README. The algorithm choices, docstrings and the organization of the project structure. 