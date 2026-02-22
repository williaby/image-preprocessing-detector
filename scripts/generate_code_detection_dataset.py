"""Generate the code-detection training dataset for the SigLIP 2 code_present head.

Dataset composition (10K total)
--------------------------------
Positive class (code_present=True, confidence=1.0):
  - 4,000 synthetic "code screenshot" renders: PIL + Pygments on built-in snippets,
    varied themes (dark/light), fonts, DPI tiers, and languages.
  - 1,000 "printed code in document" renders: mono-spaced text with surrounding
    paragraph text to simulate a technical manual / academic paper style.

Negative class (code_present=False, confidence=0.0):
  - 2,000 STEM pages from ``multimodal_textbook`` local images (formulas/figures,
    no code blocks).
  - 3,000 records from DocLayNet or synth-multiscript-v3 L2 metadata (GCS-path
    records — training job downloads from Modal volume).

Output
------
A JSONL manifest::

    {
        "image_path": str,          # relative to --output-dir (generated) or GCS path
        "source_dataset": str,      # "synthetic_code", "multimodal_textbook", "doclaynet", …
        "code_present": bool,
        "code_confidence": float,   # 1.0 positive, 0.0 negative, 0.5 edge-case STEM
        "language": str | null,     # "python", "javascript", … or null for negatives
        "theme": str | null,        # "monokai", "vs", … or null for negatives
        "split": str,               # "train", "val", or "test"
        "label_method": str,        # "synthetic_param" | "l2_metadata" | "dataset_class"
    }

Usage
-----
::

    # Generate positives only (no external datasets needed)
    uv run python scripts/generate_code_detection_dataset.py \\
        --positives 5000 --negatives 0 \\
        --output-dir /mnt/e/image_detection/03_training_datasets/code_detection \\
        --manifest code_manifest.jsonl

    # Full dataset with negatives from L2 metadata
    uv run python scripts/generate_code_detection_dataset.py \\
        --positives 5000 --negatives 5000 \\
        --l2-dir /mnt/e/image_detection/metadata_registry/json \\
        --base-data-root /mnt/e/image_detection/01_base_data \\
        --output-dir /mnt/e/image_detection/03_training_datasets/code_detection \\
        --manifest code_manifest.jsonl

    # Dry-run (count records, no image generation)
    uv run python scripts/generate_code_detection_dataset.py --dry-run
"""

from __future__ import annotations

import json
import logging
import random
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import click
from PIL import Image, ImageDraw, ImageFont
from pygments import highlight
from pygments.formatters import ImageFormatter
from pygments.lexers import get_lexer_by_name
from tqdm import tqdm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LANGUAGES: list[str] = [
    "python",
    "javascript",
    "java",
    "go",
    "rust",
    "sql",
    "bash",
    "cpp",
]

# Pygments style names (dark themes → code screenshots; light → printed-code style)
_DARK_STYLES: list[str] = ["monokai", "dracula", "native", "fruity", "vim"]
_LIGHT_STYLES: list[str] = ["friendly", "colorful", "tango", "murphy", "paraiso-light"]

# DPI tiers: (width_px, font_size) pairs for varied resolution
_DPI_CONFIGS: list[tuple[int, int]] = [
    (800, 12),  # 72 dpi equivalent — small/compressed
    (1024, 14),  # 96 dpi equivalent — standard screen
    (1200, 16),  # 150 dpi equivalent — retina-style
    (1600, 18),  # 300 dpi equivalent — high-res
]

# Monospace fonts to rotate through (system + downloaded)
_MONO_FONTS: list[str] = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/ubuntu/UbuntuMono[wght].ttf",
    "/usr/share/fonts/truetype/noto/NotoMono-Regular.ttf",
    "/home/byron/.local/share/fonts/synthetic-gen/FiraMono-Medium.ttf",
]

# Train/val/test split fractions
_SPLIT_FRACS: tuple[float, float, float] = (0.80, 0.10, 0.10)

# ---------------------------------------------------------------------------
# Code snippet library
# ---------------------------------------------------------------------------
# Short, illustrative, non-proprietary code snippets.  Each is 10-25 lines.
# These cover common programming patterns without any real-world sensitive code.

