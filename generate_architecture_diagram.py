import matplotlib.patches as patches
import matplotlib.pyplot as plt


def create_architecture_diagram():
    # --- Configuration ---
    # Resolution: 2752 x 1536 (2K 16:9)
    dpi = 100
    width_px = 2752
    height_px = 1536
    figsize = (width_px / dpi, height_px / dpi)

    # Colors
    bg_color = "#0B1120"  # Deep Navy Blue
    grid_color = "#1E293B"  # Lighter Navy for grid
    text_color = "#FFFFFF"
    arrow_color = "#94A3B8"  # Slate 400

    # Layer Colors
    color_frontend = "#F472B6"  # Pink/Salmon (Tailwind Pink 400)
    color_active = "#4ADE80"  # Green (Tailwind Green 400)
    color_future = "#94A3B8"  # Gray (Tailwind Slate 400)

    # Gradient/Fill Opacity
    box_alpha = 0.15
    border_linewidth = 2.5

    # --- Setup Plot ---
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    ax.set_facecolor(bg_color)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.invert_yaxis()  # 0 at top to match mental model of "layers down"

    # Draw Grid
    for x in range(0, 101, 5):
        ax.axvline(x, color=grid_color, linewidth=1, zorder=0)
    for y in range(0, 101, 5):
        ax.axhline(y, color=grid_color, linewidth=1, zorder=0)

    # Hide axes
    ax.axis("off")

    # --- Helper Functions ---
    def draw_box(x, y, w, h, color, title, items, icon=""):
        # Shadow/Glow effect
        shadow = patches.FancyBboxPatch(
            (x + 0.5, y + 0.5),
            w,
            h,
            boxstyle="round,pad=0.5,rounding_size=1",
            facecolor="black",
            alpha=0.3,
            zorder=1,
        )
        ax.add_patch(shadow)

        # Main Box
        box = patches.FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.5,rounding_size=1",
            facecolor=color,
            alpha=box_alpha,
            edgecolor=color,
            linewidth=border_linewidth,
            zorder=2,
        )
        ax.add_patch(box)

        # Title Background for contrast
        title_bg = patches.FancyBboxPatch(
            (x, y),
            w,
            4,  # Height of title bar
            boxstyle="round,pad=0.5,rounding_size=1",
            facecolor=color,
            alpha=0.3,
            edgecolor="none",
            zorder=2,
        )
        # Clip the bottom of the title bg manually or just layer it?
        # Layering is fine for this aesthetic.

        # Title
        ax.text(
            x + w / 2,
            y + 2,
            f"{icon} {title}",
            ha="center",
            va="center",
            fontsize=16,
            fontweight="bold",
            color=text_color,
            zorder=3,
        )

        # Content Items
        item_start_y = y + 6
        for i, item in enumerate(items):
            ax.text(
                x + w / 2,
                item_start_y + (i * 3.5),
                f"• {item}",
                ha="center",
                va="center",
                fontsize=12,
                color="#E2E8F0",
                zorder=3,
            )

        return (x + w / 2, y + h)  # Return bottom center for connections

    def draw_arrow(start_coords, end_coords, text="", curve=0, color=arrow_color):
        style = "Simple,tail_width=1.5,head_width=8,head_length=8"
        connection_style = f"arc3,rad={curve}"

        arrow = patches.FancyArrowPatch(
            posA=start_coords,
            posB=end_coords,
            arrowstyle=style,
            connectionstyle=connection_style,
            color=color,
            zorder=1,
        )
        ax.add_patch(arrow)

        if text:
            mid_x = (start_coords[0] + end_coords[0]) / 2
            mid_y = (start_coords[1] + end_coords[1]) / 2
            # Add box behind text for readability
            txt = ax.text(
                mid_x + (curve * 5),
                mid_y,
                text,
                ha="center",
                va="center",
                fontsize=10,
                color=bg_color,
                fontweight="bold",
                bbox=dict(
                    facecolor=color,
                    edgecolor="none",
                    boxstyle="round,pad=0.3",
                    alpha=0.9,
                ),
                zorder=4,
            )

    # --- LAYOUT DEFINITIONS ---

    # Layer 1: Frontend (Top)
    # y=5 to y=15
    l1_center, l1_bottom = 50, 15
    draw_box(
        35,
        5,
        30,
        10,
        color_frontend,
        "rag-processor Web UI",
        ["PDF / Office / Images 📄", "Audio / Video Upload 🔊"],
        icon="🖥️",
    )

    # Layer 2: Active Projects (Side by Side)
    # y=25 to y=45
    # Box A: Left
    l2_left_center = draw_box(
        15,
        25,
        30,
        18,
        color_active,
        "Project A: Prep & Layout",
        ["IQA & Corrections", "Layout Detection (YOLO)", "DQS & Dynamic Routing"],
    )

    # Box Audio: Right
    l2_right_center = draw_box(
        55,
        25,
        30,
        18,
        color_active,
        "Audio Processor",
        ["FFmpeg Extraction", "Deepgram Nova-2", "Diarization"],
        icon="🎙️",
    )

    # Layer 3: Project B (Middle)
    # y=55 to y=68
    l3_center = draw_box(
        30,
        55,
        40,
        13,
        color_future,
        "Project B: OCR Orchestration",
        ["Multi-Engine OCR & Selection", "Result Fusion", "Docling DOM 🛢️"],
    )

    # Layer 4: Project C
    # y=75 to y=85
    l4_center = draw_box(
        35,
        75,
        30,
        10,
        color_future,
        "Project C: Fusion & Trust",
        ["Trust Scoring", "RAG Chunking", "Normalization"],
    )

    # Layer 5: Project D (Bottom)
    # y=90 to y=100 (actually fitting just inside)
    l5_center = draw_box(
        35,
        90,
        30,
        10,
        color_future,
        "Project D: Vector Store",
        ["Embedding Generation", "Vector Database 🛢️", "Retrieval API"],
        icon="🧠",
    )

    # --- CONNECTIONS ---

    # 1. Frontend -> Project A (Left)
    draw_arrow((50, 16), (30, 24), "Documents/Images")

    # 2. Frontend -> Audio Processor (Right)
    draw_arrow((50, 16), (70, 24), "Audio/Video")

    # 3. Project A -> Project B
    draw_arrow((30, 44), (45, 54), "Doc Metadata +\nPreprocessed Pages")

    # 4. Audio -> Project B
    draw_arrow((70, 44), (55, 54), "Transcript Meta +\nAudio Segments")

    # 5. Project B -> Project C
    draw_arrow((50, 69), (50, 74), "Unified Docling DOM")

    # 6. Project C -> Project D
    draw_arrow((50, 86), (50, 89), "Normalized Text +\nRAG ChunkSet")

    # 7. Project D -> Frontend (Upward Loop)
    # Using a large curve to go around the right side
    # Start right side of D, end right side of Frontend
    loop_arrow = patches.FancyArrowPatch(
        posA=(66, 95),
        posB=(66, 10),
        arrowstyle="Simple,tail_width=1.5,head_width=8,head_length=8",
        connectionstyle="arc3,rad=0.4",  # High curve to swing wide
        color=color_future,
        alpha=0.6,
        linestyle="dashed",
        zorder=0,
    )
    ax.add_patch(loop_arrow)

    # Label for loop arrow
    ax.text(
        85,
        50,
        "Collection ID",
        ha="center",
        va="center",
        rotation=270,
        fontsize=12,
        color=color_future,
        fontweight="bold",
        bbox=dict(facecolor=bg_color, edgecolor=color_future, boxstyle="round,pad=0.3"),
    )

    # --- LEGEND & Branding ---
    # Bottom Left Legend
    ax.text(2, 98, "LEGEND", color="white", fontsize=10, fontweight="bold")

    # Frontend
    rect_f = patches.Rectangle((2, 95), 2, 2, facecolor=color_frontend, alpha=0.8)
    ax.add_patch(rect_f)
    ax.text(5, 96, "Frontend", color="white", fontsize=9, va="center")

    # Active
    rect_a = patches.Rectangle((2, 92), 2, 2, facecolor=color_active, alpha=0.8)
    ax.add_patch(rect_a)
    ax.text(5, 93, "Active Dev", color="white", fontsize=9, va="center")

    # Future
    rect_g = patches.Rectangle((2, 89), 2, 2, facecolor=color_future, alpha=0.8)
    ax.add_patch(rect_g)
    ax.text(5, 90, "Pending/Future", color="white", fontsize=9, va="center")

    # Title Top Left
    ax.text(
        2,
        4,
        "RAG PIPELINE ARCHITECTURE",
        color="#64748B",
        fontsize=24,
        fontweight="bold",
        alpha=0.5,
    )

    # Save
    plt.tight_layout()
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    plt.savefig("rag_architecture.png", dpi=dpi, facecolor=bg_color)
    print("Architecture diagram generated: rag_architecture.png")


if __name__ == "__main__":
    create_architecture_diagram()
