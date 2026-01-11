#!/usr/bin/env python3
"""Generate RAG Pipeline Architecture Visual Diagram.

This script creates a professional architecture diagram for the Foundry RAG Pipeline
based on the PlantUML specification.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from pathlib import Path


def create_rag_pipeline_diagram(output_path: str) -> None:
    """Create the RAG pipeline architecture diagram.

    Args:
        output_path: Path where the PNG image will be saved
    """
    # Create figure with high DPI for professional quality
    fig, ax = plt.subplots(figsize=(14, 10), dpi=200)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # Modern color palette - clean and professional
    colors = {
        "orchestration": "#E3F2FD",
        "storage": "#FFF3E0",
        "ingest": "#FFEBEE",
        "active": "#E8F5E9",
        "not_started": "#E0E0E0",
        "text": "#2C3E50",
        "border": "#BDC3C7",
        "shadow": "#34495E",
    }

    # Title - Simple and clean
    ax.text(
        7,
        9.5,
        "Foundry RAG Pipeline",
        ha="center",
        va="top",
        fontsize=22,
        fontweight="bold",
        color=colors["text"],
    )
    ax.text(
        7,
        9.2,
        "Document Processing Flow",
        ha="center",
        va="top",
        fontsize=13,
        style="italic",
        color="#7F8C8D",
    )

    # Simplified layer positions - no orchestration/storage layers
    y_positions = {
        "ingest": 8.0,
        "prepare": 6.2,
        "unify": 4.4,
        "chunk": 2.6,
        "embed": 0.8,
    }

    # Helper function to draw a modern rounded box with shadow
    def draw_modern_box(
        x, y, width, height, color, status="active", label="", sublabel="", bullets=None
    ):
        """Draw a modern rounded box with shadow effect."""
        # Shadow
        shadow = FancyBboxPatch(
            (x + 0.05, y - 0.05),
            width,
            height,
            boxstyle="round,pad=0.15",
            facecolor="#00000010",
            edgecolor="none",
            zorder=1,
        )
        ax.add_patch(shadow)

        # Main box
        box = FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.15",
            facecolor=color,
            edgecolor=colors["border"],
            linewidth=1.5,
            zorder=2,
        )
        ax.add_patch(box)

        # Status indicator
        status_color = "#27AE60" if status == "active" else "#95A5A6"
        status_circle = plt.Circle(
            (x + 0.3, y + height - 0.2), 0.08, color=status_color, zorder=3
        )
        ax.add_patch(status_circle)

        # Label
        ax.text(
            x + width / 2,
            y + height - 0.25,
            label,
            ha="center",
            va="center",
            fontsize=13,
            fontweight="bold",
            color=colors["text"],
            zorder=3,
        )

        # Sublabel
        if sublabel:
            ax.text(
                x + width / 2,
                y + height - 0.5,
                sublabel,
                ha="center",
                va="center",
                fontsize=9,
                style="italic",
                color="#7F8C8D",
                zorder=3,
            )

        # Bullets
        if bullets:
            bullet_y = y + height - 0.75
            for bullet in bullets:
                ax.text(
                    x + width / 2,
                    bullet_y,
                    f"• {bullet}",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color=colors["text"],
                    zorder=3,
                )
                bullet_y -= 0.25

    # LAYER 1 - INGEST
    draw_modern_box(
        x=1.5,
        y=y_positions["ingest"],
        width=11.0,
        height=1.0,
        color=colors["ingest"],
        status="active",
        label="Ingest",
        sublabel="(foundry-ingest)",
        bullets=["Document Track: PDF, Office, Images", "Audio Track: Audio, Video"],
    )

    # Arrow from Ingest down
    arrow1 = FancyArrowPatch(
        (7.0, y_positions["ingest"]),
        (7.0, y_positions["prepare"] + 1.0),
        arrowstyle="->",
        mutation_scale=25,
        linewidth=2.5,
        color="#7F8C8D",
        zorder=1,
    )
    ax.add_patch(arrow1)

    # LAYER 2 - PREPARE-DOC (left) and PREPARE-AUDIO (right)
    draw_modern_box(
        x=0.8,
        y=y_positions["prepare"],
        width=5.5,
        height=1.0,
        color=colors["active"],
        status="active",
        label="Prepare-Doc",
        sublabel="(foundry-prepare-doc)",
        bullets=["IQA & Corrections", "Layout Detection", "DQS & Routing"],
    )

    draw_modern_box(
        x=7.7,
        y=y_positions["prepare"],
        width=5.5,
        height=1.0,
        color=colors["active"],
        status="active",
        label="Prepare-Audio",
        sublabel="(foundry-prepare-audio)",
        bullets=["FFmpeg Extraction", "Deepgram Nova-2", "Diarization"],
    )

    # Convergent arrows from Prepare services to Unify
    arrow2 = FancyArrowPatch(
        (3.5, y_positions["prepare"]),
        (5.5, y_positions["unify"] + 0.9),
        arrowstyle="->",
        mutation_scale=25,
        linewidth=2.5,
        color="#7F8C8D",
        zorder=1,
    )
    ax.add_patch(arrow2)

    arrow3 = FancyArrowPatch(
        (10.5, y_positions["prepare"]),
        (8.5, y_positions["unify"] + 0.9),
        arrowstyle="->",
        mutation_scale=25,
        linewidth=2.5,
        color="#7F8C8D",
        zorder=1,
    )
    ax.add_patch(arrow3)

    # LAYER 3 - UNIFY
    draw_modern_box(
        x=1.5,
        y=y_positions["unify"],
        width=11.0,
        height=0.9,
        color=colors["not_started"],
        status="not_started",
        label="Unify",
        sublabel="(foundry-unify) - Normalized JSON (LayoutParser schema)",
        bullets=["Docling DOM: Unified schema"],
    )

    # Arrow from Unify to Chunk
    arrow4 = FancyArrowPatch(
        (7.0, y_positions["unify"]),
        (7.0, y_positions["chunk"] + 0.9),
        arrowstyle="->",
        mutation_scale=25,
        linewidth=2.5,
        color="#7F8C8D",
        zorder=1,
    )
    ax.add_patch(arrow4)

    # LAYER 4 - CHUNK
    draw_modern_box(
        x=1.5,
        y=y_positions["chunk"],
        width=11.0,
        height=0.9,
        color=colors["not_started"],
        status="not_started",
        label="Chunk",
        sublabel="(foundry-chunk)",
        bullets=["Trust Scoring", "RAG Chunking", "Normalization"],
    )

    # Arrow from Chunk to Embed
    arrow5 = FancyArrowPatch(
        (7.0, y_positions["chunk"]),
        (7.0, y_positions["embed"] + 0.9),
        arrowstyle="->",
        mutation_scale=25,
        linewidth=2.5,
        color="#7F8C8D",
        zorder=1,
    )
    ax.add_patch(arrow5)

    # LAYER 5 - EMBED
    draw_modern_box(
        x=1.5,
        y=y_positions["embed"],
        width=11.0,
        height=0.9,
        color=colors["not_started"],
        status="not_started",
        label="Embed",
        sublabel="(foundry-embed)",
        bullets=["Embedding Gen", "Vector DB", "Retrieval API"],
    )

    # Output label at bottom
    ax.text(
        7.0,
        0.3,
        "→ Collection ID",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        color="#27AE60",
        bbox={
            "boxstyle": "round,pad=0.5",
            "facecolor": "#E8F5E9",
            "edgecolor": "#27AE60",
            "linewidth": 1.5,
        },
    )

    # No legend needed - the diagram is self-explanatory with status dots and clean colors

    # Save the figure
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"Diagram saved to: {output_path}")
    plt.close()


if __name__ == "__main__":
    output_path = "/home/byron/dev/image_detection/docs/architecture/diagrams/level-0/rag-pipeline-visual.png"
    create_rag_pipeline_diagram(output_path)
