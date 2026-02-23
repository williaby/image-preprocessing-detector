# Head Adequacy Review (HAR) Master Index

> **Status**: 🔄 In Progress
> **Version**: 1.0
> **Created**: 2026-02-22
> **Updated**: 2026-02-24
> **Branch**: `docs/har-systematic-head-review`
>
> Systematic per-head dataset audit for all 22 training heads.
> Each HAR evaluates whether source datasets, assembled training datasets, and OOD holdouts are
> adequately designed for a specific model head's task.
>
> **Scoring**: Source Pool Adequacy (35%) + 14-Dimension Coverage (25%) +
> Wild Condition Coverage (20%) + OOD Design Quality (20%)
>
> **Grades**: ✅ Ready (≥75, no P0 blockers) | ⚠️ Needs Work (50–74 or P0 ≤5 days) |
> ❌ Blocked (<50 or unresolvable P0)

---

## Methodology

A **Head Adequacy Review (HAR)** is a 9-section per-head audit that ties together:

1. Whether the source dataset pool has the required L2 label fields populated at ≥0.7 confidence
2. Whether the assembled training dataset is shaped correctly for this head's task
3. Whether the 14 diversity dimensions are satisfied in the training data
4. Whether the OOD holdout covers this head's realistic failure modes
5. Whether existing L2 metadata defects (from dataset audits) block training for this head

**Key distinction from DDR audits**: DDRs audit *datasets*; HARs audit *heads*. A HAR consumes
the DDR outputs (field coverage stats, defect catalogs, KI codes) as inputs to its Section 2
source pool analysis.

**L2 field dependency**: Each head's training labels derive from specific L2 schema fields. If a
source dataset lacks the required L2 field at the required confidence, the training pool is
insufficient regardless of image count.

---

## Schema-to-Head Label Mapping

| Head ID | Head Name | Primary L2 Field | Schema Section |
| --- | --- | --- | --- |
| MNV4-H1 | orientation | `geometric.orientation_class` (0/90/180/270) | GeometricInfo |
| MNV4-H2 | skew_reg | `geometric.skew_angle_degrees` (float ±180°) | GeometricInfo |
| MNV4-H3 | resolution_quality | `resolution.resolution_quality_score` (0-1) | ResolutionInfo |
| SIG-G1-1 | blur_score | `ml_image_quality.blur_score` OR augmentation param | MLImageQualityInfo |
| SIG-G1-2 | noise_score | `ml_image_quality.noise_score` OR augmentation param | MLImageQualityInfo |
| SIG-G1-3 | contrast_score | `ml_image_quality.contrast_score` OR augmentation param | MLImageQualityInfo |
| SIG-G1-4 | skew_score (severity) | `ml_image_quality.skew_score` OR augmentation param | MLImageQualityInfo |
| SIG-G1-5 | compression_score | `ml_image_quality.compression_score` OR augmentation param | MLImageQualityInfo |
| SIG-G1-6 | overall_quality | `ml_image_quality.overall_score` OR `llm_scores.predicted_normalized` | MLImageQualityInfo |
| SIG-G2-1 | script_code | `language.script_code` (ISO 15924) | LanguageInfo |
| SIG-G3-1 | orientation_cls | `geometric.orientation_class` (shared with MNV4-H1) | GeometricInfo |
| SIG-G3-2 | skew_reg | `geometric.skew_angle_degrees` (shared with MNV4-H2) | GeometricInfo |
| SIG-G4-1 | presence_cls | `handwriting_assessment.presence` (5-class enum) | HandwritingAssessment |
| SIG-G4-2 | legibility_cls | `handwriting_assessment.legibility` (6-class enum) | HandwritingAssessment |
| SIG-G4-3 | content_type_cls | `handwriting_assessment.content_type` (7-class enum) | HandwritingAssessment |
| SIG-G4-4 | presence_reg | `handwriting_assessment.presence_score` (0-1) | HandwritingAssessment |
| SIG-G4-5 | legibility_reg | `handwriting_assessment.legibility_score` (0-1) | HandwritingAssessment |
| SIG-G5-1 | capture_cls | `capture_method.method` (7-class enum) | CaptureMethodInfo |
| SIG-G5-2 | shadow_reg | `physical_degradation.shadow_severity` (0-1) | PhysicalDegradationInfo |
| SIG-G5-3 | warping_reg | `physical_degradation.warping_severity` (0-1) | PhysicalDegradationInfo |
| SIG-G5-4 | code_reg | `content_flags.has_code` + `structure.code_language` | ContentFlags / StructureInfo |
| SIG-G5-5 | resolution_quality_reg | `resolution.resolution_quality_score` (shared with MNV4-H3) | ResolutionInfo |

