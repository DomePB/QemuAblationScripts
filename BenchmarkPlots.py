"""
benchmark_plots.py
==================
Visualisierung von QEMU Ablation Study Benchmarks.

Struktur:
  - load_data()          → Daten laden & filtern
  - PLOT 1: Box/Violin   → pro Benchmark × Build
  - PLOT 2: Grouped Bar  → pro Benchmark, Median (ohne Fehlerbalken)

Verwendung:
  python benchmark_plots.py --csv results.csv --out ./plots
"""

import os
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
from scipy import stats

# ── Konfiguration ──────────────────────────────────────────────────────────────

# Reihenfolge & Anzeigename der Builds (anpassen nach Bedarf)
BUILD_LABELS: dict[str, str] = {
    "build-default":        "Default",
    "build-noOptimization": "No Opt",
    "build-OMaskFix":       "OMaskFix",
    "build-addPatch":       "AddPatch",
}

# Farben pro Build (konsistent über alle Plots)
BUILD_COLORS: dict[str, str] = {
    "build-default":        "#4C72B0",
    "build-noOptimization": "#DD8452",
    "build-OMaskFix":       "#55A868",
    "build-addPatch":       "#C44E52",
}

OUTPUT_DPI = 150
OUTPUT_FORMAT = "pdf"   # "pdf" für LaTeX, "png" für schnellen Preview


# ── Datenladen ─────────────────────────────────────────────────────────────────

def extract_build_key(build_path: str) -> str:
    """Extrahiert den Build-Schlüssel aus dem Pfad, z.B. 'build-default'."""
    parts = Path(build_path.rstrip("/")).parts
    for part in reversed(parts):
        if part.startswith("build-"):
            return part
    return build_path  # Fallback: roher Pfad


def load_data(csv_path: str) -> pd.DataFrame:
    """
    Lädt die CSV, filtert auf return_code == 0, entfernt doppelte run_ids
    und normalisiert Build-Namen.
    """
    col_names = ["run_id", "build", "binary", "execution_time", "return_code"]
    with open(csv_path, "r") as f:
        first_line = f.readline()
    has_header = "run_id" in first_line or "execution_time" in first_line
    df = pd.read_csv(csv_path, header=0 if has_header else None, names=None if has_header else col_names)

    # Nur erfolgreiche Runs
    df = df[df["return_code"] == 0].copy()

    # ── Duplikate entfernen: gleiche run_id → ersten Eintrag behalten ──
    before = len(df)
    df = df.drop_duplicates(subset="run_id", keep="first")
    removed = before - len(df)
    if removed:
        print(f"  Duplikate entfernt: {removed} Zeilen mit doppelter run_id")

    # Build-Key aus Pfad extrahieren
    df["build_key"] = df["build"].apply(extract_build_key)

    # Menschenlesbarer Anzeigename (Fallback: build_key selbst)
    df["build_label"] = df["build_key"].map(BUILD_LABELS).fillna(df["build_key"])

    # Farbzuweisung
    df["color"] = df["build_key"].map(BUILD_COLORS).fillna("#888888")

    return df


def get_ordered_builds(df: pd.DataFrame) -> list[str]:
    """Gibt Builds in der definierten Reihenfolge zurück."""
    defined = list(BUILD_LABELS.keys())
    present = df["build_key"].unique().tolist()
    ordered = [b for b in defined if b in present]
    # Unbekannte Builds hinten anhängen
    ordered += [b for b in present if b not in ordered]
    return ordered


# ── Plot-Hilfsfunktionen ───────────────────────────────────────────────────────

