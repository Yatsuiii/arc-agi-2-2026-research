"""Program AST: a typed expression tree over `dsl.primitives.PRIMITIVES`.

A `Program` is one of:
- `INPUT` node (`op="input"`) — the grid the whole program is applied to.
  The only place a caller's data enters the tree.
- a literal node (`op="literal"`) — a constant value of some `Type`.
- a call node (`op=<primitive name>`) — its `args` are child `Program`s.

Evaluation never receives, and no node type can carry, a test output —
`evaluate`'s signature takes exactly one `Grid`, the value bound to
`INPUT`.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.gen002.dsl.primitives import PRIMITIVES
from src.gen002.dsl.types import Grid, ProgramError, Type

INPUT_COST = 0
LITERAL_COST = 1


@dataclass(frozen=True)
class Program:
    op: str
    args: tuple
    type_: Type
    literal_value: object = None
    """Set only when `op == "literal"`; `args` is empty in that case.
    Kept as a separate field (rather than overloading `args`) so `args`
    always means "child Programs" everywhere else in this module."""

    def cost(self) -> int:
        if self.op == "input":
            return INPUT_COST
        if self.op == "literal":
            return LITERAL_COST
        return PRIMITIVES[self.op].cost + sum(a.cost() for a in self.args)

    def canonical(self) -> str:
        if self.op == "input":
            return "input"
        if self.op == "literal":
            return f"lit:{self.type_.value}:{self.literal_value!r}"
        inner = ",".join(a.canonical() for a in self.args)
        return f"{self.op}({inner})"

    def depth(self) -> int:
        if self.op in ("input", "literal"):
            return 0
        return 1 + max((a.depth() for a in self.args), default=0)


def make_input(type_: Type = Type.GRID) -> Program:
    return Program(op="input", args=(), type_=type_)


def make_literal(value, type_: Type) -> Program:
    return Program(op="literal", args=(), type_=type_, literal_value=value)


def make_call(name: str, args: tuple[Program, ...]) -> Program:
    primitive = PRIMITIVES[name]
    if len(args) != len(primitive.params):
        raise ValueError(f"{name}: expected {len(primitive.params)} args, got {len(args)}")
    for arg, expected in zip(args, primitive.params):
        if arg.type_ != expected:
            raise ValueError(f"{name}: arg type {arg.type_} != expected {expected}")
    return Program(op=name, args=args, type_=primitive.returns)


def evaluate(program: Program, input_grid: Grid):
    if program.op == "input":
        return input_grid
    if program.op == "literal":
        return program.literal_value
    primitive = PRIMITIVES[program.op]
    values = [evaluate(a, input_grid) for a in program.args]
    try:
        return primitive.func(*values)
    except ProgramError:
        raise
    except (ValueError, IndexError, ZeroDivisionError, KeyError, TypeError) as exc:
        raise ProgramError(f"{program.op}: {exc}") from exc
