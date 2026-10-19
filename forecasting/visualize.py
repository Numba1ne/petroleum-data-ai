"""
Visualization helpers for production forecasting results.
"""

from pathlib import Path
from typing import Dict
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parents[1]
PLOT_DIR = BASE_DIR / "reports" / "forecast_plots"
PLOT_DIR.mkdir(parents=True, exist_ok=True)


def plot_well_forecast(
    result: Dict, save: bool = True, show: bool = False
) -> None:
    """
    Plot actual production, model fit, and future forecast for one well.
    """
    if "error" in result or "forecast_df" not in result:
        print(
            f"Skipping plot for {result.get('well')}: {result.get('error', 'No forecast data')}"
        )
        return

    df = result["forecast_df"].copy()
    well = result["well"]
    model = result["model"]
    r2 = result.get("r2_train", float("nan"))

    fig, ax = plt.subplots(figsize=(12, 6))

    # Historical actual
    hist = df[df["segment"] == "history"]
    ax.scatter(
        hist["date"],
        hist["actual_oil"],
        s=12,
        alpha=0.5,
        color="steelblue",
        label="Actual Oil Rate",
    )

    # Model fit (history)
    ax.plot(
        hist["date"],
        hist["predicted_oil"],
        color="darkorange",
        linewidth=2,
        label=f"Model Fit ({model})",
    )

    # Future forecast
    fut = df[df["segment"] == "forecast"]
    ax.plot(
        fut["date"],
        fut["predicted_oil"],
        color="crimson",
        linewidth=2,
        linestyle="--",
        label="Forecast",
    )

    # Vertical line separating history and forecast
    if not hist.empty and not fut.empty:
        split_date = hist["date"].iloc[-1]
        ax.axvline(split_date, color="gray", linestyle=":", alpha=0.7)
        ax.text(
            split_date,
            ax.get_ylim()[1] * 0.95,
            " Forecast →",
            color="gray",
            fontsize=9,
            va="top",
        )

    ax.set_title(
        f"{well}\nDecline Model: {model}  |  Train R² = {r2:.3f}",
        fontsize=13,
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Oil Rate (Sm³/day)")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    if save:
        safe_name = well.replace("/", "").replace(" ", "")
        out_path = PLOT_DIR / f"{safe_name}_forecast.png"
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        print(f"Saved: {out_path}")

    if show:
        plt.show()
    else:
        plt.close(fig)


def plot_multiple_wells(results: Dict[str, Dict], max_wells: int = 6) -> None:
    """Generate plots for several wells."""
    count = 0
    for well, res in results.items():
        if "error" in res:
            continue
        plot_well_forecast(res, save=True, show=False)
        count += 1
        if count >= max_wells:
            break
    print(f"\nGenerated {count} forecast plots in {PLOT_DIR}")
