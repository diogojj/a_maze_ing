"""Parse and validate the maze configuration file.

The file holds one ``KEY=VALUE`` pair per line; blank lines and lines
starting with ``#`` are ignored. Keys are matched case-insensitively.

Mandatory keys: WIDTH, HEIGHT, ENTRY, EXIT, OUTPUT_FILE, PERFECT.
Optional key:   SEED (integer) for a reproducible maze.

This module validates *syntax* only -- that values have the right shape
and type, and that every mandatory key is present. It deliberately does
NOT check whether the coordinates are in bounds or whether entry differs
from exit: the generator owns those semantic rules and raises ValueError
for them, so they live in exactly one place.
"""
from __future__ import annotations

from dataclasses import dataclass

_MANDATORY = ("WIDTH", "HEIGHT", "ENTRY", "EXIT", "OUTPUT_FILE", "PERFECT")
_BOOL_TRUE = {"true", "1", "yes", "on"}
_BOOL_FALSE = {"false", "0", "no", "off"}


class ConfigError(Exception):
    """Raised when the configuration file is missing or malformed."""


@dataclass(frozen=True)
class MazeConfig:
    """Validated configuration ready to hand to the generator."""

    width: int
    height: int
    entry: tuple[int, int]
    exit: tuple[int, int]
    output_file: str
    perfect: bool
    seed: int | None = None


def _read_pairs(path: str) -> dict[str, str]:
    """Read the file into a {KEY: value} dict, validating line syntax.

    Raises:
        ConfigError: If the file cannot be read, a line lacks ``=``, a
            key is empty, or a key appears twice.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError as exc:
        raise ConfigError(f"cannot read config file: {exc}") from exc

    pairs: dict[str, str] = {}
    for number, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ConfigError(
                f"line {number}: expected KEY=VALUE, got {line!r}"
            )
        key, _, value = line.partition("=")
        key = key.strip().upper()
        value = value.strip()
        if not key:
            raise ConfigError(f"line {number}: empty key")
        if key in pairs:
            raise ConfigError(f"line {number}: duplicate key {key!r}")
        pairs[key] = value
    return pairs


def _to_int(key: str, value: str) -> int:
    """Convert a value to int or raise a clear ConfigError."""
    try:
        return int(value)
    except ValueError:
        raise ConfigError(
            f"{key} must be an integer, got {value!r}"
        ) from None


def _to_coord(key: str, value: str) -> tuple[int, int]:
    """Convert an ``x,y`` value to a coordinate tuple."""
    parts = value.split(",")
    if len(parts) != 2:
        raise ConfigError(f"{key} must be 'x,y', got {value!r}")
    try:
        return (int(parts[0]), int(parts[1]))
    except ValueError:
        raise ConfigError(
            f"{key} must be integer coordinates 'x,y', got {value!r}"
        ) from None


def _to_bool(key: str, value: str) -> bool:
    """Convert a truthy/falsy word to bool."""
    low = value.lower()
    if low in _BOOL_TRUE:
        return True
    if low in _BOOL_FALSE:
        return False
    raise ConfigError(f"{key} must be true or false, got {value!r}")


def parse_config(path: str) -> MazeConfig:
    """Parse ``path`` into a validated :class:`MazeConfig`.

    Args:
        path: Path to the configuration file.

    Returns:
        A fully typed configuration object.

    Raises:
        ConfigError: For any missing key or malformed value. The message
            is safe to show the user as-is.
    """
    pairs = _read_pairs(path)

    missing = [key for key in _MANDATORY if key not in pairs]
    if missing:
        raise ConfigError(
            f"missing mandatory key(s): {', '.join(missing)}"
        )

    output_file = pairs["OUTPUT_FILE"]
    if not output_file:
        raise ConfigError("OUTPUT_FILE must not be empty")

    seed_raw = pairs.get("SEED")
    if seed_raw:
        seed = _to_int("SEED", seed_raw)

        if seed < 0 or seed > 100000:
            raise ConfigError(
                "SEED must be a positive integer below or equal to 100000"
                " including 0"
            )
    else:
        seed = None

    return MazeConfig(
        width=_to_int("WIDTH", pairs["WIDTH"]),
        height=_to_int("HEIGHT", pairs["HEIGHT"]),
        entry=_to_coord("ENTRY", pairs["ENTRY"]),
        exit=_to_coord("EXIT", pairs["EXIT"]),
        output_file=output_file,
        perfect=_to_bool("PERFECT", pairs["PERFECT"]),
        seed=seed,
    )
