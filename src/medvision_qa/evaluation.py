"""Exécution complète d'une évaluation à partir d'un fichier de configuration."""

import platform
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.metadata import version as package_version

from medvision_qa.alignment import AlignedData, align
from medvision_qa.comparison import (DELONG_STATUS, McNemarResult, PairedDifferences, mcnemar,
                                     paired_differences)
from medvision_qa.confidence_intervals import BootstrapResult, bootstrap_metrics
from medvision_qa.config import EvaluationConfig, load_config
from medvision_qa.decision_engine import Decision, aggregate, evaluate_criterion
from medvision_qa.metrics import confusion_matrix
from medvision_qa.validation import GroundTruth, Predictions, load_ground_truth, load_predictions

TRACKED_PACKAGES = ("medvision-qa", "numpy", "scipy", "scikit-learn", "jinja2")


@dataclass(frozen=True)
class RunInfo:
    run_id: str
    started_at_utc: str
    python: str
    packages: dict[str, str]


@dataclass(frozen=True)
class EvaluationResult:
    run: RunInfo
    config: EvaluationConfig
    ground_truth: GroundTruth | None
    predictions: dict[str, Predictions]
    data: AlignedData
    confusion_matrices: dict[str, list[list[int]]]
    per_version: dict[str, BootstrapResult]
    differences: PairedDifferences | None
    mcnemar: McNemarResult | None
    delong_status: str
    decision: Decision


def run_evaluation(config_path) -> EvaluationResult:
    run = RunInfo(
        run_id=str(uuid.uuid4()),
        started_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        python=platform.python_version(),
        packages={name: package_version(name) for name in TRACKED_PACKAGES},
    )
    config = load_config(config_path)
    classes = config.classes
    ground_truth = (load_ground_truth(config.ground_truth_file, classes)
                    if config.ground_truth_file is not None else None)
    predictions = {name: load_predictions(v.predictions_file, classes, config.probability_sum_tolerance)
                   for name, v in config.versions.items()}
    data = align(classes, predictions, ground_truth)

    stats = dict(n_resamples=config.bootstrap_resamples, confidence_level=config.confidence_level,
                 seed=config.seed)
    per_version = {name: bootstrap_metrics(data, name, **stats) for name in config.versions}
    k = len(classes.order)
    matrices = {name: confusion_matrix(data.y_true, data.y_pred[name], k).tolist()
                for name in config.versions}

    differences = mcnemar_result = None
    if "B" in config.versions:
        differences = paired_differences(data, "A", "B", **stats)
        mcnemar_result = mcnemar(data, "A", "B")

    results = []
    for criterion in config.criteria:
        if criterion.kind == "absolute":
            interval = per_version[criterion.version].intervals[criterion.metric_key]
        else:
            interval = differences.intervals[criterion.metric_key]
        results.append(evaluate_criterion(criterion, interval))

    return EvaluationResult(run, config, ground_truth, predictions, data, matrices, per_version,
                            differences, mcnemar_result, DELONG_STATUS, aggregate(tuple(results)))
