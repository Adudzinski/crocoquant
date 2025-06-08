import pandas as pd

def predict(price: pd.DataFrame, lookback: int, z_entry: float) -> pd.DataFrame:
    ma  = price.rolling(lookback).mean()
    std = price.rolling(lookback).std()
    z   = (price - ma) / std
    # Convert z-score to probability -1 → 0, +1 → 1
    p = (z_entry - z).clip(lower=0) / (2 * z_entry)
    return p.fillna(0.5)  # 0.5 = neutral
