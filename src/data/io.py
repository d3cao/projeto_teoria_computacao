import csv
from collections.abc import Iterable, Iterator, Mapping, Sequence
from math import isfinite
from pathlib import Path

from ..models import Sample


SAMPLE_COLUMNS = (
    "id",
    "ccd",
    "phenols",
    "dpph",
    "fps",
    "uv",
    "dna",
    "viable",
)


def write_csv(
    path: Path,
    columns: Sequence[str],
    rows: Iterable[Mapping[str, object]],
) -> None:
    """Persiste uma coleção de registros em um arquivo CSV."""
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _parse_numeric(value: str | None, column: str) -> float:
    """Converte e valida um valor numérico experimental."""
    if value is None:
        raise ValueError(f"Missing value for {column}")

    number = float(value)

    if not isfinite(number) or number < 0:
        raise ValueError(f"{column} must be finite and non-negative")

    return number


def _parse_sample(
    row: Mapping[str, str | None],
    config: dict,
) -> Sample:
    """Converte e valida os dados de uma amostra experimental."""
    sample: Sample = {
        "id": (row["id"] or "").strip(),
        "ccd": (row["ccd"] or "").strip(),
        "phenols": _parse_numeric(row["phenols"], "phenols"),
        "dpph": _parse_numeric(row["dpph"], "dpph"),
        "fps": _parse_numeric(row["fps"], "fps"),
        "uv": _parse_numeric(row["uv"], "uv"),
        "dna": _parse_numeric(row["dna"], "dna"),
        "viable": int(row["viable"] or ""),
    }

    if not sample["id"]:
        raise ValueError("Missing sample ID")

    if sample["ccd"] not in config["ccd"]:
        raise ValueError("Unknown CCD category")

    if max(sample["uv"], sample["dna"]) > 1:
        raise ValueError("UV and DNA must be between 0 and 1")

    if sample["viable"] != int(sample["dna"] >= config["dna_threshold"]):
        raise ValueError("Viability does not match the DNA threshold")

    return sample


def read_samples(
    path: Path,
    config: dict,
) -> Iterator[Sample]:
    """Lê e valida amostras experimentais armazenadas em CSV."""
    ids: set[str] = set()

    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if not set(SAMPLE_COLUMNS).issubset(reader.fieldnames or ()):
            raise ValueError(f"{path}: Missing required columns")

        for row in reader:
            try:
                sample = _parse_sample(row, config)

                if sample["id"] in ids:
                    raise ValueError("Duplicate sample ID")

            except ValueError as error:
                raise ValueError(
                    f"{path}, line {reader.line_num}: {error}"
                ) from error

            ids.add(sample["id"])
            yield sample

        if not ids:
            raise ValueError(f"{path}: No samples found")