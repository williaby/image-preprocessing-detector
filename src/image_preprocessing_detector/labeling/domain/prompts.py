# SPDX-FileCopyrightText: 2025 Byron Williams <byronawilliams@gmail.com>
# SPDX-License-Identifier: MIT
"""Prompt templates for domain classification and metadata enrichment.

Provides structured prompts for both text-based and vision-based
classification, designed to extract multiple Layer 2 metadata fields
in a single API call.

Example:
    >>> from image_preprocessing_detector.labeling.domain.prompts import (
    ...     build_text_prompt,
    ...     build_vision_prompt,
    ... )
    >>> messages = build_text_prompt("This paper presents a novel approach...")
    >>> # Send messages to OpenRouter API
"""

from __future__ import annotations

# System prompt shared between text and vision modes
_DOMAIN_TAXONOMY = """\
Classify the document into exactly ONE domain code:
- TAX: Tax documents (tax forms, returns, schedules, W-2, 1099, assessments)
- LEG: Legal documents (contracts, court filings, briefs, agreements, patents)
- FIN: Financial documents (invoices, receipts, bank statements, annual reports, SEC filings)
- TEC: Technical documents (manuals, specifications, datasheets, engineering drawings)
- SCI: Scientific documents (research papers, journal articles, lab reports, theses)
- ADM: Administrative documents (memos, letters, correspondence, meeting minutes)
- MED: Medical documents (patient records, prescriptions, lab results, insurance claims)
- EDU: Educational documents (textbooks, exams, worksheets, syllabi, certificates)
- PER: Personal documents (IDs, passports, birth certificates, personal letters)
- UNK: ONLY if the document is truly unclassifiable or ambiguous across multiple domains"""

_LANGUAGE_INSTRUCTIONS = """\
Identify the primary language and script:
- iso639_language: ISO 639-1 (2-letter) or ISO 639-3 (3-letter) code (e.g., "en", "ar", "zh", "de", "fr", "ja", "ko", "hi")
- iso15924_script: ISO 15924 4-letter script code (e.g., "Latn", "Arab", "Hans", "Hant", "Deva", "Jpan", "Kore")"""

_CONTENT_TYPE_INSTRUCTIONS = """\
Classify the content type (e.g., "scientific_paper", "invoice", "tax_form", \
"contract", "letter", "manual", "prescription", "exam", "receipt", \
"bank_statement", "court_filing", "research_report", "memo", "certificate")."""

_TEXT_SYSTEM_PROMPT = f"""\
You are a document metadata classifier. Given document text, extract structured metadata.

{_DOMAIN_TAXONOMY}

{_LANGUAGE_INSTRUCTIONS}

{_CONTENT_TYPE_INSTRUCTIONS}

Respond with ONLY a valid JSON object (no markdown, no explanation):
{{"domain": "XXX", "domain_confidence": 0.XX, "iso639_language": "xx", \
"iso15924_script": "Xxxx", "content_type": "type_name", \
"reasoning": "brief 1-sentence explanation"}}"""

_VISION_SYSTEM_PROMPT = f"""\
You are a document metadata classifier. Given a document image, extract structured metadata.

{_DOMAIN_TAXONOMY}

{_LANGUAGE_INSTRUCTIONS}

{_CONTENT_TYPE_INSTRUCTIONS}

Identify the capture method from visual cues:
- born_digital: Clean rendering, no scan artifacts, perfect alignment
- scanner_flatbed: Even illumination, possible border shadows, slight skew
- scanner_adf: Possible feed marks, streaks, consistent format
- camera_professional: High quality but may have slight perspective
- camera_smartphone: Perspective distortion, uneven lighting, finger shadows
- fax: Low resolution, banding artifacts, noise
- synthetic: Computer-generated, perfect rendering, artificial patterns
- unknown: Cannot determine

Identify content flags (true/false):
- has_table: Contains any tabular data
- has_formula: Contains mathematical equations or formulas
- has_handwriting: Contains handwritten text or annotations
- has_signature: Contains a signature
- has_figure: Contains figures, charts, graphs, or diagrams

Identify page orientation: "portrait" or "landscape"

Respond with ONLY a valid JSON object (no markdown, no explanation):
{{"domain": "XXX", "domain_confidence": 0.XX, "iso639_language": "xx", \
"iso15924_script": "Xxxx", "content_type": "type_name", \
"capture_method": "method", "has_table": false, "has_formula": false, \
"has_handwriting": false, "has_signature": false, "has_figure": false, \
"orientation": "portrait", "reasoning": "brief 1-sentence explanation"}}"""


def build_text_prompt(
    text: str,
    max_chars: int = 4000,
) -> list[dict[str, str]]:
    """Build chat messages for text-based domain classification.

    Args:
        text: Document text content to classify.
        max_chars: Maximum characters to include (truncates with notice).

    Returns:
        List of chat message dicts ready for OpenRouter API.
    """
    if len(text) > max_chars:
        truncated_text = text[:max_chars] + "\n\n[TEXT TRUNCATED]"
    else:
        truncated_text = text

    return [
        {"role": "system", "content": _TEXT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Classify this document text:\n\n{truncated_text}",
        },
    ]


def build_vision_prompt() -> list[dict[str, object]]:
    """Build chat messages for vision-based domain classification.

    The image content block must be appended by the caller since it
    depends on the image encoding format (base64 or URL).

    Returns:
        List of chat message dicts with system prompt and user text.
        Caller must append image content to the user message's content list.
    """
    return [
        {"role": "system", "content": _VISION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Classify this document image:",
                },
            ],
        },
    ]