_SNIPPETS: dict[str, list[str]] = {
    "python": [
        textwrap.dedent("""\
            from dataclasses import dataclass
            from typing import Optional

            @dataclass
            class Rectangle:
                width: float
                height: float
                color: str = "white"

                @property
                def area(self) -> float:
                    return self.width * self.height

                @property
                def perimeter(self) -> float:
                    return 2 * (self.width + self.height)

                def scale(self, factor: float) -> "Rectangle":
                    return Rectangle(self.width * factor, self.height * factor)
        """),
        textwrap.dedent("""\
            import hashlib
            import json
            from pathlib import Path

            def compute_file_sha256(path: Path) -> str:
                hasher = hashlib.sha256()
                with open(path, "rb") as fh:
                    for chunk in iter(lambda: fh.read(65536), b""):
                        hasher.update(chunk)
                return hasher.hexdigest()

            def build_registry(data_dir: Path) -> dict[str, str]:
                registry: dict[str, str] = {}
                for file in data_dir.rglob("*"):
                    if file.is_file():
                        registry[str(file)] = compute_file_sha256(file)
                return registry
        """),
        textwrap.dedent("""\
            from functools import lru_cache
            from typing import Iterator

            def fibonacci() -> Iterator[int]:
                a, b = 0, 1
                while True:
                    yield a
                    a, b = b, a + b

            @lru_cache(maxsize=128)
            def nth_fibonacci(n: int) -> int:
                if n < 2:
                    return n
                return nth_fibonacci(n - 1) + nth_fibonacci(n - 2)

            def first_n_fibonacci(count: int) -> list[int]:
                gen = fibonacci()
                return [next(gen) for _ in range(count)]
        """),
        textwrap.dedent("""\
            import asyncio
            import aiohttp
            from typing import Any

            async def fetch_json(url: str, session: aiohttp.ClientSession) -> Any:
                async with session.get(url) as response:
                    response.raise_for_status()
                    return await response.json()

            async def fetch_all(urls: list[str]) -> list[Any]:
                async with aiohttp.ClientSession() as session:
                    tasks = [fetch_json(url, session) for url in urls]
                    return await asyncio.gather(*tasks)

            if __name__ == "__main__":
                urls = ["https://api.example.com/items/1"]
                results = asyncio.run(fetch_all(urls))
        """),
        textwrap.dedent("""\
            from collections import defaultdict
            from typing import TypeVar, Callable

            T = TypeVar("T")
            K = TypeVar("K")

            def group_by(
                items: list[T], key_fn: Callable[[T], K]
            ) -> dict[K, list[T]]:
                groups: dict[K, list[T]] = defaultdict(list)
                for item in items:
                    groups[key_fn(item)].append(item)
                return dict(groups)

            words = ["apple", "ant", "banana", "avocado", "berry"]
            by_letter = group_by(words, lambda w: w[0])
        """),
    ],
    "javascript": [
        textwrap.dedent("""\
            class EventEmitter {
              #listeners = new Map();

              on(event, handler) {
                if (!this.#listeners.has(event)) {
                  this.#listeners.set(event, []);
                }
                this.#listeners.get(event).push(handler);
                return this;
              }

              off(event, handler) {
                const handlers = this.#listeners.get(event) ?? [];
                this.#listeners.set(event, handlers.filter(h => h !== handler));
                return this;
              }

              emit(event, ...args) {
                (this.#listeners.get(event) ?? []).forEach(h => h(...args));
              }
            }
        """),
        textwrap.dedent("""\
            async function fetchWithRetry(url, options = {}, maxRetries = 3) {
              for (let attempt = 0; attempt <= maxRetries; attempt++) {
                try {
                  const response = await fetch(url, options);
                  if (!response.ok) throw new Error(`HTTP ${response.status}`);
                  return await response.json();
                } catch (error) {
                  if (attempt === maxRetries) throw error;
                  const delay = Math.pow(2, attempt) * 100;
                  await new Promise(resolve => setTimeout(resolve, delay));
                }
              }
            }

            const data = await fetchWithRetry('/api/items');
        """),
        textwrap.dedent("""\
            const pipe = (...fns) => (x) => fns.reduce((v, f) => f(v), x);

            const toUpper = str => str.toUpperCase();
            const trim = str => str.trim();
            const addExcl = str => str + '!';

            const transform = pipe(trim, toUpper, addExcl);
            console.log(transform('  hello world  ')); // => 'HELLO WORLD!'

            function memoize(fn) {
              const cache = new Map();
              return function(...args) {
                const key = JSON.stringify(args);
                if (!cache.has(key)) cache.set(key, fn(...args));
                return cache.get(key);
              };
            }
        """),
    ],
    "java": [
        textwrap.dedent("""\
            import java.util.*;
            import java.util.stream.*;

            public class StreamExamples {
                record Person(String name, int age, String department) {}

                public static Map<String, Double> avgAgeByDept(List<Person> people) {
                    return people.stream()
                        .collect(Collectors.groupingBy(
                            Person::department,
                            Collectors.averagingInt(Person::age)
                        ));
                }

                public static List<String> topNames(List<Person> people, int limit) {
                    return people.stream()
                        .sorted(Comparator.comparingInt(Person::age).reversed())
                        .limit(limit)
                        .map(Person::name)
                        .toList();
                }
            }
        """),
        textwrap.dedent("""\
            import java.util.concurrent.*;
            import java.util.function.*;

            public class CircuitBreaker<T> {
                private final int threshold;
                private final long timeoutMs;
                private volatile int failures = 0;
                private volatile long lastFailure = 0;

                public CircuitBreaker(int threshold, long timeoutMs) {
                    this.threshold = threshold;
                    this.timeoutMs = timeoutMs;
                }

                public T call(Supplier<T> operation) throws Exception {
                    if (isOpen()) throw new RuntimeException("Circuit is OPEN");
                    try {
                        T result = operation.get();
                        failures = 0;
                        return result;
                    } catch (Exception e) {
                        recordFailure();
                        throw e;
                    }
                }

                private boolean isOpen() {
                    return failures >= threshold &&
                        System.currentTimeMillis() - lastFailure < timeoutMs;
                }

                private void recordFailure() {
                    failures++;
                    lastFailure = System.currentTimeMillis();
                }
            }
        """),
    ],
    "go": [
        textwrap.dedent("""\
            package main

            import (
                "context"
                "fmt"
                "sync"
            )

            type WorkerPool struct {
                workers int
                jobs    chan func()
                wg      sync.WaitGroup
            }

            func NewWorkerPool(workers int) *WorkerPool {
                pool := &WorkerPool{
                    workers: workers,
                    jobs:    make(chan func(), workers*10),
                }
                for i := 0; i < workers; i++ {
                    pool.wg.Add(1)
                    go pool.run()
                }
                return pool
            }

            func (p *WorkerPool) run() {
                defer p.wg.Done()
                for job := range p.jobs {
                    job()
                }
            }
        """),
        textwrap.dedent("""\
            package config

            import (
                "os"
                "strconv"
                "time"
            )

            type Config struct {
                Host     string
                Port     int
                Timeout  time.Duration
                Debug    bool
            }

            func FromEnv() Config {
                port, _ := strconv.Atoi(getenv("PORT", "8080"))
                timeout, _ := time.ParseDuration(getenv("TIMEOUT", "30s"))
                return Config{
                    Host:    getenv("HOST", "localhost"),
                    Port:    port,
                    Timeout: timeout,
                    Debug:   getenv("DEBUG", "false") == "true",
                }
            }

            func getenv(key, fallback string) string {
                if v := os.Getenv(key); v != "" {
                    return v
                }
                return fallback
            }
        """),
    ],
    "rust": [
        textwrap.dedent("""\
            use std::collections::HashMap;

            pub struct Cache<K, V> {
                store: HashMap<K, V>,
                capacity: usize,
            }

            impl<K: Eq + std::hash::Hash + Clone, V: Clone> Cache<K, V> {
                pub fn new(capacity: usize) -> Self {
                    Self { store: HashMap::new(), capacity }
                }

                pub fn get(&self, key: &K) -> Option<&V> {
                    self.store.get(key)
                }

                pub fn insert(&mut self, key: K, value: V) -> Option<V> {
                    if self.store.len() >= self.capacity {
                        self.evict();
                    }
                    self.store.insert(key, value)
                }

                fn evict(&mut self) {
                    if let Some(key) = self.store.keys().next().cloned() {
                        self.store.remove(&key);
                    }
                }
            }
        """),
        textwrap.dedent("""\
            use std::fmt;
            use std::str::FromStr;

            #[derive(Debug, Clone, PartialEq)]
            pub enum Token {
                Number(f64),
                Plus,
                Minus,
                Star,
                Slash,
                LParen,
                RParen,
            }

            impl fmt::Display for Token {
                fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                    match self {
                        Token::Number(n) => write!(f, "{}", n),
                        Token::Plus => write!(f, "+"),
                        Token::Minus => write!(f, "-"),
                        Token::Star => write!(f, "*"),
                        Token::Slash => write!(f, "/"),
                        Token::LParen => write!(f, "("),
                        Token::RParen => write!(f, ")"),
                    }
                }
            }
        """),
    ],
    "sql": [
        textwrap.dedent("""\
            -- Monthly revenue analysis with year-over-year comparison
            WITH monthly_revenue AS (
                SELECT
                    DATE_TRUNC('month', order_date) AS month,
                    SUM(total_amount) AS revenue,
                    COUNT(DISTINCT customer_id) AS unique_customers
                FROM orders
                WHERE status = 'completed'
                GROUP BY 1
            ),
            yoy AS (
                SELECT
                    month,
                    revenue,
                    unique_customers,
                    LAG(revenue, 12) OVER (ORDER BY month) AS prev_year_revenue
                FROM monthly_revenue
            )
            SELECT
                month,
                revenue,
                unique_customers,
                ROUND(100.0 * (revenue - prev_year_revenue) / prev_year_revenue, 2)
                    AS yoy_growth_pct
            FROM yoy
            ORDER BY month DESC;
        """),
        textwrap.dedent("""\
            -- Recursive CTE: employee hierarchy
            WITH RECURSIVE hierarchy AS (
                SELECT id, name, manager_id, 0 AS depth,
                       name::TEXT AS path
                FROM employees
                WHERE manager_id IS NULL

                UNION ALL

                SELECT e.id, e.name, e.manager_id, h.depth + 1,
                       h.path || ' > ' || e.name
                FROM employees e
                JOIN hierarchy h ON e.manager_id = h.id
            )
            SELECT
                LPAD(' ', depth * 2) || name AS indented_name,
                depth,
                path
            FROM hierarchy
            ORDER BY path;
        """),
    ],
    "bash": [
        textwrap.dedent("""\
            #!/usr/bin/env bash
            set -euo pipefail

            SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
            LOG_FILE="${SCRIPT_DIR}/deploy.log"

            log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
            die() { log "ERROR: $*" >&2; exit 1; }

            check_dependencies() {
                local missing=()
                for cmd in docker kubectl helm; do
                    command -v "$cmd" &>/dev/null || missing+=("$cmd")
                done
                [[ ${#missing[@]} -eq 0 ]] || die "Missing: ${missing[*]}"
            }

            deploy() {
                local image="$1" namespace="$2"
                log "Deploying $image to $namespace"
                kubectl set image deployment/app "app=$image" -n "$namespace" || die "Deploy failed"
                kubectl rollout status deployment/app -n "$namespace" --timeout=300s
                log "Deployment complete"
            }

            check_dependencies
            deploy "${1:?Usage: $0 <image> <namespace>}" "${2:?}"
        """),
        textwrap.dedent("""\
            #!/usr/bin/env bash
            # Parallel file processor with progress tracking
            set -euo pipefail

            process_file() {
                local file="$1"
                local out_dir="$2"
                local base; base="$(basename "$file" .txt)"
                # Process: count words, lines, unique words
                local words lines unique
                words=$(wc -w < "$file")
                lines=$(wc -l < "$file")
                unique=$(tr '[:space:]' '\\n' < "$file" | sort -u | wc -l)
                printf '%s,%d,%d,%d\\n' "$base" "$words" "$lines" "$unique" \
                    >> "$out_dir/stats.csv"
            }
            export -f process_file

            INPUT_DIR="${1:?Usage: $0 <input_dir> <output_dir>}"
            OUTPUT_DIR="${2:?}"
            mkdir -p "$OUTPUT_DIR"
            echo "file,words,lines,unique" > "$OUTPUT_DIR/stats.csv"
            find "$INPUT_DIR" -name '*.txt' -print0 \
                | xargs -0 -P "$(nproc)" -I{} bash -c 'process_file "$@"' _ {} "$OUTPUT_DIR"
        """),
    ],
    "cpp": [
        textwrap.dedent("""\
            #include <vector>
            #include <algorithm>
            #include <optional>

            template <typename T>
            class MinHeap {
                std::vector<T> data_;

                void sift_up(int i) {
                    while (i > 0) {
                        int parent = (i - 1) / 2;
                        if (data_[i] >= data_[parent]) break;
                        std::swap(data_[i], data_[parent]);
                        i = parent;
                    }
                }

                void sift_down(int i) {
                    int n = data_.size();
                    while (true) {
                        int smallest = i, l = 2*i+1, r = 2*i+2;
                        if (l < n && data_[l] < data_[smallest]) smallest = l;
                        if (r < n && data_[r] < data_[smallest]) smallest = r;
                        if (smallest == i) break;
                        std::swap(data_[i], data_[smallest]);
                        i = smallest;
                    }
                }

            public:
                void push(T val) { data_.push_back(val); sift_up(data_.size()-1); }
                std::optional<T> pop() {
                    if (data_.empty()) return std::nullopt;
                    T top = data_[0];
                    data_[0] = data_.back();
                    data_.pop_back();
                    if (!data_.empty()) sift_down(0);
                    return top;
                }
                bool empty() const { return data_.empty(); }
            };
        """),
    ],
}

