"""Inter-Annotator Agreement (IAA) gold standard framework.

Calibrates VLM reliability by measuring multi-model agreement on a
stratified sample of images.  Computes Cohen's kappa (categorical fields)
and Spearman's rank correlation (continuous fields) across model pairs.

Phases:
  1. ``select``: Pick stratified images, write ``iaa_sample_set.json``
  2. ``label``: (Semi-auto) Score images with each model
  3. ``compute``: Calculate IAA metrics
  4. ``report``: Generate reliability breakdown

Usage::

    python scripts/audit/iaa_gold_standard.py --phase select --config config/iaa_gold_standard.yaml
    python scripts/audit/iaa_gold_standard.py --phase compute --results-dir results/iaa/
"""

from __future__ import annotations

import json
import logging
import math
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "iaa_gold_standard.yaml"
AUDIT_RESULTS_DIR = PROJECT_ROOT / "scripts" / "audit" / "results"
IAA_DIR = AUDIT_RESULTS_DIR / "iaa"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class IAAConfig:
    """Configuration for IAA gold standard evaluation.

    Attributes:
        datasets: Target datasets to sample from.
        samples_per_dataset: Number of images per dataset.
        categorical_fields: Fields evaluated with Cohen's kappa.
        continuous_fields: Fields evaluated with SRCC.
        models: Model identifiers for multi-model comparison.
    """

    datasets: list[str]
    samples_per_dataset: int
    categorical_fields: list[str]
    continuous_fields: list[str]
    models: list[str]


@dataclass(frozen=True)
class SampleImage:
    """A single image selected for IAA evaluation.

    Attributes:
        dataset: Source dataset name.
        image_id: Image identifier within the dataset.
        image_path: Relative path to the image file.
    """

    dataset: str
    image_id: str
    image_path: str


@dataclass
class FieldAgreement:
    """Agreement metrics for a single field.

    Attributes:
        field_name: Name of the evaluated field.
        metric_type: "kappa" for categorical, "srcc" for continuous.
        value: Computed metric value.
        n_samples: Number of valid sample pairs.
        model_pair: Which models were compared.
    """

    field_name: str
    metric_type: str
    value: float
    n_samples: int
    model_pair: tuple[str, str]

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "field_name": self.field_name,
            "metric_type": self.metric_type,
            "value": self.value,
            "n_samples": self.n_samples,
            "model_pair": list(self.model_pair),
        }


@dataclass
class IAAReport:
    """Full IAA evaluation report.

    Attributes:
        total_samples: Total images evaluated.
        total_fields: Number of fields evaluated.
        agreements: Per-field agreement metrics.
        overall_kappa: Mean kappa across categorical fields.
        overall_srcc: Mean SRCC across continuous fields.
    """

    total_samples: int = 0
    total_fields: int = 0
    agreements: list[FieldAgreement] = field(default_factory=list)
    overall_kappa: float | None = None
    overall_srcc: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "total_samples": self.total_samples,
            "total_fields": self.total_fields,
            "overall_kappa": self.overall_kappa,
            "overall_srcc": self.overall_srcc,
            "agreements": [a.to_dict() for a in self.agreements],
        }


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------
def load_iaa_config(
    config_path: Path | None = None,
) -> IAAConfig:
    """Load IAA gold standard configuration.

    Args:
        config_path: Override config file path.

    Returns:
        Parsed IAAConfig.

    Raises:
        FileNotFoundError: If config file does not exist.
    """
    path = config_path or CONFIG_PATH
    if not path.exists():
        msg = f"IAA config not found: {path}"
        raise FileNotFoundError(msg)

    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return IAAConfig(
        datasets=data.get("datasets", []),
        samples_per_dataset=data.get("samples_per_dataset", 10),
        categorical_fields=data.get("categorical_fields", []),
        continuous_fields=data.get("continuous_fields", []),
        models=data.get("models", []),
    )


# ---------------------------------------------------------------------------
# Phase 1: Sample selection
# ---------------------------------------------------------------------------
def select_samples(
    config: IAAConfig,
    *,
    metadata_root: Path | None = None,
) -> list[SampleImage]:
    """Select stratified sample images for IAA evaluation.

    For each configured dataset, picks ``samples_per_dataset`` images.
    In production, this reads metadata files and applies stratified
    sampling.  This implementation provides the framework and returns
    placeholder samples when metadata is unavailable.

    Args:
        config: IAA configuration.
        metadata_root: Override metadata registry root.

    Returns:
        List of SampleImage objects.
    """
    samples: list[SampleImage] = []

    for dataset in config.datasets:
        # In production, load metadata and apply stratified sampling
        # For now, generate placeholder sample IDs
        for i in range(config.samples_per_dataset):
            samples.append(
                SampleImage(
                    dataset=dataset,
                    image_id=f"{dataset}_sample_{i:04d}",
                    image_path=f"{dataset}/{dataset}_sample_{i:04d}.jpg",
                )
            )

    log.info(
        "Selected %d samples across %d datasets",
        len(samples),
        len(config.datasets),
    )
    return samples


