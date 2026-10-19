"""
Arps Decline Curve Analysis
Implements Exponential and Hyperbolic decline models.
"""

import numpy as np
from scipy.optimize import curve_fit
from dataclasses import dataclass
from typing import Optional


@dataclass
class DeclineResult:
    model: str
    qi: float  # initial rate
    di: float  # initial decline rate
    b: Optional[float]  # hyperbolic exponent (None for exponential)
    r2: float
    params: dict


def exponential_decline(t, qi, di):
    """q(t) = qi * exp(-di * t)"""
    return qi * np.exp(-di * t)


def hyperbolic_decline(t, qi, di, b):
    """q(t) = qi / (1 + b * di * t)^(1/b)"""
    return qi / np.power(1 + b * di * t, 1 / b)


def fit_exponential(t: np.ndarray, q: np.ndarray) -> DeclineResult:
    """Fit exponential decline curve."""
    # Initial guesses
    qi_guess = q[0]
    di_guess = 0.001

    try:
        popt, _ = curve_fit(
            exponential_decline,
            t,
            q,
            p0=[qi_guess, di_guess],
            bounds=([0, 0], [np.inf, 1]),
            maxfev=5000,
        )
        qi, di = popt
        q_pred = exponential_decline(t, qi, di)
        ss_res = np.sum((q - q_pred) ** 2)
        ss_tot = np.sum((q - np.mean(q)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        return DeclineResult(
            model="exponential",
            qi=qi,
            di=di,
            b=None,
            r2=r2,
            params={"qi": qi, "di": di},
        )
    except Exception:
        return DeclineResult("exponential", np.nan, np.nan, None, 0.0, {})


def fit_hyperbolic(t: np.ndarray, q: np.ndarray) -> DeclineResult:
    """Fit hyperbolic decline curve."""
    qi_guess = q[0]
    di_guess = 0.001
    b_guess = 0.5

    try:
        popt, _ = curve_fit(
            hyperbolic_decline,
            t,
            q,
            p0=[qi_guess, di_guess, b_guess],
            bounds=([0, 0, 0.01], [np.inf, 1, 2.0]),
            maxfev=8000,
        )
        qi, di, b = popt
        q_pred = hyperbolic_decline(t, qi, di, b)
        ss_res = np.sum((q - q_pred) ** 2)
        ss_tot = np.sum((q - np.mean(q)) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        return DeclineResult(
            model="hyperbolic",
            qi=qi,
            di=di,
            b=b,
            r2=r2,
            params={"qi": qi, "di": di, "b": b},
        )
    except Exception:
        return DeclineResult("hyperbolic", np.nan, np.nan, np.nan, 0.0, {})


def select_best_model(t: np.ndarray, q: np.ndarray) -> DeclineResult:
    """Fit both models and return the one with higher R²."""
    exp = fit_exponential(t, q)
    hyp = fit_hyperbolic(t, q)

    if hyp.r2 >= exp.r2:
        return hyp
    return exp
