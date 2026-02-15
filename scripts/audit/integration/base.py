"""Base integration script with mixin composition.

Provides BaseIntegrationScript that composes all 4 mixins and
implements the standard integration lifecycle:
  load_sources() -> per-sample integrate_sample() -> write_output()

Datasets use this class either directly via from_yaml() or by
subclassing with custom load_sources() / integrate_sample() overrides.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from image_preprocessing_detector.schema_utils.iso_language_script import (
    get_script_family as _get_script_family,
)

from scripts.audit.integration.config import (
    DatasetIntegrationConfig,
    load_config_from_yaml,
)
from scripts.audit.integration.constants import DEFAULT_REGISTRY_DIR
from scripts.audit.integration.loaders import (
    compute_text_statistics,
    load_language_enrichment,
    load_llm_enrichment,
    load_metadata,
    load_resolution_labels,
    load_skew_labels,
    load_vlm_enrichment,
    load_vlm_text_labels,
)
from scripts.audit.integration.mixins.confidence_tracking import (
    ConfidenceTrackingMixin,
)
from scripts.audit.integration.mixins.content_flags import ContentFlagsMixin
from scripts.audit.integration.mixins.ki_mitigation import KIMitigationMixin
from scripts.audit.integration.mixins.reliability_summary import (
    ReliabilitySummaryMixin,
)
from scripts.audit.integration.resolvers import (
    resolve_language,
)

log = logging.getLogger(__name__)


class BaseIntegrationScript(
    KIMitigationMixin,
    ConfidenceTrackingMixin,
    ContentFlagsMixin,
    ReliabilitySummaryMixin,
):
    """Base class for dataset enrichment integration scripts.

    Composes all 4 mixins and implements the standard lifecycle.
    Override hooks allow dataset-specific customization without
    rewriting the entire integration logic.

    Lifecycle:
        1. load_sources() - Load all enrichment data files
        2. integrate_sample() - Per-sample integration (called for each)
        3. run() - Orchestrate integration + stats tracking
        4. write_output() - Write enriched metadata to disk
    """

    def __init__(
        self,
        config: DatasetIntegrationConfig,
        *,
        registry_dir: Path | None = None,
    ) -> None:
        """Initialize with a dataset configuration.

        Args:
            config: Dataset integration configuration.
            registry_dir: Override for the metadata registry root directory.
        """
        self.config = config
        self.registry_dir = registry_dir or DEFAULT_REGISTRY_DIR

        # Source indices populated by load_sources()
        self.metadata: dict[str, Any] = {}
        self.llm_index: dict[str, dict[str, Any]] = {}
        self.lang_index: dict[str, dict[str, Any]] = {}
        self.skew_index: dict[str, dict[str, Any]] | None = None
        self.resolution_index: dict[str, dict[str, Any]] | None = None
        self.vlm_index: dict[str, dict[str, Any]] | None = None
        self.train_gt_index: dict[str, dict[str, Any]] | None = None
        self.text_labels_index: dict[str, dict[str, Any]] | None = None

    @classmethod
    def from_yaml(
        cls,
        yaml_path: Path,
        *,
        registry_dir: Path | None = None,
    ) -> BaseIntegrationScript:
        """Create an integration script from a YAML config file.

        Args:
            yaml_path: Path to the dataset YAML config.
            registry_dir: Override for the metadata registry root.

        Returns:
            Configured BaseIntegrationScript instance.
        """
        config = load_config_from_yaml(yaml_path)
        return cls(config, registry_dir=registry_dir)

    def load_sources(self) -> None:
        """Load all enrichment data sources.

        Loads metadata, LLM enrichment, language enrichment, and any
        optional sources (skew, resolution, VLM, train GT, text labels).
        Override this method for datasets with custom GT loaders.
        """
        cfg = self.config
        rd = self.registry_dir

        self.metadata = load_metadata(cfg.get_metadata_path(rd))
        self.llm_index = load_llm_enrichment(cfg.get_llm_enrichment_path(rd))
        self.lang_index = load_language_enrichment(cfg.get_language_enrichment_path(rd))

        skew_path = cfg.resolve_path(cfg.skew_labels_path, rd)
        if skew_path:
            self.skew_index = load_skew_labels(skew_path)

        res_path = cfg.resolve_path(cfg.resolution_labels_path, rd)
        if res_path:
            self.resolution_index = load_resolution_labels(res_path)

        vlm_path = cfg.resolve_path(cfg.vlm_enrichment_path, rd)
        if vlm_path:
            self.vlm_index = load_vlm_enrichment(vlm_path)

        text_path = cfg.resolve_path(cfg.vlm_text_labels_path, rd)
        if text_path:
            self.text_labels_index = load_vlm_text_labels(text_path)

    def _build_language_sources(
        self,
        sample: dict[str, Any],
        llm: dict[str, Any] | None,
        lang_enrichment: dict[str, Any] | None,
        vlm: dict[str, Any] | None,
        train_gt: dict[str, Any] | None,
    ) -> dict[str, dict[str, Any] | None]:
        """Build source dict for language resolution.

        Args:
            sample: The full sample dict.
            llm: LLM enrichment record.
            lang_enrichment: Language enrichment record.
            vlm: VLM enrichment record.
            train_gt: Train GT record.

        Returns:
            Source dict keyed by source name.
        """
        sources: dict[str, dict[str, Any] | None] = {
            "llm": llm,
            "openlid": lang_enrichment,
            "vlm": vlm,
            "train_gt": train_gt,
        }

        # Extract parser GT from sample's original_labels
        original_labels = sample.get("original_labels", {})
        parser_lang = original_labels.get("language_code")
        if parser_lang and parser_lang != "und":
            sources["parser_gt"] = {
                "language_code": parser_lang,
                "iso15924_script_code": original_labels.get(
                    "iso15924_script_code", "Zyyy"
                ),
            }

        # Documentation fallback
        if self.config.doc_language:
            sources["dataset_doc"] = {
                "iso639_language": self.config.doc_language,
                "iso15924_script": self.config.doc_script or "Zyyy",
            }

        return sources

    def integrate_sample(
        self,
        sample: dict[str, Any],
    ) -> dict[str, Any]:
        """Create integrated enrichment data for a single sample.

        Override this method for datasets that need custom integration
        logic beyond the standard field resolution.

        Args:
            sample: A single sample from the L2 metadata "samples" list.

        Returns:
            New enrichment data dict with all sources merged.
        """
        cfg = self.config
        ki = cfg.ki_config
        vlm_corr = cfg.vlm_corrections

        filename = sample["source"]["original_filename"]
        filename_stem = Path(filename).stem
        filename_full = Path(filename).name

        # Look up enrichment records for this sample
        llm = self.llm_index.get(filename_stem)
        lang_enrichment = self.lang_index.get(filename_stem)
        skew_rec = (self.skew_index or {}).get(filename_full)
        resolution_rec = (self.resolution_index or {}).get(filename_full)
        vlm_rec = (self.vlm_index or {}).get(filename_stem)
        train_gt = (self.train_gt_index or {}).get(filename_stem)
        text_label = (self.text_labels_index or {}).get(filename_stem)

        v1_data: dict[str, Any] = {}
        if sample["enrichments"]["versions"]:
            v1_data = sample["enrichments"]["versions"][-1].get("data", {})

        data: dict[str, Any] = {}
        conf_record = self.create_confidence_record()

        # --- Layout (KI-001) ---
        v1_layout = v1_data.get("layout_detections", [])
        if ki.apply_ki_001_layout_casing:
            if ki.layout_source == "doclayout_yolo":
                standardized = self.apply_ki_001_doclayout_yolo(v1_layout)
            else:
                standardized = self.apply_ki_001_layout_casing(v1_layout)
        else:
            standardized = list(v1_layout)

        data["layout_detections"] = standardized
        data["layout_source"] = f"{ki.layout_source}_gpu"
        data["layout_confidence"] = 0.85
        data["layout_detection_count"] = len(standardized)

        # --- Capture method (KI-005) ---
        if ki.apply_ki_005_capture_override:
            capture, capture_conf, capture_src = self.apply_ki_005_capture_method(
                is_synthetic=cfg.is_synthetic,
                known_capture_method=cfg.known_capture_method,
                llm_capture=llm.get("capture_method") if llm else None,
                llm_confidence=llm.get("capture_confidence", 0.5) if llm else 0.5,
            )
        elif llm:
            capture = llm.get("capture_method", "unknown")
            capture_conf = llm.get("capture_confidence", 0.5)
            capture_src = "llm_vision"
        else:
            capture, capture_conf, capture_src = "unknown", 0.3, "none"

        data["capture_method"] = capture
        data["capture_confidence"] = capture_conf
        data["capture_detection_method"] = capture_src
        self.track_field(
            conf_record, "capture_method", capture, capture_conf, capture_src
        )

        # --- Domain ---
        if llm:
            data["domain_level1"] = llm.get("domain_level1", "UNK")
            data["domain_confidence"] = llm.get("domain_confidence", 0.5)
            data["domain_detection_method"] = "llm_vision"
            data["domain_content_type"] = llm.get("content_type", "")
        else:
            data["domain_level1"] = v1_data.get("domain_level1", "UNK")
            data["domain_confidence"] = v1_data.get("domain_confidence", 0.3)
            data["domain_detection_method"] = v1_data.get(
                "domain_detection_method", "none"
            )
        self.track_field(
            conf_record,
            "domain",
            data["domain_level1"],
            data["domain_confidence"],
            data["domain_detection_method"],
        )

        # --- Language + Script (KI-008, KI-009) ---
        lang_sources = self._build_language_sources(
            sample, llm, lang_enrichment, vlm_rec, train_gt
        )
        lang_resolved, script_resolved = resolve_language(lang_sources)

        data["iso639_language"] = lang_resolved.value
        data["iso15924_script"] = script_resolved.value
        data["language_confidence"] = lang_resolved.confidence
        data["text_scope_detection_method"] = lang_resolved.source

        if ki.apply_ki_008_script_family:
            data["script_family"] = self.apply_ki_008_script_family(
                script_resolved.value, _get_script_family
            )
        else:
            data["script_family"] = _get_script_family(script_resolved.value)

        self.track_field(
            conf_record,
            "language",
            lang_resolved.value,
            lang_resolved.confidence,
            lang_resolved.source,
            lang_resolved.source_rank,
        )

        # --- Content flags (KI-002, KI-003, KI-004, KI-006) ---
        layout_flags = self.derive_content_flags(standardized)
        content_flags = self.apply_vlm_content_flag_overrides(
            filename_stem,
            layout_flags,
            is_synthetic=cfg.is_synthetic,
            vlm_table_tp=(
                vlm_corr.table_true_positives
                if ki.apply_ki_002_table_override
                else None
            ),
            vlm_figure_tp=(
                vlm_corr.figure_true_positives
                if ki.apply_ki_003_figure_override
                else None
            ),
            vlm_formula_tp=(
                vlm_corr.formula_true_positives
                if ki.apply_ki_006_formula_override
                else None
            ),
            vlm_handwriting_tp=(
                vlm_corr.handwriting_true_positives
                if ki.apply_ki_004_handwriting_override
                else None
            ),
        )
        data.update(content_flags.to_dict())
        self.track_field(
            conf_record,
            "content_flags",
            content_flags.to_dict(),
            content_flags.confidence,
            content_flags.source,
        )

        # --- Orientation ---
        if skew_rec:
            data["orientation_class"] = skew_rec.get("orientation_class", 0)
            data["orientation_confidence"] = skew_rec.get("orientation_confidence", 0.9)
            data["orientation_detection_method"] = "mobilenetv4_skew_estimator_v1"
        elif llm and llm.get("orientation") is not None:
            data["orientation_class"] = llm.get("orientation", 0)
            data["orientation_confidence"] = 0.5
            data["orientation_detection_method"] = "llm_vision"
        else:
            data["orientation_class"] = 0
            data["orientation_confidence"] = 0.5
            data["orientation_detection_method"] = "default_upright"

        # --- Skew ---
        if skew_rec:
            data["skew_angle_degrees"] = skew_rec.get("skew_angle_degrees")
            data["skew_confidence"] = skew_rec.get("skew_bin_confidence")
            data["skew_detection_method"] = "mobilenetv4_skew_estimator_v1"

        # --- Split ---
        data["split"] = sample.get("source", {}).get("split", "unknown")

        # --- Content type ---
        if llm:
            data["text_scope_content_type"] = llm.get("content_type", "") or "unknown"
        else:
            data["text_scope_content_type"] = v1_data.get(
                "text_scope_content_type", "unknown"
            )

        data["text_scope"] = v1_data.get("text_scope", "printed")
        data["image_properties_color_mode"] = v1_data.get(
            "image_properties_color_mode", "color"
        )

        # --- Resolution quality ---
        if resolution_rec:
            data["resolution_quality_score"] = resolution_rec.get("quality_score")
            data["resolution_quality_bucket"] = resolution_rec.get("bucket")
            data["resolution_char_height_px"] = resolution_rec.get(
                "median_char_height_px"
            )
            data["resolution_detection_method"] = resolution_rec.get(
                "method", "paddleocr_cc_v1"
            )
        else:
            for field_name in (
                "resolution_category",
                "resolution_pixels",
                "resolution_quality_score",
                "resolution_quality_bucket",
                "resolution_char_height_px",
            ):
                if field_name in v1_data:
                    data[field_name] = v1_data[field_name]

        # --- Text content ---
        if text_label and text_label.get("transcription"):
            transcription = text_label["transcription"]
            data["text_has_content"] = True
            data["text_content"] = transcription
            data["text_content_confidence"] = text_label.get("confidence", 0.8)
            data["text_content_source"] = "vlm_manual_transcription"
            data["text_statistics"] = compute_text_statistics(transcription)
        else:
            data["text_has_content"] = False
            data["text_content"] = ""
            data["text_content_confidence"] = 0.0
            data["text_content_source"] = "none"
            data["text_statistics"] = compute_text_statistics("")

        # --- Metadata ---
        data["dataset_short_code"] = cfg.dataset_name
        data["sample_reliability_summary"] = self.compute_reliability_summary(data)
        data["field_confidence_provenance"] = self.get_confidence_summary(conf_record)

        return data

    def _init_stats(self) -> dict[str, Any]:
        """Create an empty statistics dict."""
        return {
            "total": 0,
            "integrated": 0,
            "llm_matched": 0,
            "lang_matched": 0,
            "vlm_matched": 0,
            "train_gt_matched": 0,
            "skew_matched": 0,
            "resolution_matched": 0,
            "text_labels_matched": 0,
            "has_text_content_count": 0,
            "domain_dist": Counter(),
            "split_dist": Counter(),
            "lang_dist": Counter(),
            "script_family_dist": Counter(),
            "lang_method_dist": Counter(),
            "capture_method_dist": Counter(),
            "content_type_dist": Counter(),
            "has_table_count": 0,
            "has_formula_count": 0,
            "has_handwriting_count": 0,
            "has_figure_count": 0,
        }

    def _track_stats(
        self,
        stats: dict[str, Any],
        filename_stem: str,
        filename_full: str,
        integrated_data: dict[str, Any],
    ) -> None:
        """Update statistics counters for a processed sample."""
        # Source match tracking
        if filename_stem in self.llm_index:
            stats["llm_matched"] += 1
        if filename_stem in self.lang_index:
            stats["lang_matched"] += 1
        if self.vlm_index and filename_stem in self.vlm_index:
            stats["vlm_matched"] += 1
        if self.train_gt_index and filename_stem in self.train_gt_index:
            stats["train_gt_matched"] += 1
        if self.skew_index and filename_full in self.skew_index:
            stats["skew_matched"] += 1
        if self.resolution_index and filename_full in self.resolution_index:
            stats["resolution_matched"] += 1
        if self.text_labels_index and filename_stem in self.text_labels_index:
            stats["text_labels_matched"] += 1

        # Distribution tracking
        dist_fields = [
            ("domain_dist", "domain_level1", "UNK"),
            ("split_dist", "split", "unknown"),
            ("lang_dist", "iso639_language", "und"),
            ("script_family_dist", "script_family", "unknown"),
            ("lang_method_dist", "text_scope_detection_method", "unknown"),
            ("capture_method_dist", "capture_method", "unknown"),
            ("content_type_dist", "text_scope_content_type", "unknown"),
        ]
        for counter_key, data_key, default in dist_fields:
            stats[counter_key][integrated_data.get(data_key, default)] += 1

        if integrated_data.get("text_has_content"):
            stats["has_text_content_count"] += 1

        for stat_key, data_key in [
            ("has_table_count", "has_table"),
            ("has_formula_count", "has_formula"),
            ("has_handwriting_count", "has_handwriting"),
            ("has_figure_count", "has_figure"),
        ]:
            if integrated_data.get(data_key):
                stats[stat_key] += 1

    def _write_enrichment_version(
        self,
        sample: dict[str, Any],
        integrated_data: dict[str, Any],
        now: str,
    ) -> None:
        """Write (or replace) an enrichment version into sample."""
        cfg = self.config
        new_version = {
            "version": cfg.enrichment_version_number,
            "created_at": now,
            "created_by": f"integration_framework/{cfg.dataset_name}",
            "method": "tier_2_model",
            "description": (
                f"Integrated enrichment {cfg.enrichment_version_tag}: "
                "LLM vision + layout + language enrichment + "
                "dataset documentation (via BaseIntegrationScript)"
            ),
            "script_version": cfg.script_version,
            "data": integrated_data,
        }
        versions = sample["enrichments"]["versions"]
        for i, ver in enumerate(versions):
            if ver.get("version") == cfg.enrichment_version_number:
                versions[i] = new_version
                sample["enrichments"]["current_version"] = cfg.enrichment_version_number
                return
        versions.append(new_version)
        sample["enrichments"]["current_version"] = cfg.enrichment_version_number

    def run(self, *, dry_run: bool = False) -> dict[str, Any]:
        """Run integration for all samples.

        Args:
            dry_run: If True, compute stats without modifying metadata.

        Returns:
            Stats dict with counts and distribution Counters.
        """
        stats = self._init_stats()
        now = datetime.now(UTC).isoformat()

        for sample in self.metadata["samples"]:
            stats["total"] += 1
            filename = sample["source"]["original_filename"]
            filename_stem = Path(filename).stem
            filename_full = Path(filename).name

            integrated_data = self.integrate_sample(sample)
            stats["integrated"] += 1

            self._track_stats(stats, filename_stem, filename_full, integrated_data)

            if not dry_run:
                self._write_enrichment_version(sample, integrated_data, now)

        return stats

    def write_output(self, output_path: Path) -> None:
        """Write enriched metadata to disk.

        Args:
            output_path: Path to write the output JSON.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        log.info("Writing output to %s", output_path)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        log.info("Done. Written %d samples.", len(self.metadata["samples"]))

    def print_summary(self, stats: dict[str, Any]) -> None:
        """Print integration summary with distributions.

        Args:
            stats: Stats dict returned by run().
        """
        total = max(stats["total"], 1)
        name = self.config.dataset_name

        print(f"\n{'=' * 60}")
        print(f"{name} Enrichment Integration Summary")
        print(f"{'=' * 60}")
        print(f"Total samples:        {stats['total']}")
        print(f"Integrated:           {stats['integrated']}")
        print(f"LLM matched:          {stats['llm_matched']}")
        print(f"Language matched:     {stats['lang_matched']}")
        print(f"VLM matched:          {stats.get('vlm_matched', 0)}")
        print(f"Train GT matched:     {stats.get('train_gt_matched', 0)}")
        print(f"Skew matched:         {stats.get('skew_matched', 0)}")
        print(f"Resolution matched:   {stats.get('resolution_matched', 0)}")
        print(f"Text labels matched:  {stats.get('text_labels_matched', 0)}")
        print(f"Has text content:     {stats.get('has_text_content_count', 0)}")
        print()

        for label, key, limit in [
            ("Domain distribution:", "domain_dist", None),
            ("Split distribution:", "split_dist", None),
            ("Language distribution (top 15):", "lang_dist", 15),
            ("Script family distribution:", "script_family_dist", None),
            ("Language method distribution:", "lang_method_dist", None),
            ("Capture method distribution:", "capture_method_dist", None),
            ("Content type (top 10):", "content_type_dist", 10),
        ]:
            print(label)
            items = stats[key].most_common(limit)
            for value, count in items:
                pct = count / total * 100
                print(f"  {value:30s}: {count:5d} ({pct:.1f}%)")
            print()

        print("Content flags:")
        print(f"  has_table:          {stats['has_table_count']}")
        print(f"  has_formula:        {stats['has_formula_count']}")
        print(f"  has_handwriting:    {stats['has_handwriting_count']}")
        print(f"  has_figure:         {stats['has_figure_count']}")
        print(f"{'=' * 60}")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for config-driven integration.

    Args:
        argv: Command-line arguments (defaults to sys.argv).

    Returns:
        Exit code (0 = success, 1 = error).
    """
    parser = argparse.ArgumentParser(
        description="Run dataset enrichment integration from YAML config.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "config",
        type=Path,
        help="Path to dataset integration YAML config",
    )
    parser.add_argument(
        "--registry-dir",
        type=Path,
        default=DEFAULT_REGISTRY_DIR,
        help="Metadata registry root directory (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: overwrite input metadata file)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report only, do not write output",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    script = BaseIntegrationScript.from_yaml(
        args.config, registry_dir=args.registry_dir
    )
    script.load_sources()

    start = time.monotonic()
    stats = script.run(dry_run=args.dry_run)
    elapsed = time.monotonic() - start

    script.print_summary(stats)
    log.info("Integration completed in %.2f seconds", elapsed)

    if args.dry_run:
        log.info("Dry run - no output written")
    else:
        output_path = args.output or script.config.get_metadata_path(args.registry_dir)
        script.write_output(output_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
