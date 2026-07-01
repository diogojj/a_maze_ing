#!/usr/bin/env python3
"""A-Maze-ing entry point: config -> maze -> output file + display.

Usage:
    python3 a_maze_ing.py config.txt

Reads a configuration file, generates a maze, writes it to the output
file named in the config, then opens an interactive terminal display.
Every foreseeable error (unreadable or invalid config, impossible maze
parameters, unwritable output) is caught and reported as one clear line
with a non-zero exit code; the user never sees a traceback.
"""
from __future__ import annotations

import sys

from display import MazeDisplay
from mazegen import (MazeGenerator, ConfigError, MazeConfig,
                     parse_config, write_maze)


def _build_maze(cfg: MazeConfig, seed: int | None) -> MazeGenerator:
    """Create and generate a maze from ``cfg`` using the given seed."""
    maze = MazeGenerator(
        cfg.width,
        cfg.height,
        cfg.entry,
        cfg.exit,
        perfect=cfg.perfect,
        seed=seed,
    )
    maze.generate()
    write_maze(
            cfg.output_file,
            maze.grid,
            maze.entry,
            maze.exit,
            maze.solve(),
        )
    return maze


def main(argv: list[str]) -> int:
    """Run the program; return a process exit code (0 means success)."""
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <config_file>", file=sys.stderr)
        return 1
    try:
        cfg = parse_config(argv[1])
        # First maze honours the config seed and is the one written out.
        maze = _build_maze(cfg, cfg.seed)
        write_maze(
            cfg.output_file,
            maze.grid,
            maze.entry,
            maze.exit,
            maze.solve(),
        )
        print(f"Maze written to {cfg.output_file} (seed: {maze.seed}).")
        # Regeneration in the display uses a fresh random seed each time.
        display = MazeDisplay(
            lambda: _build_maze(cfg, None),
            initial=maze
        )
        display.run()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Invalid maze parameters: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"File error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
