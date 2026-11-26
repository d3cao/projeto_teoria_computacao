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
        discarded = discard_layer is not None

        yield {
            "id": sample["id"],
            "decision": "DISCARD" if discarded else "ADVANCE",
            "discard_layer": discard_layer,
            "viable": sample["viable"],
            "false_discard": int(discarded and sample["viable"] == 1),
        }