def save_fig(fig: plt.Figure, out_dir: str, filename: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{filename}.{OUTPUT_FORMAT}")
    fig.savefig(path, dpi=OUTPUT_DPI, bbox_inches="tight")
    print(f"  Gespeichert: {path}")
    plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════════
# PLOT 1 – Box-/Violin-Plot: pro Benchmark × Build
# ══════════════════════════════════════════════════════════════════════════════

def plot_violin_per_benchmark(df: pd.DataFrame, out_dir: str) -> None:
    """
    Pro Benchmark eine eigene Abbildung.
    Jeder Build ist eine Gruppe: Violin (Verteilung) + Box (IQR) + Stripplot (Einzelwerte).
    """
    benchmarks = df["binary"].unique()
    builds = get_ordered_builds(df)

    for benchmark in benchmarks:
        bdf = df[df["binary"] == benchmark]

        # Daten pro Build sammeln
        groups = []
        labels = []
        colors = []
        for build_key in builds:
            subset = bdf[bdf["build_key"] == build_key]["execution_time"].values
            if len(subset) > 0:
                groups.append(subset)
                labels.append(BUILD_LABELS.get(build_key, build_key))
                colors.append(BUILD_COLORS.get(build_key, "#888888"))

        if not groups:
            continue

        fig, ax = plt.subplots(figsize=(max(6, len(groups) * 2), 5))

        positions = np.arange(1, len(groups) + 1)

        # ── Violin ──
        if any(len(g) >= 3 for g in groups):  # Violin braucht mind. 3 Punkte
            vp = ax.violinplot(
                [g if len(g) >= 3 else np.repeat(g, 3) for g in groups],
                positions=positions,
                showmedians=False,
                showextrema=False,
                widths=0.6,
            )
            for body, color in zip(vp["bodies"], colors):
                body.set_facecolor(color)
                body.set_alpha(0.35)
                body.set_edgecolor(color)
                body.set_linewidth(1.2)

        # ── Box (IQR + Median + Whisker) ──
        bp = ax.boxplot(
            groups,
            positions=positions,
            widths=0.25,
            patch_artist=True,
            medianprops=dict(color="white", linewidth=2.0),
            whiskerprops=dict(linewidth=1.2),
            capprops=dict(linewidth=1.8),
            flierprops=dict(marker="x", markersize=0, linestyle="none", alpha=0.0),
            manage_ticks=False,
        )
        for patch, color in zip(bp["boxes"], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.85)
        for whisker, color in zip(
            [w for pair in zip(bp["whiskers"][::2], bp["whiskers"][1::2]) for w in pair],
            [c for c in colors for _ in range(2)],
        ):
            whisker.set_color(color)
        for cap, color in zip(
            [c for pair in zip(bp["caps"][::2], bp["caps"][1::2]) for c in pair],
            [c for c in colors for _ in range(2)],
        ):
            cap.set_color(color)

        # ── Einzelne Datenpunkte (Jitter) ──
        rng = np.random.default_rng(42)
        for pos, group, color in zip(positions, groups, colors):
            jitter = rng.uniform(-0.08, 0.08, size=len(group))
            ax.scatter(
                pos + jitter, group,
                color=color, s=30, zorder=5, alpha=0.8, linewidths=0.5,
                edgecolors="white",
            )

        # ── Mittelwert-Marker ──
        for pos, group, color in zip(positions, groups, colors):
            ax.scatter(
                pos, np.mean(group),
                marker="D", color="white", s=40, zorder=6,
                edgecolors=color, linewidths=1.5,
            )

        ax.set_xticks(positions)
        ax.set_xticklabels(labels, fontsize=11)
        ax.set_ylabel("Execution Time (s)", fontsize=11)
        ax.set_title(f"Benchmark: {benchmark}", fontsize=13, fontweight="bold")
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        ax.grid(axis="y", which="minor", linestyle=":", alpha=0.2)
        ax.set_axisbelow(True)

        # Legende: ◆ = Mittelwert
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker="D", color="gray", markerfacecolor="white",
                   markersize=7, label="Mittelwert", linestyle="None"),
            Line2D([0], [0], color="white", linewidth=2, label="Median",
                   markerfacecolor="white"),
        ]
        ax.legend(handles=legend_elements, fontsize=9, loc="upper right")

        fig.tight_layout()
        safe_name = benchmark.replace("/", "_").replace(" ", "_")
        save_fig(fig, out_dir, f"violin_{safe_name}")


# ══════════════════════════════════════════════════════════════════════════════
# PLOT 2 – Grouped Bar Chart: pro Benchmark, Median (ohne Fehlerbalken)
# ══════════════════════════════════════════════════════════════════════════════