# ---------------------------------------------------------------------------
# Helper types
# ---------------------------------------------------------------------------


@dataclass
class CodeImageSpec:
    """Parameters for a single synthetic code image.

    Attributes:
        language: Programming language for syntax highlighting.
        snippet: Source code text.
        style: Pygments style name.
        font_path: Path to the monospace .ttf font.
        width_px: Image width in pixels.
        font_size: Font size in points.
        image_type: ``"screenshot"`` or ``"printed"`` rendering style.
    """

    language: str
    snippet: str
    style: str
    font_path: str
    width_px: int
    font_size: int
    image_type: str


@dataclass
class GenerationConfig:
    """Runtime configuration for the generation run.

    Attributes:
        n_positives: Total positive-class images to generate.
        n_screenshot: Subset of positives rendered as code screenshots.
        n_printed: Subset of positives rendered as printed-code-in-document style.
        n_negatives: Total negative-class records (sourced from L2 metadata).
        output_dir: Root directory for generated images.
        l2_dir: Directory for L2 metadata JSON files.
        base_data_root: Root for local dataset image directories.
        negative_sources: Ordered list of dataset names to pull negatives from.
        seed: Random seed for reproducibility.
        dry_run: If True, count records without generating images.
    """

    n_positives: int = 5000
    n_screenshot: int = 4000
    n_printed: int = 1000
    n_negatives: int = 5000
    output_dir: Path = Path("output/code_detection")
    l2_dir: Path = Path("/mnt/e/image_detection/metadata_registry/json")
    base_data_root: Path = Path("/mnt/e/image_detection/01_base_data")
    negative_sources: list[str] = field(
        default_factory=lambda: ["multimodal_textbook", "doclaynet"]
    )
    seed: int = 42
    dry_run: bool = False