def write_sample_set(
    samples: list[SampleImage],
    *,
    output_dir: Path | None = None,
) -> Path:
    """Write sample set to JSON.

    Args:
        samples: List of selected samples.
        output_dir: Override output directory.

    Returns:
        Path to the written file.
    """
    out_dir = output_dir or IAA_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "iaa_sample_set.json"

    data = {
        "total_samples": len(samples),
        "samples": [asdict(s) for s in samples],
    }

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    log.info("Wrote %d samples to %s", len(samples), path)
    return path


# ---------------------------------------------------------------------------
# Phase 3: IAA computation
# ---------------------------------------------------------------------------
def compute_cohens_kappa(
    labels_a: list[str],
    labels_b: list[str],
) -> float:
    """Compute Cohen's kappa for two sets of categorical labels.

    Args:
        labels_a: Labels from annotator/model A.
        labels_b: Labels from annotator/model B.

    Returns:
        Cohen's kappa coefficient (-1 to 1).

    Raises:
        ValueError: If label lists have different lengths.
    """
    if len(labels_a) != len(labels_b):
        msg = f"Label lists must have same length: {len(labels_a)} vs {len(labels_b)}"
        raise ValueError(msg)

    n = len(labels_a)
    if n == 0:
        return 0.0

    # Observed agreement
    agree = sum(1 for a, b in zip(labels_a, labels_b) if a == b)
    p_o = agree / n

    # Expected agreement
    all_labels = set(labels_a) | set(labels_b)
    count_a = Counter(labels_a)
    count_b = Counter(labels_b)
    p_e = sum(
        (count_a.get(label, 0) / n) * (count_b.get(label, 0) / n)
        for label in all_labels
    )

    if abs(p_e - 1.0) < 1e-10:
        return 1.0 if p_o == 1.0 else 0.0

    return (p_o - p_e) / (1.0 - p_e)


def compute_srcc(
    values_a: list[float],
    values_b: list[float],
) -> float:
    """Compute Spearman's rank correlation coefficient.

    Args:
        values_a: Values from annotator/model A.
        values_b: Values from annotator/model B.

    Returns:
        SRCC (-1 to 1).

    Raises:
        ValueError: If value lists have different lengths.
    """
    if len(values_a) != len(values_b):
        msg = f"Value lists must have same length: {len(values_a)} vs {len(values_b)}"
        raise ValueError(msg)

    n = len(values_a)
    if n < 2:
        return 0.0

    def _rank(values: list[float]) -> list[float]:
        """Assign ranks with average tie-breaking."""
        indexed = sorted(enumerate(values), key=lambda x: x[1])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and indexed[j + 1][1] == indexed[j][1]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                ranks[indexed[k][0]] = avg_rank
            i = j + 1
        return ranks

    ranks_a = _rank(values_a)
    ranks_b = _rank(values_b)

    # Pearson correlation on ranks
    mean_a = sum(ranks_a) / n
    mean_b = sum(ranks_b) / n

    cov = sum((ra - mean_a) * (rb - mean_b) for ra, rb in zip(ranks_a, ranks_b))
    std_a = math.sqrt(sum((ra - mean_a) ** 2 for ra in ranks_a))
    std_b = math.sqrt(sum((rb - mean_b) ** 2 for rb in ranks_b))

    if std_a < 1e-10 or std_b < 1e-10:
        return 0.0

    return cov / (std_a * std_b)


def compute_pairwise_agreement(
    labels_a: list[str],
    labels_b: list[str],
) -> float:
    """Compute simple percent agreement.

    Args:
        labels_a: Labels from annotator/model A.
        labels_b: Labels from annotator/model B.

    Returns:
        Percent agreement (0-100).
    """
    if not labels_a:
        return 0.0
    agree = sum(1 for a, b in zip(labels_a, labels_b) if a == b)
    return 100.0 * agree / len(labels_a)


