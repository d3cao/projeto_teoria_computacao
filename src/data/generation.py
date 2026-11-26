from bisect import bisect_right
from collections.abc import Iterator
from math import exp
from random import Random

from ..models import Sample


def _generate_reading(
    parameters: list[float],
    potential: float,
    rng: Random,
) -> float:
    """Gera uma leitura experimental considerando o potencial
    latente da amostra e o ruído gaussiano.
    """
    mean, coefficient, noise = parameters

    return mean + coefficient * potential + rng.gauss(0, noise)


def generate_samples(
    config: dict,
    rng: Random,
    size: int,
    prefix: str,
) -> Iterator[Sample]:
    """Gera amostras sintéticas individualmente, simulando os
    resultados dos ensaios e a viabilidade dos extratos.
    """
    simulation = config["simulation"]

    for index in range(1, size + 1):
        potential = rng.gauss(0, 1)

        profile = _generate_reading(simulation["ccd"], potential, rng)
        phenols = _generate_reading(simulation["phenols"], potential, rng)
        dpph = _generate_reading(simulation["log_dpph"], potential, rng)
        fps = _generate_reading(simulation["log_fps"], potential, rng)

        phenols = max(0, phenols)
        dpph = exp(dpph)
        fps = exp(fps)

        uv = _generate_reading(simulation["uv"], potential, rng)

        if rng.random() < simulation["uv_failure_probability"]:
            uv -= simulation["uv_loss"]

        uv = round(min(1, max(0, uv)), 6)

        dna = _generate_reading(simulation["dna"], potential, rng)
        dna += simulation["uv_weight_in_dna"] * uv

        if rng.random() < simulation["dna_failure_probability"]:
            dna -= simulation["dna_loss"]

        dna = round(min(1, max(0, dna)), 6)

        ccd_index = bisect_right(simulation["ccd_thresholds"], profile)
        viable = int(dna >= config["dna_threshold"])

        yield {
            "id": f"{prefix}-{index:06d}",
            "ccd": config["ccd"][ccd_index],
            "phenols": round(phenols, 6),
            "dpph": round(dpph, 6),
            "fps": round(fps, 6),
            "uv": uv,
            "dna": dna,
            "viable": viable,
        }


def generate_datasets(
    config: dict,
    seed: int = 42,
    train_size: int = 2000,
    test_size: int = 500,
) -> tuple[list[Sample], list[Sample]]:
    """Gera os datasets de treinamento e teste utilizando fluxos
    pseudoaleatórios distintos derivados de uma mesma semente.
    """
    if min(train_size, test_size) < 1:
        raise ValueError("Dataset sizes must be positive")

    seed_rng = Random(seed)
    train_rng = Random(seed_rng.getrandbits(128))
    test_rng = Random(seed_rng.getrandbits(128))

    train = list(generate_samples(config, train_rng, train_size, "train"))
    test = list(generate_samples(config, test_rng, test_size, "test"))

    return train, test