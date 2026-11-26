from bisect import bisect_left, bisect_right

from ..models import Sample


FIVE_TO_THREE_LEVELS = (0, 0, 1, 2, 2)


def build_alphabet(
    config: dict,
    levels: int,
) -> list[tuple[str, ...]]:
    """Constrói os grupos de símbolos possíveis para cada
    camada experimental.
    """
    if levels not in (3, 5):
        raise ValueError("Levels must be either 3 or 5")

    layer_sizes = {
        "ccd": len(config["ccd"]),
        "phenols": 3,
        "dpph": levels,
        "fps": levels,
        "uv": 3,
    }

    return [
        tuple(f"{layer}:{index}" for index in range(1, size + 1))
        for layer, size in layer_sizes.items()
    ]


def _classify_numeric(
    value: float,
    thresholds: list[float],
    *,
    inclusive_last: bool = False,
) -> int:
    """Determina o índice do intervalo ao qual um valor pertence,
    considerando a inclusão do último limite quando necessário.
    """
    if inclusive_last and value == thresholds[-1]:
        return bisect_left(thresholds, value)

    return bisect_right(thresholds, value)


def discretize(
    sample: Sample,
    config: dict,
    levels: int,
) -> tuple[str, ...]:
    """Converte os resultados experimentais de uma amostra
    em um rastro de símbolos ordenados por camada.
    """
    alphabet = build_alphabet(config, levels)
    thresholds = config["thresholds"]

    ccd = config["ccd"].index(sample["ccd"])

    phenols = _classify_numeric(
        sample["phenols"],
        thresholds["phenols"],
        inclusive_last=True,
    )

    dpph = _classify_numeric(
        sample["dpph"],
        thresholds["dpph"],
        inclusive_last=True,
    )

    fps = _classify_numeric(sample["fps"], thresholds["fps"])
    uv = _classify_numeric(sample["uv"], thresholds["uv"])

    if levels == 3:
        dpph = FIVE_TO_THREE_LEVELS[dpph]
        fps = FIVE_TO_THREE_LEVELS[fps]

    indices = (ccd, phenols, dpph, fps, uv)

    return tuple(
        group[index]
        for group, index in zip(alphabet, indices)
    )