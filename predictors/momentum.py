# predictors/momentum.py
"""
Momentum predictor
------------------
• Computes the N-day % return (default 10 days).  
• Scales that return into a probability:
        strong +mom  →  p → 1
        flat         →  p → 0.5
        strong –mom  →  p → 0
• Clip extreme values so the range is always [0, 1].

Tune `lookback` and `clip` in config.yaml if you like.
"""

import pandas as pd
import numpy as np

def predict(price: pd.DataFrame,
            lookback: int ,
            clip: float ) -> pd.DataFrame:
    """
    Parameters
    ----------
    price : DataFrame  (dates × tickers)
    lookback : int     number of days for momentum
    clip : float       max abs-return to map linearly

    """

    # 1) simple N-day % return
    mom = price.pct_change(lookback)

    # 2) convert to probability
    #    +clip   → 1
    #     0      → 0.5
    #    –clip   → 0
    p = (mom / (2 * clip) + 0.5).clip(0, 1)
    # 3) fill NaNs (first 'lookback' rows) with neutral 0.5
    return p.fillna(0.5)

