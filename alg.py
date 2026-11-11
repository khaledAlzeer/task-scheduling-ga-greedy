"""Algorithm core: binary GA + earliest-finish Greedy repair (independent of UI)."""
from __future__ import annotations
from dataclasses import dataclass
import math
import random
import time
from typing import Sequence


@dataclass(frozen=True)
class Task:
    task_id: str
    start: float
    finish: float


@dataclass
class GAResult:
    selected: list[Task]
    rejected: list[Task]
    chromosome: list[int]
    fitness: int
    exact_greedy_count: int
    gap: int
    generations: int
    evaluations: int
    elapsed_seconds: float
    history: list[int]
    stop_reason: str
    seed: int


def validate_tasks(tasks: Sequence[Task]) -> list[Task]:
    """Reject bad intervals before optimization; never infer missing time values."""
    items = list(tasks)
    seen: set[str] = set()
    for i, task in enumerate(items, 1):
        if not isinstance(task, Task):
            raise ValueError(f"Row {i}: expected Task(task_id, start, finish).")
        if not task.task_id or not str(task.task_id).strip():
            raise ValueError(f"Row {i}: missing task identifier.")
        if task.task_id in seen:
            raise ValueError(f"Row {i}: duplicate ID {task.task_id!r}.")
        seen.add(task.task_id)
        if not isinstance(task.start, (int, float)) or not isinstance(task.finish, (int, float)):
            raise ValueError(f"Row {i}: start and finish must be numeric.")
        if not math.isfinite(task.start) or not math.isfinite(task.finish):
            raise ValueError(f"Row {i}: times must be finite.")
        if not task.start < task.finish:
            raise ValueError(f"Row {i}: finish must be greater than start.")
    return items


def finish_order(tasks: Sequence[Task]) -> list[int]:
    return sorted(range(len(tasks)), key=lambda i: (tasks[i].finish, tasks[i].start, tasks[i].task_id))


def exact_greedy(tasks: Sequence[Task], order: Sequence[int] | None = None) -> list[int]:
    """Optimal maximum-cardinality schedule for unweighted one-resource intervals."""
    if order is None:
        order = finish_order(tasks)
    indices: list[int] = []
    last_finish = -math.inf
    for i in order:
        if tasks[i].start >= last_finish:
            indices.append(i)
            last_finish = tasks[i].finish
    return indices


def repair(bits: Sequence[int], tasks: Sequence[Task], order: Sequence[int]) -> list[int]:
    """Deterministic repair: keep non-overlapping proposed jobs in finish-time order."""
    if len(bits) != len(tasks):
        raise ValueError("Chromosome length does not match number of tasks.")
    repaired = [0] * len(tasks)
    last_finish = -math.inf
    for i in order:
        if bits[i] == 1 and tasks[i].start >= last_finish:
            repaired[i] = 1
            last_finish = tasks[i].finish
    return repaired


def is_feasible(bits: Sequence[int], tasks: Sequence[Task]) -> bool:
    if len(bits) != len(tasks) or any(v not in (0, 1) for v in bits):
        return False
    last_finish = -math.inf
    for i in finish_order(tasks):
        if bits[i]:
            if tasks[i].start < last_finish:
                return False
            last_finish = tasks[i].finish
    return True


def run_genetic_algorithm(
    tasks: Sequence[Task], *, population_size: int = 30, max_generations: int = 100,
    crossover_rate: float = 0.80, mutation_rate: float = 0.05,
    initial_probability: float = 0.50, tournament_size: int = 3,
    elite_count: int = 1, seed: int = 42,
) -> GAResult:
    """Evolve feasible job subsets; exact Greedy only checks the known optimum/early stop.

    The full optimum is NOT inserted into the GA population. Phase-2 specification
    is followed: Bernoulli initialization, tournament, 1-point crossover, mutation,
    repair, elitism, and early stop upon reaching the exact unweighted optimum.
    """
    start_clock = time.perf_counter()
    tasks = validate_tasks(tasks)
    if population_size < 2 or max_generations < 0 or not 1 <= tournament_size <= population_size:
        raise ValueError("Use population >= 2, generations >= 0, and 1 <= tournament_size <= population.")
    if not 1 <= elite_count < population_size:
        raise ValueError("elite_count must be at least 1 and less than population size.")
    for name, value in [("crossover_rate", crossover_rate), ("mutation_rate", mutation_rate), ("initial_probability", initial_probability)]:
        if not 0 <= value <= 1:
            raise ValueError(f"{name} must be in [0, 1].")
    if not isinstance(seed, int):
        raise ValueError("seed must be an integer.")

    rng = random.Random(seed)
    n = len(tasks)
    order = finish_order(tasks)
    optimum = len(exact_greedy(tasks, order))
    evaluations = 0
    if n == 0:
        return GAResult([], [], [], 0, 0, 0, 0, 0, time.perf_counter() - start_clock, [0], "empty input", seed)

    # Store (repaired chromosome, score) so all stored solutions remain feasible.
    population: list[tuple[list[int], int]] = []
    for _ in range(population_size):
        raw = [int(rng.random() < initial_probability) for _ in range(n)]
        fixed = repair(raw, tasks, order)
        population.append((fixed, sum(fixed)))
        evaluations += 1

    def best_of(group: Sequence[tuple[list[int], int]]) -> tuple[list[int], int]:
        # Deterministic tie-break (prefer lexicographically smaller bit-string).
        return min(group, key=lambda item: (-item[1], tuple(item[0])))

    best_bits, best_fitness = best_of(population)
    best_bits = best_bits.copy()
    history = [best_fitness]
    generations = 0

    def tournament() -> list[int]:
        chosen = rng.sample(range(population_size), tournament_size)
        winner = min(chosen, key=lambda idx: (-population[idx][1], tuple(population[idx][0]), idx))
        return population[winner][0]

    while generations < max_generations and best_fitness < optimum:
        children: list[tuple[list[int], int]] = []
        while len(children) < population_size:
            a, b = tournament(), tournament()
            left, right = a.copy(), b.copy()
            if n >= 2 and rng.random() < crossover_rate:
                cut = rng.randrange(1, n)
                left = a[:cut] + b[cut:]
                right = b[:cut] + a[cut:]
            for child in (left, right):
                for j in range(n):
                    if rng.random() < mutation_rate:
                        child[j] ^= 1
                fixed = repair(child, tasks, order)
                children.append((fixed, sum(fixed)))
                evaluations += 1
                if len(children) == population_size:
                    break
        # Insert elite from previous best, replacing worst offspring deterministically.
        worst = min(range(population_size), key=lambda i: (children[i][1], tuple(children[i][0]), i))
        children[worst] = (best_bits.copy(), best_fitness)
        population = children
        cand_bits, cand_fit = best_of(population)
        if cand_fit > best_fitness or (cand_fit == best_fitness and tuple(cand_bits) < tuple(best_bits)):
            best_bits, best_fitness = cand_bits.copy(), cand_fit
        generations += 1
        history.append(best_fitness)

    selected = [tasks[i] for i in order if best_bits[i]]
    rejected = [task for i, task in enumerate(tasks) if not best_bits[i]]
    assert is_feasible(best_bits, tasks)
    assert best_fitness == len(selected)
    reason = "exact optimum reached" if best_fitness == optimum else "generation limit reached"
    return GAResult(selected, rejected, best_bits, best_fitness, optimum,
                    optimum - best_fitness, generations, evaluations,
                    time.perf_counter() - start_clock, history, reason, seed)
