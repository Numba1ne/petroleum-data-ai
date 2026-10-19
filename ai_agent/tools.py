"""
Tools that the AI agent can call.
Each function returns clean, serialisable data (dict / list).
"""

from typing import Dict, List, Optional

from anomaly_detection.pipeline import detect_well_anomalies
from anomaly_detection.scoring import summarise_well_anomalies
from forecasting.forecast import forecast_well
from forecasting.evaluate import evaluate_forecast
from well_performance.scorecard import build_scorecard
from well_performance.utils import load_producer_df


def get_producer_list() -> List[str]:
    """Return sorted list of producer well names."""
    df = load_producer_df()
    return sorted(df["well_bore_code"].unique().tolist())


def get_well_summary(well: str) -> Dict:
    """Basic production summary for one well."""
    df = load_producer_df()
    w = df[df["well_bore_code"] == well]
    if w.empty:
        return {"error": f"Well {well} not found"}

    cum_oil = w["bore_oil_vol"].sum()
    cum_gas = w["bore_gas_vol"].sum()
    cum_water = w["bore_wat_vol"].sum()
    liquid = cum_oil + cum_water
    avg_wc = (cum_water / liquid * 100) if liquid > 0 else None
    avg_gor = (cum_gas / cum_oil) if cum_oil > 0 else None

    recent = w.tail(90)
    return {
        "well": well,
        "days": len(w),
        "cum_oil_sm3": round(cum_oil, 1),
        "cum_gas_sm3": round(cum_gas, 1),
        "cum_water_sm3": round(cum_water, 1),
        "avg_water_cut_pct": round(avg_wc, 2) if avg_wc is not None else None,
        "avg_gor": round(avg_gor, 1) if avg_gor is not None else None,
        "recent_90d_avg_oil": round(recent["bore_oil_vol"].mean(), 1),
        "first_date": str(w["dateprd"].min().date()),
        "last_date": str(w["dateprd"].max().date()),
    }


def run_forecast(well: str, horizon_days: int = 180) -> Dict:
    """Run decline-curve forecast and return key results."""
    result = forecast_well(well, forecast_days=horizon_days)
    if "error" in result:
        return result

    metrics = evaluate_forecast(result)
    fut = result["forecast_df"]
    future = fut[fut["segment"] == "forecast"]

    return {
        "well": well,
        "model": result["model"],
        "qi": round(result["qi"], 1),
        "di": round(result["di"], 6),
        "b": result["b"],
        "r2_train": round(result["r2_train"], 3),
        "mape_test": round(metrics.get("mape_test", float("nan")), 1),
        "forecast_horizon_days": horizon_days,
        "forecast_end_date": str(future["date"].iloc[-1].date()) if len(future) else None,
        "final_predicted_rate": round(future["predicted_oil"].iloc[-1], 1) if len(future) else None,
    }


def get_anomalies(well: str, include_residual: bool = True) -> Dict:
    """Run anomaly detection and return summary + top events."""
    flags = detect_well_anomalies(well, include_residual=include_residual)
    summary = summarise_well_anomalies(flags, well)

    top = (
        flags[flags["any_anomaly"]]
        .sort_values("anomaly_score", ascending=False)
        .head(5)
    )
    top_events = []
    for idx, row in top.iterrows():
        top_events.append({
            "date": str(idx.date()) if hasattr(idx, "date") else str(idx),
            "oil_rate": round(row.get("bore_oil_vol", 0), 1),
            "score": round(row.get("anomaly_score", 0), 1),
            "severity": row.get("severity", "N/A"),
        })

    return {**summary, "top_events": top_events}


def get_scorecard(wells: Optional[List[str]] = None) -> List[Dict]:
    """Return performance scorecard as list of dicts."""
    sc = build_scorecard(wells=wells, save=False)
    cols = ["rank", "well", "overall_score", "cum_oil", "recent_oil_rate",
            "recent_water_cut", "anomaly_pct", "decline_r2"]
    cols = [c for c in cols if c in sc.columns]
    return sc[cols].round(2).to_dict(orient="records")


# Registry the agent will use
TOOL_REGISTRY = {
    "get_producer_list": {
        "fn": get_producer_list,
        "description": "List all producer well names in the Volve dataset.",
        "parameters": {},
    },
    "get_well_summary": {
        "fn": get_well_summary,
        "description": "Get production summary (cumulatives, averages, date range) for one well.",
        "parameters": {"well": "str - well bore code, e.g. 'NO 15/9-F-12 H'"},
    },
    "run_forecast": {
        "fn": run_forecast,
        "description": "Run Arps decline-curve forecast for a well.",
        "parameters": {
            "well": "str - well bore code",
            "horizon_days": "int - forecast days ahead (default 180)",
        },
    },
    "get_anomalies": {
        "fn": get_anomalies,
        "description": "Detect anomalies for a well and return summary + top events.",
        "parameters": {
            "well": "str - well bore code",
            "include_residual": "bool - include decline residual flags (default True)",
        },
    },
    "get_scorecard": {
        "fn": get_scorecard,
        "description": "Rank wells by overall performance score.",
        "parameters": {
            "wells": "optional list of well names; if omitted, scores default set",
        },
    },
}
