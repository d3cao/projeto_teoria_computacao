import argparse
import json
from pathlib import Path

from src.config import CONFIG_PATH, load_config
from src.data.generation import generate_datasets
from src.data.io import SAMPLE_COLUMNS, read_samples, write_csv
from src.automata.discretize import build_alphabet, discretize
from src.analysis.evaluation import evaluate
from src.analysis.experiments import run_experiment
from src.analysis.reports import generate_report
from src.models import InferenceArtifact
from src.automata.moore import infer_moore


def _generate(args: argparse.Namespace) -> None:
    """Gera e persiste os datasets de treinamento e teste."""
    paths = {path.resolve() for path in (args.train, args.test, args.config)}

    if len(paths) != 3:
        raise ValueError("Configuration and dataset paths must be distinct")

    config = load_config(args.config)
    train, test = generate_datasets(
        config, args.seed, args.train_size, args.test_size
    )

    write_csv(args.train, SAMPLE_COLUMNS, train)
    write_csv(args.test, SAMPLE_COLUMNS, test)

    print(f"{args.train}: {len(train)} samples")
    print(f"{args.test}: {len(test)} samples")


def _infer(args: argparse.Namespace) -> None:
    """Infere e persiste a máquina de Moore."""
    if args.output.resolve() in (args.csv.resolve(), args.config.resolve()):
        raise ValueError("Output must differ from input files")

    config = load_config(args.config)
    alphabet = build_alphabet(config, args.levels)

    traces = (
        (discretize(sample, config, args.levels), sample["viable"])
        for sample in read_samples(args.csv, config)
    )

    machine = infer_moore(traces, alphabet, args.min_support)

    artifact: InferenceArtifact = {
        "config": config,
        "levels": args.levels,
        "machine": machine,
    }

    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"States: {machine['states_before']} -> {machine['states_after']}")
    print(f"Model saved to {args.output}")


def _evaluate(args: argparse.Namespace) -> None:
    """Avalia a máquina e exporta os resultados individuais."""
    if args.output.resolve() in (args.csv.resolve(), args.model.resolve()):
        raise ValueError("Output must differ from input files")

    artifact: InferenceArtifact = json.loads(
        args.model.read_text(encoding="utf-8")
    )

    config = artifact["config"]
    levels = artifact["levels"]
    machine = artifact["machine"]

    samples = read_samples(args.csv, config)
    results = list(evaluate(machine, samples, config, levels))

    write_csv(args.output, tuple(results[0]), results)

    viable = sum(result["viable"] for result in results)
    false_discards = sum(result["false_discard"] for result in results)
    discards = sum(result["decision"] == "DISCARD" for result in results)

    rate = f"{false_discards / viable:.2%}" if viable else "undefined"

    print(f"Samples: {len(results)}")
    print(f"Discards: {discards}")
    print(f"False discards: {false_discards}/{viable} ({rate})")
    print(f"Results saved to {args.output}")


def _experiment(args: argparse.Namespace) -> None:
    """Executa a bateria comparativa e informa o diretório de saída."""
    run_experiment(args.spec, args.output_dir)
    print(f"Experiment results saved to {args.output_dir}")


def _report(args: argparse.Namespace) -> None:
    """Exporta os materiais e informa dependências de visualização ausentes."""
    warnings = generate_report(args.experiment_dir, args.output_dir)
    for warning in warnings:
        print(f"Warning: {warning}")
    print(f"Report saved to {args.output_dir}")


def _build_parser() -> argparse.ArgumentParser:
    """Configura os comandos e argumentos da interface CLI."""
    parser = argparse.ArgumentParser(
        description="Conservative Moore machine for extract screening"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    generate_parser = commands.add_parser("generate", help="Generate synthetic datasets")
    generate_parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    generate_parser.add_argument("--seed", type=int, default=42)
    generate_parser.add_argument("--train-size", type=int, default=2000)
    generate_parser.add_argument("--test-size", type=int, default=500)
    generate_parser.add_argument("--train", type=Path, default=Path("data/train.csv"))
    generate_parser.add_argument("--test", type=Path, default=Path("data/test.csv"))
    generate_parser.set_defaults(handler=_generate)

    infer_parser = commands.add_parser("infer", help="Infer a Moore machine")
    infer_parser.add_argument("csv", type=Path)
    infer_parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    infer_parser.add_argument("--levels", type=int, choices=(3, 5), default=3)
    infer_parser.add_argument("--min-support", type=int, default=3)
    infer_parser.add_argument("--output", type=Path, default=Path("data/moore.json"))
    infer_parser.set_defaults(handler=_infer)

    evaluate_parser = commands.add_parser("evaluate", help="Evaluate an inferred Moore machine")
    evaluate_parser.add_argument("model", type=Path)
    evaluate_parser.add_argument("csv", type=Path)
    evaluate_parser.add_argument("--output", type=Path, default=Path("data/decisions.csv"))
    evaluate_parser.set_defaults(handler=_evaluate)

    experiment_parser = commands.add_parser(
        "experiment", help="Run a paired comparison over multiple seeds"
    )
    experiment_parser.add_argument("--spec", type=Path, required=True)
    experiment_parser.add_argument("--output-dir", type=Path, required=True)
    experiment_parser.set_defaults(handler=_experiment)

    report_parser = commands.add_parser("report", help="Export tables and figures from an experiment")
    report_parser.add_argument("--experiment-dir", type=Path, required=True)
    report_parser.add_argument("--output-dir", type=Path, required=True)
    report_parser.set_defaults(handler=_report)

    return parser


def run() -> None:
    """Executa o comando selecionado e centraliza o tratamento de erros."""
    parser = _build_parser()
    args = parser.parse_args()

    try:
        args.handler(args)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"Error: {error}\n")