def plot_grouped_bar(df: pd.DataFrame, out_dir: str) -> None:
    """
    Ein Plot mit allen Benchmarks nebeneinander.
    Pro Benchmark: ein Balken pro Build, Median ohne Fehlerbalken.
    Unterschiede werden durch %-Abweichung vom schnellsten Build annotiert.
    """
    benchmarks = sorted(df["binary"].unique())
    builds = get_ordered_builds(df)
    n_builds = len(builds)
    n_benchmarks = len(benchmarks)

    bar_width = 0.8 / n_builds
    fig, axes = plt.subplots(
        1, n_benchmarks,
        figsize=(max(8, n_benchmarks * n_builds * 1.8), 6),
        sharey=False,
    )
    if n_benchmarks == 1:
        axes = [axes]

    for ax, benchmark in zip(axes, benchmarks):
        bdf = df[df["binary"] == benchmark]
        offsets = np.linspace(
            -(n_builds - 1) / 2 * bar_width,
             (n_builds - 1) / 2 * bar_width,
            n_builds,
        )

        # Mediane vorberechnen für %-Vergleich
        medians = {}
        for build_key in builds:
            subset = bdf[bdf["build_key"] == build_key]["execution_time"].values
            if len(subset) > 0:
                medians[build_key] = np.median(subset)

        best_median = min(medians.values()) if medians else 1.0

        bars_drawn = []
        for offset, build_key in zip(offsets, builds):
            if build_key not in medians:
                continue

            median = medians[build_key]
            color = BUILD_COLORS.get(build_key, "#888888")
            label = BUILD_LABELS.get(build_key, build_key)

            bar = ax.bar(
                offset, median,
                width=bar_width * 0.88,
                color=color,
                alpha=0.90,
                label=label,
                zorder=3,
                linewidth=1.2,
                edgecolor="white",
            )
            bars_drawn.append((offset, median, color, build_key))

            # ── Annotation über dem Balken: Wert + %-Overhead in einem Text ──
            pct = (median / best_median - 1.0) * 100
            if pct > 0.05:
                label_text = f"{median:.2f}s\n+{pct:.1f}%"
                fontsizes = [8, 7.5]
                colors_txt = [color, "#666666"]
                styles = ["normal", "italic"]
            else:
                label_text = f"{median:.2f}s"
                fontsizes = [8]
                colors_txt = [color]
                styles = ["normal"]

            # Mehrzeiligen Text zeilenweise mit unterschiedlichem Stil zeichnen
            lines = label_text.split("\n")
            # Gesamthöhe schätzen: jede Zeile ~0.013 * y_range
            y_range_est = max(medians.values()) * 1.22 - min(medians.values()) * 0.92
            line_h = y_range_est * 0.045
            y_start = median + line_h * 0.3
            for i, (line, fs, fc, st) in enumerate(zip(lines, fontsizes, colors_txt, styles)):
                ax.text(
                    offset, y_start + i * line_h,
                    line,
                    ha="center", va="bottom",
                    fontsize=fs, fontweight="bold" if i == 0 else "normal",
                    color=fc, style=st,
                )

        # ── Horizontale Referenzlinie beim schnellsten Median ──
        ax.axhline(best_median, color="#333333", linewidth=0.8,
                   linestyle="--", alpha=0.5, zorder=2)

        ax.set_title(benchmark, fontsize=11, fontweight="bold")
        ax.set_ylabel("Execution Time (s)", fontsize=10)
        ax.set_xticks([])
        ax.grid(axis="y", linestyle="--", alpha=0.35)
        ax.yaxis.set_minor_locator(ticker.AutoMinorLocator())
        ax.grid(axis="y", which="minor", linestyle=":", alpha=0.18)
        ax.set_axisbelow(True)

        # Y-Achse: Puffer nach oben für Beschriftungen
        y_max = ax.get_ylim()[1]
        ax.set_ylim(0, y_max * 1.22)

        # Y-Achse beginnt knapp unter dem kleinsten Median für bessere Lesbarkeit
        if medians:
            y_min_data = min(medians.values())
            ax.set_ylim(y_min_data * 0.92, y_max * 1.22)

    # Gemeinsame Legende
    handles, lbls = axes[0].get_legend_handles_labels()
    seen = {}
    for h, l in zip(handles, lbls):
        seen[l] = h
    fig.legend(
        seen.values(), seen.keys(),
        loc="upper center",
        ncol=n_builds,
        fontsize=10,
        title="Build  (+x% = Overhead gegenüber schnellstem Build)",
        title_fontsize=9,
        bbox_to_anchor=(0.5, 1.02),
    )

    fig.suptitle("Execution Time – Median pro Build & Benchmark",
                 fontsize=13, fontweight="bold", y=1.08)
    fig.tight_layout()
    save_fig(fig, out_dir, "grouped_bar")


def main() -> None:
    from datetime import datetime

    script_dir = Path(__file__).parent
    csv_path = script_dir / "benchmark_results.csv"

    if not csv_path.exists():
        print(f"FEHLER: Keine 'benchmark_results.csv' in {script_dir} gefunden.")
        return

    # Ausgabe-Ordner mit Zeitstempel
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_dir = str(script_dir / f"BenchmarkPlots_{timestamp}")

    print(f"Lade Daten aus: {csv_path}")
    df = load_data(str(csv_path))

    print(f"  {len(df)} Runs geladen")
    print(f"  Builds:      {df['build_key'].unique().tolist()}")
    print(f"  Benchmarks:  {df['binary'].unique().tolist()}")
    print(f"  Output:      {out_dir}")
    print()

    print("Plot 1: Violin-/Box-Plot pro Benchmark …")
    plot_violin_per_benchmark(df, out_dir)

    print("Plot 2: Grouped Bar Chart …")
    plot_grouped_bar(df, out_dir)

    print("\nFertig!")


if __name__ == "__main__":
    main()