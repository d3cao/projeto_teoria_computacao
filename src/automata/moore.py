from collections.abc import Iterable, Iterator
from itertools import chain

from src.models import Decision, MooreMachine, StateInfo


CONTINUATION_STATE = "continuation"
DECISION_LAYERS = (4, 5)

Trace = tuple[str, ...]
PrefixCounts = dict[Trace, list[int]]
StateSignature = tuple[int, Decision, tuple[bool, bool], Trace]


def _count_prefixes(
    traces: Iterable[tuple[Trace, int]],
    alphabet: list[Trace],
) -> PrefixCounts:
    """Contabiliza as evidências de viabilidade de cada prefixo observado."""
    counts: PrefixCounts = {(): [0, 0]}

    for trace, viable in traces:
        trace = tuple(trace)

        if viable not in (0, 1) or len(trace) != len(alphabet):
            raise ValueError("Invalid trace or viability label")

        if any(symbol not in group for symbol, group in zip(trace, alphabet)):
            raise ValueError("Invalid trace symbol")

        for layer in range(len(trace) + 1):
            counts.setdefault(trace[:layer], [0, 0])[viable] += 1

    return counts


def _determine_output(
    layer: int, nonviable: int, viable: int, min_support: int
) -> Decision:
    """Aplica a regra conservadora de descarte."""
    if layer in DECISION_LAYERS and nonviable >= min_support and not viable:
        return "DISCARD"

    return "ADVANCE"


def _build_states(
    counts: PrefixCounts,
    symbols: list[str],
    min_support: int,
    merge_states: bool,
) -> MooreMachine:
    """Constrói a máquina e funde estados equivalentes de baixo para cima."""
    states: dict[str, StateInfo] = {
        CONTINUATION_STATE: {
            "layer": None, "prefixes": 0, "nonviable": 0, "viable": 0
        }
    }
    outputs: dict[str, Decision] = {CONTINUATION_STATE: "ADVANCE"}
    transitions = {CONTINUATION_STATE: dict.fromkeys(symbols, CONTINUATION_STATE)}

    representatives: dict[Trace, str] = {}
    equivalents: dict[StateSignature, str] = {}

    for prefix in sorted(counts, key=lambda p: (-len(p), p)):
        layer = len(prefix)
        nonviable, viable = counts[prefix]
        output = _determine_output(layer, nonviable, viable, min_support)
        evidence = (bool(nonviable), bool(viable))

        destinations = {
            symbol: representatives.get(prefix + (symbol,), CONTINUATION_STATE)
            for symbol in symbols
        }

        signature = (layer, output, evidence, tuple(destinations.values()))
        state = equivalents.get(signature) if merge_states else None

        if state is None:
            state = f"q{len(states) - 1}"
            equivalents[signature] = state
            states[state] = {
                "layer": layer, "prefixes": 0, "nonviable": 0, "viable": 0
            }
            outputs[state] = output
            transitions[state] = destinations

        representatives[prefix] = state
        states[state]["prefixes"] += 1
        states[state]["nonviable"] += nonviable
        states[state]["viable"] += viable

    return {
        "alphabet": symbols,
        "output_alphabet": ["ADVANCE", "DISCARD"],
        "initial_state": representatives[()],
        "states": states,
        "transitions": transitions,
        "outputs": outputs,
        "states_before": len(counts) + 1,
        "states_after": len(states),
        "min_support": min_support,
    }


def infer_moore(
    traces: Iterable[tuple[Trace, int]],
    alphabet: list[Trace],
    min_support: int = 3,
    *,
    merge_states: bool = True,
) -> MooreMachine:
    """Infere uma máquina de Moore conservadora a partir de rastros rotulados."""
    if min_support < 1:
        raise ValueError("Minimum support must be positive")

    symbols = list(chain.from_iterable(alphabet))
    counts = _count_prefixes(traces, alphabet)

    return _build_states(counts, symbols, min_support, merge_states)


def traverse(machine: MooreMachine, trace: Iterable[str]) -> Iterator[str]:
    """Percorre a máquina de Moore, produzindo os estados visitados."""
    state = machine["initial_state"]
    yield state

    for symbol in trace:
        state = machine["transitions"][state][symbol]
        yield state