from collections import Counter
from collections.abc import Iterable

from src.automata.moore import CONTINUATION_STATE
from src.models import EvaluationResult, MooreMachine


Metrics = dict[str, int | float | None]


def _rate(count: int, total: int) -> float | None:
    return count / total if total else None


def summarize_decisions(results: Iterable[EvaluationResult]) -> Metrics:
    """Calcula a preservação de viáveis, a eficiência e a economia de ensaios."""
    counts = Counter((row["discard_layer"], row["viable"]) for row in results)
    samples = counts.total()
    viable = sum(count for (_, label), count in counts.items() if label == 1)
    nonviable = samples - viable
    false_fps, false_uv = counts[4, 1], counts[5, 1]
    correct_fps, correct_uv = counts[4, 0], counts[5, 0]
    false_discards = false_fps + false_uv
    correct_discards = correct_fps + correct_uv
    discards_after_fps = false_fps + correct_fps
    discards_after_uv = false_uv + correct_uv
    uv_saved = discards_after_fps
    dna_saved = discards_after_fps + discards_after_uv

    return {
        "samples": samples,
        "viable": viable,
        "nonviable": nonviable,
        "discards_after_fps": discards_after_fps,
        "discards_after_uv": discards_after_uv,
        "false_discards": false_discards,
        "false_discards_after_fps": false_fps,
        "false_discards_after_uv": false_uv,
        "false_discard_rate": _rate(false_discards, viable),
        "false_discard_after_fps_rate": _rate(false_fps, viable),
        "false_discard_after_uv_rate": _rate(false_uv, viable),
        "correct_discards": correct_discards,
        "correct_discards_after_fps": correct_fps,
        "correct_discards_after_uv": correct_uv,
        "discard_efficiency_rate": _rate(correct_discards, nonviable),
        "discard_efficiency_after_fps_rate": _rate(correct_fps, nonviable),
        "discard_efficiency_after_uv_rate": _rate(correct_uv, nonviable),
        "uv_assays_saved": uv_saved,
        "dna_assays_saved": dna_saved,
        "assays_saved": uv_saved + dna_saved,
        "uv_assays_saved_rate": _rate(uv_saved, samples),
        "dna_assays_saved_rate": _rate(dna_saved, samples),
        "assays_saved_rate": _rate(uv_saved + dna_saved, 2 * samples),
    }


def summarize_compaction(before: MooreMachine, after: MooreMachine) -> Metrics:
    """Compara a árvore e a máquina sob a mesma convenção de completude."""
    metrics: Metrics = {}
    for suffix, machine in (("before", before), ("after", after)):
        transitions = machine["transitions"].values()
        metrics[f"states_{suffix}"] = len(machine["states"])
        metrics[f"transitions_{suffix}"] = sum(len(row) for row in transitions)
        metrics[f"observed_transitions_{suffix}"] = sum(
            destination != CONTINUATION_STATE
            for row in transitions
            for destination in row.values()
        )
    return metrics
