import csv
import json
import platform
from collections import defaultdict
from collections.abc import Iterator, Sequence
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, stdev

from src.analysis.evaluation import evaluate, evaluate_fps_cutoff, evaluate_no_pruning
from src.analysis.metrics import Metrics, summarize_compaction, summarize_decisions
from src.analysis.scoring import LAYERS, load_scoring, rank_samples
from src.automata.discretize import build_alphabet, discretize
from src.automata.moore import infer_moore
from src.config import load_config
from src.data.generation import generate_datasets
from src.data.io import write_csv
from src.models import EvaluationResult


DECISION_COLUMNS = (
    "run_id", "seed", "policy_id", "levels", "train_size",
    "sample_id", "decision", "discard_layer", "viable", "false_discard",
)
SUMMARY_COLUMNS = (
    "policy_id", "levels", "train_size", "baseline", "metric",
    "mean", "stdev", "valid_repetitions",
)
BASELINES = (
    ("no_pruning", evaluate_no_pruning),
    ("fps_cutoff", evaluate_fps_cutoff),
)
RANKING_COLUMNS = (
    "run_id", "seed", "policy_id", "levels", "train_size", "sample_id",
    "weight_profile", *(f"score_{layer}" for layer in LAYERS), "score", "rank",
)


@dataclass
class RunMetrics:
    """Identifica as métricas de uma política em uma repetição."""

    run_id: str
    seed: int
    policy_id: str
    metrics: Metrics
    levels: int | None = None
    train_size: int | None = None

    def metadata(self) -> dict[str, object]:
        """Retorna os campos de identificação comuns aos arquivos CSV."""
        return {
            "run_id": self.run_id,
            "seed": self.seed,
            "policy_id": self.policy_id,
            "levels": self.levels,
            "train_size": self.train_size,
        }


def _integers(spec: dict, name: str) -> list[int]:
    values = spec[name]
    if (
        not isinstance(values, list)
        or not values
        or any(type(value) is not int for value in values)
    ):
        raise ValueError(f"{name} must be a nonempty list of integers")
    if len(set(values)) != len(values):
        raise ValueError(f"{name} must not contain duplicates")
    return values


def _positive_integer(spec: dict, name: str) -> int:
    value = spec[name]
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _decision_rows(
    run: RunMetrics, results: Sequence[EvaluationResult]
) -> Iterator[dict[str, object]]:
    metadata = run.metadata()
    for row in results:
        yield {
            **metadata,
            "sample_id": row["id"],
            "decision": row["decision"],
            "discard_layer": row["discard_layer"],
            "viable": row["viable"],
            "false_discard": row["false_discard"],
        }


def _summarize(runs: list[RunMetrics]) -> list[dict[str, object]]:
    baselines = {
        (run.seed, run.policy_id): run.metrics for run in runs if run.levels is None
    }
    groups: dict[tuple[str, int | None, int | None, str, str], list[int | float]]
    groups = defaultdict(list)
    for run in runs:
        configuration = (run.policy_id, run.levels, run.train_size)
        for metric, value in run.metrics.items():
            values = groups[(*configuration, "", metric)]
            if value is not None:
                values.append(value)
            if run.levels is not None and metric.endswith("_rate"):
                for baseline, _ in BASELINES:
                    deltas = groups[(*configuration, baseline, metric)]
                    reference = baselines[run.seed, baseline][metric]
                    if value is not None and reference is not None:
                        deltas.append(value - reference)

    return [
        {
            "policy_id": policy,
            "levels": levels,
            "train_size": train_size,
            "baseline": baseline,
            "metric": metric,
            "mean": mean(values) if values else None,
            "stdev": stdev(values) if len(values) > 1 else None,
            "valid_repetitions": len(values),
        }
        for (policy, levels, train_size, baseline, metric), values in groups.items()
    ]


