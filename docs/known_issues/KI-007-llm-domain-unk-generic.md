# KI-007: LLM Domain Classification UNK on Generic Content

> **Severity**: LOW | **Status**: ACCEPTED | **Discovered**: 2026-02-11

## Summary

LLM domain classification produces a high rate of `domain_level1=UNK` on generic, narrative, or creative text content. This is expected behavior, not a defect - the domain taxonomy does not cover literary/narrative content well.

## Scope

All datasets with generic, narrative, literary, or creative text content.

## Root Cause

The domain classification taxonomy (ADM, EDU, SCI, FIN, MED, TEC, LEG, PER, TAX) is designed for formal document types. Generic content such as personal narratives, cultural essays, fictional writing, and creative prose does not fit cleanly into any category. The LLM correctly identifies this gap by outputting `UNK`.

## Evidence

**JSSODa (2,000 images)**:

| Domain | Count | Pct |
|--------|------:|----:|
| UNK | 693 | 34.7% |
| ADM | 621 | 31.1% |
| EDU | 187 | 9.4% |
| SCI | 174 | 8.7% |
| PER | 111 | 5.6% |
| MED | 82 | 4.1% |
| TEC | 74 | 3.7% |
| LEG | 33 | 1.7% |
| FIN | 22 | 1.1% |
| TAX | 3 | 0.2% |

VLM inspection of 4 UNK samples confirmed they are genuinely generic content (personal narratives, cultural essays) that does not fit the taxonomy.

## Assessment

The UNK classification is **correct behavior** for the current taxonomy. The 693 UNK samples cause `domain_level1` prescreening failure (34.65% fail rate), but this is a taxonomy limitation, not an enrichment defect.

## Possible Future Improvements

- Add `GEN` (general) or `LIT` (literary) domain category to reduce UNK rate
- Reclassify some UNK samples to `PER` (personal) where content is personal narratives
- Accept UNK as a valid domain for training diversity purposes

## Mitigation

Accept `domain_level1=UNK` on prescreening. Do not force reclassification.