# ---------------------------------------------------------------------------
# Split assignment
# ---------------------------------------------------------------------------


def _assign_split(index: int, total: int, fracs: tuple[float, float, float]) -> str:
    """Assign train/val/test split by index.

    Args:
        index: 0-based record index.
        total: Total number of records.
        fracs: (train, val, test) fractions.

    Returns:
        Split name.
    """
    train_end = int(total * fracs[0])
    val_end = train_end + int(total * fracs[1])
    if index < train_end:
        return "train"
    if index < val_end:
        return "val"
    return "test"


# ---------------------------------------------------------------------------
# Font loading
# ---------------------------------------------------------------------------


def _load_font(font_path: str, font_size: int) -> ImageFont.FreeTypeFont | None:
    """Load a FreeType font, returning None if unavailable.

    Args:
        font_path: Filesystem path to a .ttf or .otf file.
        font_size: Font size in points.

    Returns:
        Loaded font, or None if the path does not exist.
    """
    if not Path(font_path).exists():
        return None
    try:
        return ImageFont.truetype(font_path, font_size)
    except Exception:
        return None


def _available_mono_fonts() -> list[str]:
    """Return the subset of _MONO_FONTS that exist on disk.

    Returns:
        List of valid font paths.
    """
    return [p for p in _MONO_FONTS if Path(p).exists()]


