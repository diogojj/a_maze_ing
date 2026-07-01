from .mazegen import MazeGenerator
from .config_parser import ConfigError, MazeConfig, parse_config
from .output_writer import write_maze

__name__ = "mazegen"
__version__ = "1.0.0"

__author__ = "dide-jes", "mgracio-"

__all__ = [
    "MazeGenerator",
    "ConfigError",
    "MazeConfig",
    "parse_config",
    "write_maze"
]
