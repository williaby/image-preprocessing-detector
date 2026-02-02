# Dataset Documentation

> **Purpose**: Modular dataset documentation with task-based discovery
> **Organization**: Flat alphabetical by origin + task-based indices
> **Total Datasets**: 51 source + 2 training = 53 datasets

---

## Quick Start

**Looking for a specific dataset?** → Check `source/{canonical-name}.md` (alphabetical)

**Looking for datasets by task?** → Check task indices:

- [indices/IQA.md](indices/IQA.md) - IQA training datasets
- [indices/LAYOUT.md](indices/LAYOUT.md) - Layout detection datasets
- [indices/TABLES.md](indices/TABLES.md) - Table structure datasets
- [indices/TEXT_DETECTION.md](indices/TEXT_DETECTION.md) - Text detection & script classification
- [indices/HANDWRITING.md](indices/HANDWRITING.md) - Handwriting detection & legibility
- [indices/BENCHMARKS.md](indices/BENCHMARKS.md) - Benchmark restrictions
- [indices/SCRIPTS.md](indices/SCRIPTS.md) - Script-specific datasets

**Need quick stats?** → Read [DATASET_QUICK_REFERENCE.md](DATASET_QUICK_REFERENCE.md) first

---

## Directory Structure

```
docs/datasets/
├── README.md                              # This file
├──
├── DATASET_QUICK_REFERENCE.md             # Quick stats, task groups, restrictions
├── DATASET_PROCESSING_STATUS.md           # Conversion status, blockers, ETAs
├── DATASET_NAMING_STANDARD.md             # Canonical names, aliases
├── DATASET_TEMPLATE.md                    # Template for source datasets
├──
├── TRAINING_DATASET_QUICK_REFERENCE.md    # Training dataset quick stats
├── TRAINING_DATASET_CATALOG.md            # Training dataset full docs
├── TRAINING_DATASET_TEMPLATE.md           # Template for training datasets
├──
├── source/                                # External source datasets (51)
│   ├── arabic-docs-ocr.md
│   ├── bentham-handwritten.md
│   ├── bhutan-afs.md
│   ├── ...
│   ├── tablebank.md
│   └── yarmouk-ocr.md
├──
├── training/                              # Generated/synthetic datasets (2)
│   ├── orientation.md                     # 50K orientation detection
│   └── synth-multiscript-250k.md          # 250K script detection (in progress)
├──
├── indices/                               # Task-based discovery
│   ├── BENCHMARKS.md                      # Benchmark restrictions
│   ├── HANDWRITING.md                     # Handwriting detection
│   ├── IQA.md                             # IQA training
│   ├── LAYOUT.md                          # Layout detection
│   ├── SCRIPTS.md                         # Script-specific datasets
│   ├── TABLES.md                          # Table structure
│   └── TEXT_DETECTION.md                  # Text detection & scripts
├──
├── reviews/                               # Dataset review notes
└── source_labels/                         # Label format documentation
```

---

## Organization Philosophy

**Why flat alphabetical + task indices?**

1. **No forced categorization** - Datasets serve multiple purposes (e.g., DIQA-5000 is benchmark AND IQA training)
2. **Easy lookup** - Know the name? Go to `source/{name}.md` directly
3. **Task-based discovery** - Need IQA datasets? Read `indices/IQA.md` (just links)
4. **Clear origin separation** - source/ = external, training/ = generated

**Why separate source/ and training/?**

- **source/**: Datasets downloaded from external sources (researchers, competitions, repositories)
- **training/**: Datasets we generate/assemble from source datasets (orientation, synth-multiscript-250k)

This separation clarifies:

- **Provenance**: Generated datasets reference source datasets used
- **Reproducibility**: Training datasets can be regenerated from source
- **Licensing**: Training datasets inherit licenses from source components

---

## File Naming Conventions

**Source datasets**: Use canonical names from [DATASET_NAMING_STANDARD.md](DATASET_NAMING_STANDARD.md)

- Lowercase, kebab-case (hyphens, not underscores)
- Examples: `ohr-bench.md`, `diqa-5000.md`, `nist-sd19.md`

**Training datasets**: Descriptive names

- Lowercase, kebab-case
- Examples: `orientation.md`, `synth-multiscript-250k.md`

---

## Usage Patterns

### Find Dataset by Name

```bash
# Know the canonical name?
cat docs/datasets/source/tablebank.md

# Not sure of exact name? Check naming standard
grep -i "tablebank" docs/datasets/DATASET_NAMING_STANDARD.md
```

### Find Datasets by Task

```bash
# Need IQA training datasets?
cat docs/datasets/indices/IQA.md

# Need table datasets?
cat docs/datasets/indices/TABLES.md
```

### Check Benchmark Restrictions

```bash
# Before training, check restrictions
cat docs/datasets/indices/BENCHMARKS.md

# Or check individual dataset file
cat docs/datasets/source/ohr-bench.md | grep -A5 "Benchmark"
```

### Quick Stats Lookup

```bash
# Start with Quick Reference
cat docs/datasets/DATASET_QUICK_REFERENCE.md

# Then drill down to specific dataset if needed
cat docs/datasets/source/{dataset-name}.md
```

---

## Restriction Levels

**🔒 Benchmark-Only (Test Only)**:

- cc-ocr, omnidocbench
- **Rule**: NEVER use for training

**⚠️ Benchmark-Reserved (Train OK, Test Protected)**:

- ohr-bench, diqa-5000, pubtabnet, doclaynet, funsd, mdiw13, mlt19, cocotext, hiertext, hasyv2, smartdoc-qa
- **Rule**: Can train on train/val, NEVER use test splits

**✅ Unrestricted (Full Training Allowed)**:

- tablebank, fintabnet, rvl-cdip, sroie, doc3d, realdae, and most others
- **Rule**: Can use all splits for training

---

## Maintenance

**Adding new source dataset**:

1. Create `source/{canonical-name}.md` using [DATASET_TEMPLATE.md](DATASET_TEMPLATE.md)
2. Add to [DATASET_QUICK_REFERENCE.md](DATASET_QUICK_REFERENCE.md)
3. Add to [DATASET_NAMING_STANDARD.md](DATASET_NAMING_STANDARD.md)
4. Add to relevant task indices (e.g., `indices/IQA.md`)
5. Update [DATASET_PROCESSING_STATUS.md](DATASET_PROCESSING_STATUS.md)

**Adding new training dataset**:

1. Create `training/{descriptive-name}.md` using [TRAINING_DATASET_TEMPLATE.md](TRAINING_DATASET_TEMPLATE.md)
2. Add to [TRAINING_DATASET_QUICK_REFERENCE.md](TRAINING_DATASET_QUICK_REFERENCE.md)
3. Document source datasets used in generation
4. Add to relevant task indices if applicable

---

## Token Efficiency

| Query Type | Files Read | Token Cost | vs Old Catalog |
|------------|------------|------------|----------------|
| "Datasets for IQA?" | indices/IQA.md | ~2K | 96% savings |
| "TableBank details?" | source/tablebank.md | ~500-1K | 98% savings |
| "All IQA datasets?" | QUICK_REFERENCE.md | ~8K | 82% savings |
| "Deep technical details?" | source/{dataset}.md | ~500-2K each | 95%+ savings |

**Old approach**: Read entire 11,000-line DATASET_CATALOG.md (45K tokens)
**New approach**: Read only what you need (500-8K tokens typically)

---

*This modular structure reduces context consumption by 90-98% for typical dataset queries while maintaining comprehensive documentation.*