# ---------------------------------------------------------------------------
# Code image rendering
# ---------------------------------------------------------------------------


def _render_screenshot(spec: CodeImageSpec, out_path: Path) -> bool:
    """Render a code screenshot using Pygments ImageFormatter.

    Args:
        spec: Image specification.
        out_path: Output path for the generated PNG.

    Returns:
        True on success.
    """
    try:
        lexer = get_lexer_by_name(spec.language, stripall=True)
        formatter = ImageFormatter(
            style=spec.style,
            font_name="DejaVu Sans Mono",
            font_size=spec.font_size,
            line_numbers=random.choice([True, False]),
            line_number_bg="#282828",
            image_pad=12,
        )
        png_data = highlight(spec.snippet, lexer, formatter)
        img = Image.open(__import__("io").BytesIO(png_data))
        # Resize to target width while preserving aspect
        if img.width != spec.width_px:
            ratio = spec.width_px / img.width
            new_h = max(int(img.height * ratio), 100)
            img = img.resize((spec.width_px, new_h), Image.LANCZOS)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, "PNG", optimize=False)
        return True
    except Exception as exc:
        logger.debug("Screenshot render failed for %s: %s", out_path, exc)
        return False


def _render_printed_code(spec: CodeImageSpec, out_path: Path) -> bool:
    """Render code embedded in a document-style page (white/cream background).

    Simulates a technical manual, academic paper, or textbook that includes
    a code listing within surrounding paragraph text.

    Args:
        spec: Image specification.
        out_path: Output path for the generated PNG.

    Returns:
        True on success.
    """
    try:
        font = _load_font(spec.font_path, spec.font_size)
        if font is None:
            font = ImageFont.load_default()

        bg_colors = ["#FFFFFF", "#FFFEF8", "#F8F8F0", "#FAFAF7"]
        bg = random.choice(bg_colors)
        code_bg = random.choice(["#F4F4F4", "#F0F0F0", "#EFEFEF"])
        text_color = "#1A1A1A"
        code_color = "#333333"

        lines = spec.snippet.split("\n")
        img_w = spec.width_px
        line_h = spec.font_size + 4
        padding = 32
        code_block_h = len(lines) * line_h + padding * 2
        # Add header/footer paragraph margins
        header_h = 60
        footer_h = 40
        img_h = header_h + code_block_h + footer_h + padding * 2

        img = Image.new("RGB", (img_w, img_h), bg)
        draw = ImageDraw.Draw(img)

        # Header: fake paragraph lines
        for row_y in range(12, header_h - 8, 14):
            line_w = random.randint(img_w // 3, int(img_w * 0.85))
            draw.rectangle(
                [padding, row_y, padding + line_w, row_y + 8], fill="#CCCCCC"
            )

        # Code block background
        block_top = header_h + padding
        draw.rectangle(
            [padding, block_top, img_w - padding, block_top + code_block_h],
            fill=code_bg,
        )
        # Left accent bar
        draw.rectangle(
            [padding, block_top, padding + 3, block_top + code_block_h], fill="#4A90D9"
        )

        # Code text
        for idx, line in enumerate(lines):
            y = block_top + padding + idx * line_h
            draw.text((padding + 12, y), line, font=font, fill=code_color)

        # Footer: fake paragraph lines
        footer_top = block_top + code_block_h + 12
        for row_y in range(footer_top, footer_top + footer_h - 8, 14):
            line_w = random.randint(img_w // 4, int(img_w * 0.9))
            draw.rectangle(
                [padding, row_y, padding + line_w, row_y + 8], fill="#CCCCCC"
            )

        out_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_path, "PNG", optimize=True)
        return True
    except Exception as exc:
        logger.debug("Printed-code render failed for %s: %s", out_path, exc)
        return False


# ---------------------------------------------------------------------------
# Spec sampling
# ---------------------------------------------------------------------------


def _sample_spec(
    rng: random.Random,
    image_type: str,
    mono_fonts: list[str],
) -> CodeImageSpec:
    """Sample a random CodeImageSpec.

    Args:
        rng: Random state.
        image_type: ``"screenshot"`` or ``"printed"``.
        mono_fonts: Available monospace font paths.

    Returns:
        Sampled spec.
    """
    lang = rng.choice(_LANGUAGES)
    snippets = _SNIPPETS.get(lang, _SNIPPETS["python"])
    snippet = rng.choice(snippets)
    if image_type == "screenshot":
        style = rng.choice(_DARK_STYLES + _LIGHT_STYLES)
    else:
        style = rng.choice(_LIGHT_STYLES)
    width_px, font_size = rng.choice(_DPI_CONFIGS)
    font_path = rng.choice(mono_fonts) if mono_fonts else _MONO_FONTS[0]
    return CodeImageSpec(
        language=lang,
        snippet=snippet,
        style=style,
        font_path=font_path,
        width_px=width_px,
        font_size=font_size,
        image_type=image_type,
    )


# ---------------------------------------------------------------------------
# Positive generation
# ---------------------------------------------------------------------------


def _generate_positives(
    cfg: GenerationConfig,
    rng: random.Random,
) -> list[dict[str, Any]]:
    """Generate synthetic positive-class code images.

    Args:
        cfg: Generation configuration.
        rng: Random state.

    Returns:
        List of manifest records.
    """
    mono_fonts = _available_mono_fonts()
    if not mono_fonts:
        logger.warning("No monospace fonts found — using Pillow default font")

    total = cfg.n_screenshot + cfg.n_printed
    specs: list[tuple[CodeImageSpec, str]] = []  # (spec, filename_stem)
    for idx in range(total):
        if idx < cfg.n_screenshot:
            img_type = "screenshot"
            prefix = "code_ss"
        else:
            img_type = "printed"
            prefix = "code_pr"
        spec = _sample_spec(rng, img_type, mono_fonts)
        specs.append((spec, f"{prefix}_{idx:05d}_{spec.language}_{spec.style[:8]}"))

    records: list[dict[str, Any]] = []
    for idx, (spec, stem) in enumerate(tqdm(specs, desc="Generating positive images")):
        rel_path = f"positive/{spec.language}/{stem}.png"
        out_path = cfg.output_dir / rel_path

        if not cfg.dry_run:
            success = (
                _render_screenshot(spec, out_path)
                if spec.image_type == "screenshot"
                else _render_printed_code(spec, out_path)
            )
            if not success:
                continue

        records.append(
            {
                "image_path": str(rel_path),
                "source_dataset": "synthetic_code",
                "code_present": True,
                "code_confidence": 1.0,
                "language": spec.language,
                "theme": spec.style,
                "split": _assign_split(idx, total, _SPLIT_FRACS),
                "label_method": "synthetic_param",
            }
        )

    return records


# ---------------------------------------------------------------------------
# Negative sourcing
# ---------------------------------------------------------------------------


def _load_l2_samples(l2_dir: Path, dataset_name: str) -> list[dict[str, Any]]:
    """Load L2 metadata samples for a dataset.

    Args:
        l2_dir: Directory with ``{name}_metadata.json`` files.
        dataset_name: Canonical dataset name.

    Returns:
        List of sample dicts.  Empty if file not found.
    """
    meta_path = l2_dir / f"{dataset_name}_metadata.json"
    if not meta_path.exists():
        logger.warning("L2 metadata not found: %s", meta_path)
        return []
    with open(meta_path) as fh:
        data = json.load(fh)
    return data.get("samples", [])


def _gather_negatives(
    cfg: GenerationConfig,
    rng: random.Random,
) -> list[dict[str, Any]]:
    """Gather negative-class records from L2 metadata sources.

    Filters to samples with ``has_code=False`` where the field exists.
    Falls back to including all samples if the field is absent (dataset-class
    label for born-digital non-code sources like DocLayNet).

    Args:
        cfg: Generation configuration.
        rng: Random state.

    Returns:
        List of manifest records.
    """
    all_neg: list[dict[str, Any]] = []
    per_source = cfg.n_negatives // max(len(cfg.negative_sources), 1)

    for ds_name in cfg.negative_sources:
        # Dataset-specific subdir mapping
        subdir_map: dict[str, str] = {
            "multimodal_textbook": "educational/multimodal_textbook",
            "doclaynet": "layout/doclaynet",
            "mathverse": "formulas/mathverse",
            "synth-multiscript-v3": "language/synth-multiscript-v3",
        }
        base_subdir = subdir_map.get(ds_name, ds_name)
        base_dir = cfg.base_data_root / base_subdir

        samples = _load_l2_samples(cfg.l2_dir, ds_name)
        if not samples:
            logger.warning("No L2 metadata for %s — skipping negatives", ds_name)
            continue

        # Filter: has_code=False (or field absent → no code expected by design)
        filtered: list[dict[str, Any]] = []
        for s in samples:
            enr = s.get("enrichments", {}).get("versions", [{}])[-1].get("data", {})
            has_code = enr.get("has_code")
            if has_code is True:
                continue  # skip code pages
            filtered.append(s)

        # Pre-sample to avoid O(N) disk scans on large datasets
        if len(filtered) > per_source * 4:
            filtered = rng.sample(filtered, per_source * 4)

        taken = 0
        for idx, sample in enumerate(filtered):
            if taken >= per_source:
                break
            original_path = sample.get("source", {}).get("original_path", "")
            raw_split = sample.get("source", {}).get("split", "train")
            if not original_path:
                continue

            # If directory exists locally, check file existence
            if base_dir.exists():
                if not (base_dir / original_path).exists():
                    continue
                img_path_rel = str(Path(base_subdir) / original_path)
            else:
                # GCS-only — include path as-is; training job handles retrieval
                img_path_rel = str(Path(base_subdir) / original_path)

            split_map = {"validation": "val", "valid": "val", "testing": "test"}
            norm_split = split_map.get(raw_split.lower(), raw_split.lower())
            if norm_split not in ("train", "val", "test"):
                norm_split = "train"

            all_neg.append(
                {
                    "image_path": img_path_rel,
                    "source_dataset": ds_name,
                    "code_present": False,
                    "code_confidence": 0.0,
                    "language": None,
                    "theme": None,
                    "split": norm_split,
                    "label_method": "l2_metadata"
                    if base_dir.exists()
                    else "dataset_class",
                }
            )
            taken += 1

    return all_neg


# ---------------------------------------------------------------------------
# Manifest writing
# ---------------------------------------------------------------------------


def _print_summary(records: list[dict[str, Any]], verbose: bool) -> None:
    """Print dataset statistics.

    Args:
        records: All assembled records.
        verbose: Print per-dataset breakdown.
    """
    total = len(records)
    positive = sum(1 for r in records if r["code_present"])
    negative = total - positive
    per_ds: dict[str, int] = {}
    splits: dict[str, int] = {}
    langs: dict[str, int] = {}
    for r in records:
        per_ds[r["source_dataset"]] = per_ds.get(r["source_dataset"], 0) + 1
        splits[r["split"]] = splits.get(r["split"], 0) + 1
        if r["language"]:
            langs[r["language"]] = langs.get(r["language"], 0) + 1

    click.echo("\nDataset summary:")
    click.echo(f"  Total records  : {total:>7,}")
    click.echo(
        f"  Positive (code): {positive:>7,}  ({100 * positive / max(total, 1):.1f}%)"
    )
    click.echo(
        f"  Negative       : {negative:>7,}  ({100 * negative / max(total, 1):.1f}%)"
    )
    click.echo("  Splits: " + ", ".join(f"{k}={v}" for k, v in sorted(splits.items())))

    if verbose:
        click.echo("\n  Per-source:")
        for ds, cnt in sorted(per_ds.items(), key=lambda x: -x[1]):
            click.echo(f"    {ds:<28} {cnt:>6,}")
        click.echo("\n  Language distribution (positives):")
        for lang, cnt in sorted(langs.items(), key=lambda x: -x[1]):
            click.echo(f"    {lang:<16} {cnt:>6,}")

    # Go/No-Go
    if positive < 4000:
        click.echo(f"\n  WARNING: positive class {positive:,} < 4,000 minimum.")
    if negative < 2000:
        click.echo(
            f"  WARNING: negative class {negative:,} < 2,000 minimum.\n"
            "  Provide --negatives-from datasets or increase --negatives.",
        )
    if positive >= 4000 and negative >= 2000:
        click.echo("\n  GO: Code detection dataset meets 4K+/2K+ class targets.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.command()
@click.option(
    "--positives",
    default=5000,
    show_default=True,
    help="Number of positive-class (code present) images to generate.",
)
@click.option(
    "--screenshot-fraction",
    default=0.80,
    show_default=True,
    help="Fraction of positives rendered as code screenshots (vs printed-code style).",
)
@click.option(
    "--negatives",
    default=5000,
    show_default=True,
    help="Number of negative-class records to pull from L2 metadata sources.",
)
@click.option(
    "--negatives-from",
    multiple=True,
    default=["multimodal_textbook", "doclaynet"],
    show_default=True,
    help="Dataset names to use as negative sources (ordered by preference).",
)
@click.option(
    "--l2-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("/mnt/e/image_detection/metadata_registry/json"),
    show_default=True,
    help="Directory with L2 {dataset}_metadata.json files.",
)
@click.option(
    "--base-data-root",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("/mnt/e/image_detection/01_base_data"),
    show_default=True,
    help="Root directory for local dataset images.",
)
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=Path("/mnt/e/image_detection/03_training_datasets/code_detection"),
    show_default=True,
    help="Output directory for generated images.",
)
@click.option(
    "--manifest",
    "manifest_path",
    type=click.Path(path_type=Path),
    default=Path("code_detection_manifest.jsonl"),
    show_default=True,
    help="Output JSONL manifest path.",
)
@click.option(
    "--seed",
    default=42,
    show_default=True,
    help="Random seed for reproducibility.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Count records without generating images or writing manifest.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Print per-source and per-language breakdown.",
)
def main(
    positives: int,
    screenshot_fraction: float,
    negatives: int,
    negatives_from: tuple[str, ...],
    l2_dir: Path,
    base_data_root: Path,
    output_dir: Path,
    manifest_path: Path,
    seed: int,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Generate the code-detection training dataset.

    Generates synthetic code images (positive class) using PIL and Pygments,
    and sources negative-class records from L2 metadata for non-code datasets.

    Example::

        uv run python scripts/generate_code_detection_dataset.py \\
            --positives 5000 --negatives 5000 \\
            --negatives-from multimodal_textbook \\
            --output-dir /mnt/e/image_detection/03_training_datasets/code_detection \\
            --manifest code_detection_manifest.jsonl
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    rng = random.Random(seed)

    n_screenshot = int(positives * screenshot_fraction)
    n_printed = positives - n_screenshot

    cfg = GenerationConfig(
        n_positives=positives,
        n_screenshot=n_screenshot,
        n_printed=n_printed,
        n_negatives=negatives,
        output_dir=output_dir,
        l2_dir=l2_dir,
        base_data_root=base_data_root,
        negative_sources=list(negatives_from),
        seed=seed,
        dry_run=dry_run,
    )

    click.echo(
        f"Generating {n_screenshot} code screenshots + {n_printed} printed-code images…"
    )
    positive_records = _generate_positives(cfg, rng)
    click.echo(f"  Generated {len(positive_records):,} positive records.")

    click.echo(f"Gathering {negatives:,} negative records from {list(negatives_from)}…")
    negative_records = _gather_negatives(cfg, rng)
    click.echo(f"  Gathered {len(negative_records):,} negative records.")

    all_records = positive_records + negative_records
    rng.shuffle(all_records)

    _print_summary(all_records, verbose=verbose)

    if dry_run:
        click.echo("\nDry-run complete — no files written.")
        return

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w") as fh:
        fh.writelines(json.dumps(record) + "\n" for record in all_records)
    click.echo(f"\nWrote {len(all_records):,} records → {manifest_path}")


if __name__ == "__main__":
    main()