---

## Tracking Table

| Head ID | Head Name | HAR File | L2 Field | Pool Status | Assembly Status | P0 Gaps | Adequacy | Consensus |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Batch A — Geometry (P0)** | | | | | | | | |
| MNV4-H1 | orientation | [mnv4-h1-orientation.md](har/mnv4-h1-orientation.md) | `geometric.orientation_class` | ✅ 50K assembled | ✅ 50K ready | 0 | ⚠️ 63/100 | ✅ Done |
| SIG-G3-1 | orientation_cls | [sig-g3-orientation-cls.md](har/sig-g3-orientation-cls.md) | `geometric.orientation_class` | ✅ 50K assembled | ✅ 50K ready | 0 | ⚠️ 52/100 | ✅ Done |
| MNV4-H2 | skew_reg | [mnv4-h2-skew.md](har/mnv4-h2-skew.md) | `geometric.skew_angle_degrees` | ✅ 90K assembled | ✅ 90K ready | 0 | ⚠️ 55/100 | ✅ Done |
| SIG-G3-2 | skew_reg | [sig-g3-skew-reg.md](har/sig-g3-skew-reg.md) | `geometric.skew_angle_degrees` | ✅ 90K assembled | ✅ 90K ready | 0 | ⚠️ 46/100 | ✅ Done |
| **Batch B — IQA (P0)** | | | | | | | | |
| SIG-G1-6 | overall_quality | [sig-g1-overall-quality.md](har/sig-g1-overall-quality.md) | `ml_image_quality.overall_score` | ❌ 5.5K/116K (DIQA only) | ❌ 0/116K assembled | 3 | ❌ 37/100 | ✅ Done |
| SIG-G1-1 | blur_score | [sig-g1-blur-score.md](har/sig-g1-blur-score.md) | `ml_image_quality.blur_score` | ❌ 0 labeled / 116K | ❌ 0/100K synth | 3 | ⚠️ 45/100 | ✅ Done |
| SIG-G1-2 | noise_score | [sig-g1-noise-score.md](har/sig-g1-noise-score.md) | `ml_image_quality.noise_score` | ❌ 0 labeled / detector broken | ❌ 0/100K synth | 3 | ❌ 32/100 | ✅ Done |
| SIG-G1-3 | contrast_score | [sig-g1-contrast-score.md](har/sig-g1-contrast-score.md) | `ml_image_quality.contrast_score` | ❌ 0 labeled / 116K | ❌ 0/100K synth | 3 | ⚠️ 49/100 | ✅ Done |
| SIG-G1-4 | skew_score | [sig-g1-skew-score.md](har/sig-g1-skew-score.md) | `ml_image_quality.skew_score` | ❌ 0 labeled / transfer fn undefined | ❌ 0/100K synth | 3 | ⚠️ 54/100 | ✅ Done |
| SIG-G1-5 | compression_score | [sig-g1-compression-score.md](har/sig-g1-compression-score.md) | `ml_image_quality.compression_score` | ❌ 0 labeled / DCT viable | ❌ 0/100K synth | 4 | ⚠️ 65/100 | ✅ Done |
| **Batch C — Script (P0)** | | | | | | | | |
| SIG-G2-1 | script_code | [sig-g2-script-code.md](har/sig-g2-script-code.md) | `language.script_code` | ❌ 4 classes no real data; 8.6× imbalance | ❌ 0/108K target | 5 | ⚠️ 32/100 | ✅ Done |
| **Batch D — Resolution (P0/P1)** | | | | | | | | |
| MNV4-H3 | resolution_quality | [mnv4-h3-resolution-quality.md](har/mnv4-h3-resolution-quality.md) | `resolution.resolution_quality_score` | ⚠️ 5.5K/30K (DIQA-5000 only) | ❌ 0/30K blocked | 3 | ⚠️ 26/100 | ✅ Done |
| SIG-G5-5 | resolution_quality_reg | [sig-g5-resolution-quality-reg.md](har/sig-g5-resolution-quality-reg.md) | `resolution.resolution_quality_score` | ⚠️ 5.5K/30K (corrected-image path) | ❌ 0/30K blocked | 4 | ⚠️ 39/100 | ✅ Done |
| **Batch E — Handwriting (P1)** | | | | | | | | |
| SIG-G4-1 | presence_cls | [sig-g4-presence-cls.md](har/sig-g4-presence-cls.md) | `handwriting_assessment.presence` | ❌ 0 intermediate classes; NONE >350K | ❌ 0/60K blocked | 5 | ❌ 32/100 | ✅ Done |
| SIG-G4-2 | legibility_cls | [sig-g4-legibility-cls.md](har/sig-g4-legibility-cls.md) | `handwriting_assessment.legibility` | ❌ ILLEGIBLE/POOR: 0 labeled (curation bias) | ❌ 0/60K blocked | 4 | ❌ 21/100 | ✅ Done |
| SIG-G4-3 | content_type_cls | [sig-g4-content-type-cls.md](har/sig-g4-content-type-cls.md) | `handwriting_assessment.content_type` | ⏳ Pending | ⏳ 0/60K | TBD | TBD | ⏳ Pending |
| SIG-G4-4 | presence_reg | [sig-g4-presence-reg.md](har/sig-g4-presence-reg.md) | `handwriting_assessment.presence_score` | ⏳ Pending | ⏳ 0/60K | TBD | TBD | ⏳ Pending |
| SIG-G4-5 | legibility_reg | [sig-g4-legibility-reg.md](har/sig-g4-legibility-reg.md) | `handwriting_assessment.legibility_score` | ⏳ Pending | ⏳ 0/60K | TBD | TBD | ⏳ Pending |
| **Batch F — Page Attributes (P2)** | | | | | | | | |
| SIG-G5-1 | capture_cls | [sig-g5-capture-cls.md](har/sig-g5-capture-cls.md) | `capture_method.method` | ⏳ Pending | ⏳ 0/50K | TBD | TBD | ⏳ Pending |
| SIG-G5-2 | shadow_reg | [sig-g5-shadow-reg.md](har/sig-g5-shadow-reg.md) | `physical_degradation.shadow_severity` | ⏳ Pending | ⏳ 0/15K | TBD | TBD | ⏳ Pending |
| SIG-G5-3 | warping_reg | [sig-g5-warping-reg.md](har/sig-g5-warping-reg.md) | `physical_degradation.warping_severity` | ⏳ Pending | ⏳ 0/20K | TBD | TBD | ⏳ Pending |
| SIG-G5-4 | code_reg | [sig-g5-code-reg.md](har/sig-g5-code-reg.md) | `content_flags.has_code` | ⏳ Pending | ⏳ 0/10K | TBD | TBD | ⏳ Pending |

