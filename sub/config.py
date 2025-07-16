# config.py
import yaml
from pathlib import Path

DEFAULT_CONFIG_PATH = Path("config.yaml")

def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    return config

