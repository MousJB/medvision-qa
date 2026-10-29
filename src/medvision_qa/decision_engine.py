"""Evaluation of the acceptance criteria and aggregation (docs/evaluation_config.md § 3).

Decisions rest only on the bounds of the confidence intervals. An undefined or
zero-width interval leads to INCONCLUSIVE, never to SATISFIED.
"""

from dataclasses import dataclass

from medvision_qa.config import Criterion
from medvision_qa.confidence_intervals import ConfidenceInterval
from medvision_qa.i18n import Text, msg

SATISFIED = "SATISFIED"
NOT_SATISFIED = "NOT_SATISFIED"
INCONCLUSIVE = "INCONCLUSIVE"

AGGREGATION_RULE = msg("dec.aggregation_rule")


@dataclass(frozen=True)
class CriterionResult:
    criterion: Criterion
    state: str
    reason: Text
    quantity: str  # what is compared, e.g. "macro_f1 (B − A)"
    interval: ConfidenceInterval


@dataclass(frozen=True)
class Decision:
    state: str
    reason: Text
    criteria: tuple[CriterionResult, ...]


def _fmt(x: float) -> str:
    return f"{x:.4f}"


def evaluate_criterion(criterion: Criterion, interval: ConfidenceInterval) -> CriterionResult:
    """``interval``: CI of the metric (absolute) or of Δ = B − A (comparisons)."""
    key = criterion.metric_key
    quantity = f"{key} ({criterion.version})" if criterion.kind == "absolute" else f"{key} (B − A)"

    def result(state, reason):
        return CriterionResult(criterion, state, reason, quantity, interval)

    if not interval.defined:
        return result(INCONCLUSIVE, msg("dec.interval_undefined", reason=interval.undefined_reason))
    if interval.zero_width:
        return result(INCONCLUSIVE, msg("dec.zero_width"))
    lo, hi = interval.lower, interval.upper
    ci = msg("dec.ci", lower=_fmt(lo), upper=_fmt(hi))

    if criterion.kind == "absolute":
        t = _fmt(criterion.threshold)
        if lo >= criterion.threshold:
            return result(SATISFIED, msg("dec.abs_satisfied", ci=ci, t=t))
        if hi < criterion.threshold:
            return result(NOT_SATISFIED, msg("dec.abs_not", ci=ci, t=t))
        return result(INCONCLUSIVE, msg("dec.abs_inconclusive", ci=ci, t=t))

    if criterion.kind == "non_inferiority":
        m = -criterion.margin
        if lo > m:
            return result(SATISFIED, msg("dec.ni_satisfied", ci=ci, m=_fmt(m)))
        if hi < m:
            return result(NOT_SATISFIED, msg("dec.ni_not", ci=ci, m=_fmt(m)))
        return result(INCONCLUSIVE, msg("dec.ni_inconclusive", ci=ci, m=_fmt(m)))

    if criterion.kind == "superiority":
        if lo > 0:
            return result(SATISFIED, msg("dec.sup_satisfied", ci=ci))
        if hi <= 0:
            return result(NOT_SATISFIED, msg("dec.sup_not", ci=ci))
        return result(INCONCLUSIVE, msg("dec.sup_inconclusive", ci=ci))

    raise ValueError(f"Unknown criterion type: {criterion.kind!r}")


def aggregate(results: tuple[CriterionResult, ...]) -> Decision:
    if not results:
        raise ValueError("No criterion: no decision is possible.")
    by_state = {s: [r.criterion.id for r in results if r.state == s]
                for s in (SATISFIED, NOT_SATISFIED, INCONCLUSIVE)}
    if by_state[NOT_SATISFIED]:
        return Decision(NOT_SATISFIED, msg("dec.not_satisfied", ids=str(by_state[NOT_SATISFIED])), results)
    if by_state[INCONCLUSIVE]:
        return Decision(INCONCLUSIVE, msg("dec.inconclusive", ids=str(by_state[INCONCLUSIVE])), results)
    return Decision(SATISFIED, msg("dec.satisfied", n=len(results)), results)
