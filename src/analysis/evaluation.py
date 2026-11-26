from collections.abc import Iterable, Iterator

from src.automata.discretize import discretize
from src.models import EvaluationResult, MooreMachine, Sample
from src.automata.moore import traverse


def _find_discard_layer(
    machine: MooreMachine,
    trace: tuple[str, ...],
) -> int | None:
    """Identifica a primeira camada em que a máquina recomenda o descarte."""
    for layer, state in enumerate(traverse(machine, trace)):
        if machine["outputs"][state] == "DISCARD":
            return layer

    return None


def _build_result(sample: Sample, discard_layer: int | None) -> EvaluationResult:
    """Monta o resultado individual a partir da primeira camada de descarte."""
    discarded = discard_layer is not None
    return {
        "id": sample["id"],
        "decision": "DISCARD" if discarded else "ADVANCE",
        "discard_layer": discard_layer,
        "viable": sample["viable"],
        "false_discard": int(discarded and sample["viable"] == 1),
    }


def evaluate(
    machine: MooreMachine,
    samples: Iterable[Sample],
    config: dict,
    levels: int,
) -> Iterator[EvaluationResult]:
    """Avalia as decisões da máquina de Moore sobre amostras experimentais."""
    for sample in samples:
        trace = discretize(sample, config, levels)
        discard_layer = _find_discard_layer(machine, trace)
        yield _build_result(sample, discard_layer)


def evaluate_no_pruning(samples: Iterable[Sample]) -> Iterator[EvaluationResult]:
    """Encaminha todas as amostras até a análise molecular."""
    for sample in samples:
        yield _build_result(sample, None)


def evaluate_fps_cutoff(samples: Iterable[Sample]) -> Iterator[EvaluationResult]:
    """Descarta após a quarta camada as amostras com FPS menor ou igual a 6."""
    for sample in samples:
        discard_layer = 4 if sample["fps"] <= 6 else None
        yield _build_result(sample, discard_layer)