# ---------------------------------------------------------------------------
# Phase 3: Full IAA computation from label files
# ---------------------------------------------------------------------------
def compute_iaa_from_labels(
    label_files: dict[str, Path],
    config: IAAConfig,
) -> IAAReport:
    """Compute IAA metrics from model label files.

    Args:
        label_files: Dict mapping model name to label file path.
        config: IAA configuration.

    Returns:
        IAAReport with all agreement metrics.
    """
    # Load all label data
    model_labels: dict[str, dict[str, dict[str, Any]]] = {}
    for model, path in label_files.items():
        if not path.exists():
            log.warning("Label file not found for %s: %s", model, path)
            continue
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        # Expected format: {"labels": {"image_id": {"field": value, ...}}}
        model_labels[model] = data.get("labels", {})

    models = list(model_labels.keys())
    if len(models) < 2:
        log.warning("Need at least 2 models for IAA, got %d", len(models))
        return IAAReport()

    report = IAAReport()
    report.total_fields = len(config.categorical_fields) + len(config.continuous_fields)

    # Compute pairwise metrics
    kappa_values: list[float] = []
    srcc_values: list[float] = []

    for i in range(len(models)):
        for j in range(i + 1, len(models)):
            model_a, model_b = models[i], models[j]
            labels_a = model_labels[model_a]
            labels_b = model_labels[model_b]

            # Find common image IDs
            common_ids = sorted(set(labels_a.keys()) & set(labels_b.keys()))
            report.total_samples = max(report.total_samples, len(common_ids))

            # Categorical fields
            for field_name in config.categorical_fields:
                vals_a = [
                    str(labels_a[img_id].get(field_name, ""))
                    for img_id in common_ids
                    if field_name in labels_a.get(img_id, {})
                    and field_name in labels_b.get(img_id, {})
                ]
                vals_b = [
                    str(labels_b[img_id].get(field_name, ""))
                    for img_id in common_ids
                    if field_name in labels_a.get(img_id, {})
                    and field_name in labels_b.get(img_id, {})
                ]
                if vals_a:
                    kappa = compute_cohens_kappa(vals_a, vals_b)
                    kappa_values.append(kappa)
                    report.agreements.append(
                        FieldAgreement(
                            field_name=field_name,
                            metric_type="kappa",
                            value=kappa,
                            n_samples=len(vals_a),
                            model_pair=(model_a, model_b),
                        )
                    )

            # Continuous fields
            for field_name in config.continuous_fields:
                vals_a_f = [
                    float(labels_a[img_id][field_name])
                    for img_id in common_ids
                    if field_name in labels_a.get(img_id, {})
                    and field_name in labels_b.get(img_id, {})
                ]
                vals_b_f = [
                    float(labels_b[img_id][field_name])
                    for img_id in common_ids
                    if field_name in labels_a.get(img_id, {})
                    and field_name in labels_b.get(img_id, {})
                ]
                if len(vals_a_f) >= 2:
                    srcc = compute_srcc(vals_a_f, vals_b_f)
                    srcc_values.append(srcc)
                    report.agreements.append(
                        FieldAgreement(
                            field_name=field_name,
                            metric_type="srcc",
                            value=srcc,
                            n_samples=len(vals_a_f),
                            model_pair=(model_a, model_b),
                        )
                    )

    if kappa_values:
        report.overall_kappa = sum(kappa_values) / len(kappa_values)
    if srcc_values:
        report.overall_srcc = sum(srcc_values) / len(srcc_values)

    return report


# ---------------------------------------------------------------------------
# Phase 4: Report writing
# ---------------------------------------------------------------------------
def write_iaa_report(
    report: IAAReport,
    *,
    output_dir: Path | None = None,
) -> Path:
    """Write IAA report to JSON.

    Args:
        report: IAA evaluation report.
        output_dir: Override output directory.

    Returns:
        Path to the written file.
    """
    out_dir = output_dir or IAA_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "iaa_results.json"

    with path.open("w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

    log.info("Wrote IAA report to %s", path)
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="IAA gold standard framework.")
    parser.add_argument(
        "--phase",
        choices=["select", "compute", "report"],
        required=True,
        help="Which phase to run.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Config file path.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=None,
        help="Results directory.",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    config = load_iaa_config(args.config)

    if args.phase == "select":
        samples = select_samples(config)
        path = write_sample_set(samples, output_dir=args.results_dir)
        print(f"Selected {len(samples)} samples -> {path}")

    elif args.phase == "compute":
        results_dir = args.results_dir or IAA_DIR
        label_files = {
            model: results_dir / f"iaa_labels_{model}.json" for model in config.models
        }
        report = compute_iaa_from_labels(label_files, config)
        path = write_iaa_report(report, output_dir=args.results_dir)
        print(f"IAA report -> {path}")
        if report.overall_kappa is not None:
            print(f"  Mean kappa: {report.overall_kappa:.3f}")
        if report.overall_srcc is not None:
            print(f"  Mean SRCC: {report.overall_srcc:.3f}")


if __name__ == "__main__":
    main()