def run_experiment(spec_path: Path, output_dir: Path) -> None:
    """Executa e exporta uma bateria comparativa pareada por semente."""
    spec = json.loads(spec_path.read_text(encoding="utf-8-sig"))
    if not isinstance(spec, dict):
        raise ValueError("Experiment specification must be a JSON object")
    seeds = _integers(spec, "seeds")
    train_sizes = _integers(spec, "train_sizes")
    levels = _integers(spec, "levels")
    test_size = _positive_integer(spec, "test_size")
    min_support = _positive_integer(spec, "min_support")
    if min(train_sizes) < 1 or not set(levels).issubset({3, 5}):
        raise ValueError("Training sizes must be positive and levels must be 3 or 5")
    config_path = (spec_path.resolve().parent / spec["config"]).resolve()
    config = load_config(config_path)
    scoring = load_scoring(spec["score"], config["ccd"]) if "score" in spec else None
    diagram_run = spec.get("diagram_run")
    if "diagram_run" in spec:
        options = {"seed": seeds, "levels": levels, "train_size": train_sizes}
        if not isinstance(diagram_run, dict) or set(diagram_run) != set(options) or any(
            type(diagram_run[key]) is not int or diagram_run[key] not in values
            for key, values in options.items()
        ):
            raise ValueError("diagram_run must select a seed, levels and train_size from the experiment")

    output_dir.mkdir(parents=True)
    runs: list[RunMetrics] = []
    with ExitStack() as stack:
        file = stack.enter_context(
            (output_dir / "decisions.csv").open("w", encoding="utf-8", newline="")
        )
        writer = csv.DictWriter(file, fieldnames=DECISION_COLUMNS)
        writer.writeheader()
        if scoring is not None:
            ranking_file = stack.enter_context(
                (output_dir / "rankings.csv").open("w", encoding="utf-8", newline="")
            )
            ranking_writer = csv.DictWriter(ranking_file, fieldnames=RANKING_COLUMNS)
            ranking_writer.writeheader()
        for seed in seeds:
            train, test = generate_datasets(config, seed, max(train_sizes), test_size)
            for policy, evaluator in BASELINES:
                results = list(evaluator(test))
                run = RunMetrics(f"seed-{seed}", seed, policy, summarize_decisions(results))
                runs.append(run)
                writer.writerows(_decision_rows(run, results))

            for level in levels:
                alphabet = build_alphabet(config, level)
                traces = [
                    (discretize(sample, config, level), sample["viable"])
                    for sample in train
                ]
                for size in train_sizes:
                    training = traces[:size]
                    machine = infer_moore(training, alphabet, min_support)
                    tree = infer_moore(training, alphabet, min_support, merge_states=False)
                    results = list(evaluate(machine, test, config, level))
                    metrics = summarize_decisions(results) | summarize_compaction(tree, machine)
                    run = RunMetrics(
                        f"seed-{seed}-levels-{level}-train-{size}",
                        seed, "moore", metrics, level, size,
                    )
                    runs.append(run)
                    writer.writerows(_decision_rows(run, results))
                    if scoring is not None:
                        approved = (
                            sample for sample, row in zip(test, results)
                            if row["decision"] == "ADVANCE" and row["viable"] == 1
                        )
                        metadata = run.metadata()
                        ranking_writer.writerows(
                            metadata | row for row in rank_samples(approved, scoring)
                        )
                    if diagram_run == {"seed": seed, "levels": level, "train_size": size}:
                        artifact = {"config": config, "levels": level, "machine": machine}
                        (output_dir / "moore.json").write_text(
                            json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8",
                        )

    rows = [run.metadata() | run.metrics for run in runs]
    columns = tuple(dict.fromkeys(column for row in rows for column in row))
    write_csv(output_dir / "metrics_by_seed.csv", columns, rows)
    write_csv(output_dir / "metrics_summary.csv", SUMMARY_COLUMNS, _summarize(runs))

    manifest = {
        "config_path": str(config_path),
        "config": config,
        "seeds": seeds,
        "train_sizes": train_sizes,
        "test_size": test_size,
        "levels": levels,
        "min_support": min_support,
        "python_version": platform.python_version(),
    }
    if scoring is not None:
        manifest["score"] = scoring
    if diagram_run is not None:
        manifest["diagram_run"] = diagram_run
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
