from pathlib import Path
from math import isfinite
import json


CONFIG_PATH = Path(__file__).resolve().parents[1] / "parameters.json"

def load_config(config_path: Path) -> dict:
    """
    Carrega, valida e retorna os parâmetros experimentais
    definidos no arquivo de configuração.
    """
    with config_path.open("r", encoding="utf-8") as file:
        config: dict = json.load(file)

    validate_config(config)

    return config


def validate_config(config: dict) -> None:
    """
    Verifica a consistência estrutural e matemática dos
    parâmetros experimentais, levantando ValueError quando
    uma das restrições validadas não é atendida.
    """
    thresholds = config["thresholds"]
    simulation = config["simulation"]

    threshold_rules = (
        ("ccd", simulation["ccd_thresholds"], 2),
        ("phenols", thresholds["phenols"], 2),
        ("dpph", thresholds["dpph"], 4),
        ("fps", thresholds["fps"], 4),
        ("uv", thresholds["uv"], 2),
    )

    for name, values, expected_count in threshold_rules:
        if len(values) != expected_count:
            raise ValueError(f"Invalid number of thresholds for {name}")

        if not all(isfinite(value) for value in values):
            raise ValueError(f"Thresholds for {name} must be finite")

        if sorted(set(values)) != values:
            raise ValueError(f"Thresholds for {name} must be sorted and unique")

    categories = config["ccd"]

    if len(categories) != len(simulation["ccd_thresholds"]) + 1:
        raise ValueError("Incompatible CCD categories and thresholds")

    if len(categories) != len(set(categories)):
        raise ValueError("CCD categories must be unique")

    if not 0 <= config["dna_threshold"] <= 1:
        raise ValueError("DNA threshold must be between 0 and 1")

