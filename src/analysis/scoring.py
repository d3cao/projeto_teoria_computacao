from bisect import bisect_right
from collections.abc import Iterable, Iterator
from fractions import Fraction
from math import isfinite
from typing import TypedDict

from src.models import Sample


NUMERIC_LAYERS = ("phenols", "dpph", "fps", "uv", "dna")
LAYERS = ("ccd", *NUMERIC_LAYERS)


class Bands(TypedDict):
    """Representa cortes crescentes e uma pontuação por faixa."""

    thresholds: list[float]
    scores: list[float]


class ScoreConfig(TypedDict):
    """Define as faixas e os perfis efetivos usados no ranking."""

    ccd: dict[str, float]
    bands: dict[str, Bands]
    profiles: dict[str, dict[str, float]]


def _number(value: object, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number")
    try:
        number = float(value)
    except OverflowError as error:
        raise ValueError(f"{name} must be a finite number") from error
    if not isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    return number


def _score(value: object, name: str) -> float:
    score = _number(value, name)
    if not 0 <= score <= 1:
        raise ValueError(f"{name} must be between 0 and 1")
    return score


def load_scoring(spec: object, categories: list[str]) -> ScoreConfig:
    """Valida a configuração e completa os pesos omitidos com 1."""
    if not isinstance(spec, dict):
        raise ValueError("score must be an object")
    ccd = spec["ccd"]
    if not isinstance(ccd, dict) or set(ccd) != set(categories):
        raise ValueError("score.ccd must contain all configured CCD categories")
    tables = spec["bands"]
    if not isinstance(tables, dict) or set(tables) != set(NUMERIC_LAYERS):
        raise ValueError("score.bands must contain phenols, dpph, fps, uv and dna")

    bands: dict[str, Bands] = {}
    for layer in NUMERIC_LAYERS:
        table = tables[layer]
        if not isinstance(table, dict):
            raise ValueError(f"score.bands.{layer} must be an object")
        cuts, raw_scores = table["thresholds"], table["scores"]
        if not isinstance(cuts, list) or not isinstance(raw_scores, list):
            raise ValueError(f"{layer} thresholds and scores must be lists")
        thresholds = [_number(value, f"{layer} threshold") for value in cuts]
        scores = [_score(value, f"{layer} score") for value in raw_scores]
        if len(scores) != len(thresholds) + 1:
            raise ValueError(f"{layer} requires one score per band")
        if thresholds != sorted(set(thresholds)) or any(value <= 0 for value in thresholds):
            raise ValueError(f"{layer} thresholds must be positive and strictly increasing")
        if layer in ("uv", "dna") and thresholds and thresholds[-1] > 1:
            raise ValueError(f"{layer} thresholds must be at most 1")
        if layer == "dpph" and scores != sorted(scores, reverse=True):
            raise ValueError("DPPH scores must not increase with IC50")
        bands[layer] = {"thresholds": thresholds, "scores": scores}

    custom = spec.get("profiles", {})
    if not isinstance(custom, dict) or "uniform" in custom:
        raise ValueError("score.profiles must be an object; uniform is reserved")
    profiles: dict[str, dict[str, float]] = {"uniform": dict.fromkeys(LAYERS, 1.0)}
    for name, weights in custom.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Weight profile names must be nonempty")
        if not isinstance(weights, dict) or not set(weights).issubset(LAYERS):
            raise ValueError(f"{name} weights must use the six known layers")
        profile = {layer: _number(weights.get(layer, 1), f"{name}.{layer}") for layer in LAYERS}
        if any(weight <= 0 for weight in profile.values()):
            raise ValueError(f"{name} weights must be strictly positive")
        profiles[name] = profile

    return {
        "ccd": {category: _score(ccd[category], f"ccd.{category}") for category in categories},
        "bands": bands,
        "profiles": profiles,
    }


def _components(sample: Sample, config: ScoreConfig) -> dict[str, float]:
    components = {"ccd": config["ccd"][sample["ccd"]]}
    for layer in NUMERIC_LAYERS:
        band = config["bands"][layer]
        components[layer] = band["scores"][bisect_right(band["thresholds"], sample[layer])]
    return components


def rank_samples(samples: Iterable[Sample], config: ScoreConfig) -> Iterator[dict[str, object]]:
    """Ordena a mesma coorte por perfil e atribui posições densas aos empates."""
    cohort = [(sample["id"], _components(sample, config)) for sample in samples]
    for profile, weights in config["profiles"].items():
        # Frações preservam os empates antes da conversão para o CSV.
        fractions = {layer: Fraction(str(weight)) for layer, weight in weights.items()}
        total_weight = sum(fractions.values())
        scores = []
        for sample_id, components in cohort:
            weighted_sum = sum(
                Fraction(str(value)) * fractions[layer]
                for layer, value in components.items()
            )
            scores.append((weighted_sum / total_weight, sample_id, components))
        previous = None
        rank = 0
        for score, sample_id, components in sorted(scores, key=lambda row: (-row[0], row[1])):
            if score != previous:
                rank += 1
                previous = score
            yield {
                "sample_id": sample_id,
                "weight_profile": profile,
                **{f"score_{layer}": value for layer, value in components.items()},
                "score": float(score),
                "rank": rank,
            }