---

## Progress Summary

| Batch | Heads | Completed | Blocked | Ready |
| --- | --- | --- | --- | --- |
| A — Geometry | 4 | 4 | 0 | 0 |
| B — IQA | 6 | 6 | 2 | 0 |
| C — Script | 1 | 1 | 0 | 0 |
| D — Resolution | 2 | 2 | 0 | 0 |
| E — Handwriting | 5 | 2 | 2 | 0 |
| F — Page Attributes | 4 | 0 | TBD | TBD |
| **Total** | **22** | **15** | **4** | **0** |

---

## Key Reference Files

| File | Used For |
| --- | --- |
| [docs/planning/SIGLIP2_MULTITASK_REQUIREMENTS.md](SIGLIP2_MULTITASK_REQUIREMENTS.md) | Head specs, performance targets, training phases |
| [docs/schema/layer2_enrichment_v2.schema.json](../schema/layer2_enrichment_v2.schema.json) | L2 field definitions, enum values, provenance tiers |
| [docs/datasets/DATASET_QUICK_REFERENCE.md](../datasets/DATASET_QUICK_REFERENCE.md) | Source dataset pool, L2 audit grades |
| [docs/datasets/TRAINING_DATASET_QUICK_REFERENCE.md](../datasets/TRAINING_DATASET_QUICK_REFERENCE.md) | Assembled dataset status |
| [docs/datasets/OOD_DATASET_CATALOG.md](../datasets/OOD_DATASET_CATALOG.md) | OOD category coverage |
| [docs/planning/DATASET_DIVERSITY_REQUIREMENTS.md](DATASET_DIVERSITY_REQUIREMENTS.md) | 14 diversity dimensions, head-specific targets |
| [docs/planning/HAR_TEMPLATE.md](HAR_TEMPLATE.md) | Blank 9-section HAR template |
| [docs/planning/HAR_SYNTHESIS.md](HAR_SYNTHESIS.md) | Cross-head synthesis (created after all 22 HARs complete) |

---

## Synthesis

**HAR_SYNTHESIS.md** will be written after all 22 HARs and their Section 9 consensus reviews
are complete. It will contain:

- Gap Registry Summary (all gap IDs grouped by root cause type)
- Audit Defect Cross-Reference (which dataset audit defects block which heads)
- Blocker Dependency Graph (which heads are blocked by which missing scripts/L2 fields)
- Training Phase Risk Map (per-phase unresolved P0 gap count)
- Prioritized Remediation Backlog (ordered action list)
- Cross-Head Patterns (systemic gaps affecting multiple heads)
