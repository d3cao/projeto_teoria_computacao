from typing import Literal, TypedDict


Decision = Literal["ADVANCE", "DISCARD"]


class Sample(TypedDict):
    """Representa uma amostra experimental e seu rótulo de viabilidade."""

    id: str
    ccd: str
    phenols: float
    dpph: float
    fps: float
    uv: float
    dna: float
    viable: int


class StateInfo(TypedDict):
    """Representa as evidências associadas a um estado da máquina."""

    layer: int | None
    prefixes: int
    nonviable: int
    viable: int


class MooreMachine(TypedDict):
    """Representa uma máquina de Moore inferida e seus metadados."""

    alphabet: list[str]
    output_alphabet: list[Decision]
    initial_state: str
    states: dict[str, StateInfo]
    transitions: dict[str, dict[str, str]]
    outputs: dict[str, Decision]
    states_before: int
    states_after: int
    min_support: int

class EvaluationResult(TypedDict):
    """Representa o resultado individual da avaliação de uma amostra."""

    id: str
    decision: Decision
    discard_layer: int | None
    viable: int
    false_discard: int

class InferenceArtifact(TypedDict):
    """Representa a máquina inferida e sua configuração experimental."""

    config: dict
    levels: int
    machine: MooreMachine