import csv
import json
import shutil
import subprocess
from collections import defaultdict
from pathlib import Path

from src.automata.moore import CONTINUATION_STATE
from src.data.io import write_csv
from src.models import MooreMachine


CONFIG_COLUMNS = ("policy_id", "levels", "train_size")
COMPARISON_METRICS = (
    "viable", "nonviable", "false_discards", "correct_discards",
    "discards_after_fps", "discards_after_uv", "uv_assays_saved", "dna_assays_saved",
    "assay_days_saved_min", "assay_days_saved_max",
    "false_discards_after_fps", "false_discards_after_uv",
    "correct_discards_after_fps", "correct_discards_after_uv",
    "false_discard_rate", "false_discard_after_fps_rate", "false_discard_after_uv_rate",
    "discard_efficiency_rate", "discard_efficiency_after_fps_rate",
    "discard_efficiency_after_uv_rate", "uv_assays_saved_rate", "dna_assays_saved_rate",
    "assays_saved_rate",
)
TOPOLOGY_METRICS = (
    "states_before", "states_after", "transitions_before", "transitions_after",
    "observed_transitions_before", "observed_transitions_after",
)
RANK_CHANGE_COLUMNS = (
    "run_id", "seed", "levels", "train_size", "sample_id", "weight_profile",
    "uniform_rank", "rank", "positions_gained", "uniform_score", "score",
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _write_matrix(path: Path, summary: list[dict[str, str]], metrics: tuple[str, ...]) -> None:
    statistics = ("mean", "stdev", "valid_repetitions")
    rows: dict[tuple[str, ...], dict[str, str]] = {}
    for row in summary:
        metric = row["metric"]
        if metric in metrics:
            key = tuple(row[column] for column in CONFIG_COLUMNS)
            record = rows.setdefault(key, {column: row[column] for column in CONFIG_COLUMNS})
            record.update({f"{metric}_{statistic}": row[statistic] for statistic in statistics})
    columns = (*CONFIG_COLUMNS, *(f"{metric}_{stat}" for metric in metrics for stat in statistics))
    write_csv(path, columns, rows.values())


def _write_rank_changes(path: Path, rankings: list[dict[str, str]]) -> None:
    uniform = {
        (row["run_id"], row["sample_id"]): row
        for row in rankings if row["weight_profile"] == "uniform"
    }
    rows = []
    for row in rankings:
        if row["weight_profile"] == "uniform":
            continue
        reference = uniform[row["run_id"], row["sample_id"]]
        rows.append({
            **{key: row[key] for key in RANK_CHANGE_COLUMNS if key in row},
            "uniform_rank": reference["rank"],
            "positions_gained": int(reference["rank"]) - int(row["rank"]),
            "uniform_score": reference["score"],
        })
    write_csv(path, RANK_CHANGE_COLUMNS, rows)


def _plot_sensitivity(plt, directory: Path, summary: list[dict[str, str]]) -> None:
    charts = {
        "false_discard_rate": "Taxa de falsos descartes",
        "discard_efficiency_rate": "Eficiência de descarte",
        "states_before": "Estados antes da fusão",
        "states_after": "Estados após a fusão",
    }
    for metric, label in charts.items():
        fig, axis = plt.subplots(figsize=(7, 4), layout="constrained")
        series = defaultdict(list)
        for row in summary:
            if row["policy_id"] == "moore" and row["metric"] == metric and row["mean"]:
                deviation = float(row["stdev"]) if row["stdev"] else None
                series[int(row["levels"])].append(
                    (int(row["train_size"]), float(row["mean"]), deviation)
                )
        for levels, points in sorted(series.items()):
            points.sort()
            line, = axis.plot([x for x, _, _ in points], [y for _, y, _ in points],
                              marker="o", label=f"{levels} níveis")
            with_deviation = [(x, y, sd) for x, y, sd in points if sd is not None]
            if with_deviation:
                x, y, sd = zip(*with_deviation)
                axis.errorbar(x, y, yerr=sd, fmt="none", capsize=3, color=line.get_color())
        axis.set(xlabel="Amostras de treino", ylabel=label)
        if series:
            axis.legend()
        else:
            axis.text(0.5, 0.5, "Sem repetições válidas", ha="center", transform=axis.transAxes)
        fig.savefig(directory / f"sensitivity_{metric}.svg")
        plt.close(fig)


def _plot_scores(plt, directory: Path, rankings: list[dict[str, str]]) -> None:
    groups = defaultdict(list)
    for row in rankings:
        groups[int(row["levels"]), int(row["train_size"]), row["weight_profile"]].append(
            float(row["score"])
        )
    configurations = sorted({(levels, size) for levels, size, _ in groups})
    for levels, size in configurations:
        fig, axis = plt.subplots(figsize=(7, 4), layout="constrained")
        for (group_levels, group_size, profile), scores in groups.items():
            if (group_levels, group_size) == (levels, size):
                axis.hist(scores, bins=10, range=(0, 1), histtype="step", label=profile)
        axis.set(xlabel="Escore", ylabel="Aprovados por faixa", xlim=(0, 1),
                 title=f"{levels} níveis · {size} amostras de treino")
        axis.legend()
        fig.savefig(directory / f"scores_levels_{levels}_train_{size}.svg")
        plt.close(fig)


def _moore_dot(machine: MooreMachine) -> str:
    quote = json.dumps
    lines = ["digraph Moore {", "  rankdir=LR;", '  "__start" [shape=point];',
             f'  "__start" -> {quote(machine["initial_state"])};']
    for state, info in machine["states"].items():
        caption = f'{state}\n{machine["outputs"][state]}'
        if info["layer"] is not None:
            caption += f'\nCamada {info["layer"]}'
        fill = "#fbd8d0" if machine["outputs"][state] == "DISCARD" else "#e1eef8"
        lines.append(f'  {quote(state)} [label={quote(caption)}, style=filled, fillcolor="{fill}"];')
    for origin, transitions in machine["transitions"].items():
        by_destination = defaultdict(list)
        for symbol, destination in transitions.items():
            by_destination[destination].append(symbol)
        for destination, symbols in by_destination.items():
            style = "dashed" if destination == CONTINUATION_STATE else "solid"
            label = quote(", ".join(symbols))
            lines.append(f"  {quote(origin)} -> {quote(destination)} [label={label}, style={style}];")
    lines.append("}")
    return "\n".join(lines) + "\n"


def generate_report(experiment_dir: Path, output_dir: Path) -> list[str]:
    """Gera as tabelas e as figuras a partir de uma bateria concluída."""
    manifest = json.loads((experiment_dir / "manifest.json").read_text(encoding="utf-8"))
    all_metrics = _read_csv(experiment_dir / "metrics_summary.csv")
    summary = [row for row in all_metrics if not row["baseline"]]
    rankings = _read_csv(experiment_dir / "rankings.csv") if "score" in manifest else None
    diagram = None
    if "diagram_run" in manifest:
        artifact = json.loads((experiment_dir / "moore.json").read_text(encoding="utf-8"))
        diagram = _moore_dot(artifact["machine"])

    output_dir.mkdir(parents=True)
    _write_matrix(output_dir / "comparison.csv", summary, COMPARISON_METRICS)
    _write_matrix(output_dir / "topology.csv", summary, TOPOLOGY_METRICS)
    if rankings is not None:
        shutil.copyfile(experiment_dir / "rankings.csv", output_dir / "rankings.csv")
        _write_rank_changes(output_dir / "rank_changes.csv", rankings)

    warnings = []
    if diagram is not None:
        dot_path = output_dir / "moore.dot"
        dot_path.write_text(diagram, encoding="utf-8")
        dot = shutil.which("dot")
        if dot is None:
            warnings.append("Install Graphviz and add dot to PATH to render moore.svg.")
        else:
            result = subprocess.run(
                [dot, "-Tsvg", str(dot_path), "-o", str(output_dir / "moore.svg")],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            if result.returncode:
                warnings.append(f"Graphviz could not render moore.svg: {result.stderr.strip()}")

    try:
        import matplotlib
    except ModuleNotFoundError as error:
        if error.name != "matplotlib":
            raise
        warnings.append("Install Matplotlib to render the sensitivity and score figures.")
    else:
        matplotlib.use("Agg")
        from matplotlib import pyplot as plt

        _plot_sensitivity(plt, output_dir, summary)
        if rankings:
            _plot_scores(plt, output_dir, rankings)
    return warnings
