"""
Evaluation metrics and simple reporting for production forecasts.
"""

from typing import Dict
import numpy as np
import pandas as pd


def mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Absolute Percentage Error (ignores zeros)."""
    mask = y_true > 0
    if mask.sum() == 0:
        return np.nan
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Root Mean Squared Error."""
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def evaluate_forecast(result: Dict) -> Dict:
    """
    Compute evaluation metrics for a single well forecast result.
    """
    if "error" in result:
        return {"well": result["well"], "error": result["error"]}

    metrics = {
        "well": result["well"],
        "model": result["model"],
        "r2_train": result["r2_train"],
        "qi": result["qi"],
        "di": result["di"],
        "b": result["b"],
    }

    if len(result.get("q_test", [])) > 0:
        metrics["mape_test"] = mape(result["q_test"], result["q_test_pred"])
        metrics["rmse_test"] = rmse(result["q_test"], result["q_test_pred"])
        metrics["n_test"] = len(result["q_test"])
    else:
        metrics["mape_test"] = np.nan
        metrics["rmse_test"] = np.nan
        metrics["n_test"] = 0

    return metrics


def summarise_results(all_results: Dict[str, Dict]) -> pd.DataFrame:
    """Create a summary table of metrics for all wells."""
    rows = [evaluate_forecast(res) for res in all_results.values()]
    summary = pd.DataFrame(rows)
    if "r2_train" in summary.columns:
        summary = summary.sort_values(
            "r2_train", ascending=False
        ).reset_index(drop=True)
    return summary
