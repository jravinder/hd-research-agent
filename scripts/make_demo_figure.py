"""Generate a synthetic 'HD clinical results' figure for the demo video.

We don't want to ship a real PMC figure (network fragility + ambiguous rights),
and we don't want to ship a real medical scan (clinical territory). A clearly
synthetic Kaplan-Meier-ish survival curve serves the multimodal demo perfectly:
Gemma 4 should describe it and pull off the axis labels + survival fractions.

Run:
    python3 scripts/make_demo_figure.py
Writes media/demo_figure.png.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


REPO = Path(__file__).resolve().parent.parent
MEDIA = REPO / "media"
MEDIA.mkdir(exist_ok=True)


def main() -> None:
    rng = np.random.default_rng(7)
    months = np.linspace(0, 36, 100)

    # Synthetic step-down survival curves
    placebo = np.maximum(0.10, 1.0 - months / 36 * 0.85 + rng.normal(0, 0.01, months.size))
    placebo = np.minimum.accumulate(placebo)

    treated = np.maximum(0.40, 1.0 - months / 36 * 0.55 + rng.normal(0, 0.01, months.size))
    treated = np.minimum.accumulate(treated)

    fig, ax = plt.subplots(figsize=(7.5, 4.5), dpi=160)
    ax.plot(months, treated, color="#92400E", linewidth=2.4,
            label="HTT-lowering ASO (n=24)")
    ax.plot(months, placebo, color="#9CA3AF", linewidth=2.4, linestyle="--",
            label="Placebo (n=22)")

    # Censor marks
    for x in [6, 12, 18, 24, 30]:
        y_t = float(np.interp(x, months, treated))
        y_p = float(np.interp(x, months, placebo))
        ax.plot([x], [y_t], marker="|", color="#92400E", markersize=10, mew=1.8)
        ax.plot([x], [y_p], marker="|", color="#9CA3AF", markersize=10, mew=1.8)

    ax.set_xlim(0, 36)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Months from baseline", fontsize=11)
    ax.set_ylabel("Survival probability (motor decline-free)", fontsize=11)
    ax.set_title("SYNTHETIC DEMO — HTT-lowering ASO vs placebo, motor decline-free survival\n"
                 "(NOT real clinical data — for hackathon multimodal demo only)",
                 fontsize=11, color="#1f2937", pad=12)
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(loc="lower left", frameon=False, fontsize=10)

    # Annotations carrying real-looking numerics so the model has things to extract
    ax.annotate("HR = 0.44 (95% CI 0.21 – 0.92)\np = 0.028 (log-rank)",
                xy=(20, 0.65), xytext=(22, 0.85),
                arrowprops={"arrowstyle": "-", "color": "#374151", "lw": 0.8},
                fontsize=9, color="#374151")
    ax.annotate("ΔSurvival at 24 mo: +28 pp",
                xy=(24, float(np.interp(24, months, treated)) - 0.05),
                fontsize=9, color="#92400E")

    fig.tight_layout()
    out = MEDIA / "demo_figure.png"
    fig.savefig(out, dpi=160, bbox_inches="tight")
    print(f"saved: {out}")


if __name__ == "__main__":
    main()
