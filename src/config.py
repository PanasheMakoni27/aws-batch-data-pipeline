"""Load the table config and return the active tables."""
from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "tables.yaml"


def load_tables(path=CONFIG_PATH):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)["tables"]


def active_tables(tables):
    return [t for t in tables if t["active"]]


if __name__ == "__main__":
    for t in active_tables(load_tables()):
        print(f'{t["name"]:20} {t["source_schema"]}.{t["source_table"]:18} {t["load_type"]}')