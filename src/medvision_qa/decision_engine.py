"""Évaluation des critères d'acceptation et agrégation (docs/evaluation_config.md § 3).

Les décisions reposent uniquement sur les bornes des intervalles de confiance. Un
intervalle indéfini ou de largeur nulle mène à INCONCLUSIVE, jamais à SATISFIED.
"""

from dataclasses import dataclass

from medvision_qa.config import Criterion
from medvision_qa.confidence_intervals import ConfidenceInterval

SATISFIED = "SATISFIED"
NOT_SATISFIED = "NOT_SATISFIED"
INCONCLUSIVE = "INCONCLUSIVE"

AGGREGATION_RULE = ("NOT_SATISFIED si au moins un critère est NOT_SATISFIED ; sinon INCONCLUSIVE "
                    "si au moins un critère est INCONCLUSIVE ; SATISFIED seulement si tous les "
                    "critères sont SATISFIED.")


@dataclass(frozen=True)
class CriterionResult:
    criterion: Criterion
    state: str
    reason: str
    quantity: str  # ce qui est comparé, par ex. "macro_f1 (B − A)"
    interval: ConfidenceInterval


@dataclass(frozen=True)
class Decision:
    state: str
    reason: str
    criteria: tuple[CriterionResult, ...]


def _fmt(x: float) -> str:
    return f"{x:.4f}"


def evaluate_criterion(criterion: Criterion, interval: ConfidenceInterval) -> CriterionResult:
    """``interval`` : IC de la métrique (absolute) ou de Δ = B − A (comparaisons)."""
    key = criterion.metric_key
    quantity = f"{key} ({criterion.version})" if criterion.kind == "absolute" else f"{key} (B − A)"

    def result(state, reason):
        return CriterionResult(criterion, state, reason, quantity, interval)

    if not interval.defined:
        return result(INCONCLUSIVE, f"intervalle non calculable : {interval.undefined_reason}")
    if interval.zero_width:
        return result(INCONCLUSIVE, "intervalle de largeur nulle : l'incertitude n'est pas "
                                    "estimable par le bootstrap percentile sur ces données")
    lo, hi = interval.lower, interval.upper
    ci = f"IC [{_fmt(lo)}, {_fmt(hi)}]"

    if criterion.kind == "absolute":
        t = criterion.threshold
        if lo >= t:
            return result(SATISFIED, f"{ci} : borne inférieure ≥ seuil {_fmt(t)}")
        if hi < t:
            return result(NOT_SATISFIED, f"{ci} : borne supérieure < seuil {_fmt(t)}")
        return result(INCONCLUSIVE, f"{ci} contient le seuil {_fmt(t)}")

    if criterion.kind == "non_inferiority":
        m = criterion.margin
        if lo > -m:
            return result(SATISFIED, f"{ci} : borne inférieure > −marge ({_fmt(-m)})")
        if hi < -m:
            return result(NOT_SATISFIED, f"{ci} : borne supérieure < −marge ({_fmt(-m)}) ; B inférieure")
        return result(INCONCLUSIVE, f"{ci} contient −marge ({_fmt(-m)}) ; "
                                    "la non-infériorité n'est ni démontrée ni exclue")

    if criterion.kind == "superiority":
        if lo > 0:
            return result(SATISFIED, f"{ci} : borne inférieure > 0")
        if hi <= 0:
            return result(NOT_SATISFIED, f"{ci} : borne supérieure ≤ 0")
        return result(INCONCLUSIVE, f"{ci} contient 0 ; la supériorité n'est pas démontrée")

    raise ValueError(f"Type de critère inconnu : {criterion.kind!r}")


def aggregate(results: tuple[CriterionResult, ...]) -> Decision:
    if not results:
        raise ValueError("Aucun critère : pas de décision possible.")
    by_state = {s: [r.criterion.id for r in results if r.state == s]
                for s in (SATISFIED, NOT_SATISFIED, INCONCLUSIVE)}
    if by_state[NOT_SATISFIED]:
        return Decision(NOT_SATISFIED, f"critère(s) non satisfait(s) : {by_state[NOT_SATISFIED]}", results)
    if by_state[INCONCLUSIVE]:
        return Decision(INCONCLUSIVE, f"critère(s) inconclusif(s) : {by_state[INCONCLUSIVE]}", results)
    return Decision(SATISFIED, f"les {len(results)} critère(s) sont satisfaits", results)
