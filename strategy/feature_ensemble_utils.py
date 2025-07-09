#feature_ensemble_utils.py:

import pandas as pd
from strategy.train_model_historic import FeatureEngineer

def prepare_features_for_ensemble(candles: list, timeframe: str, symbol: str) -> pd.DataFrame:
    df = pd.DataFrame(candles)
    df = FeatureEngineer.add_technical_indicators(df, timeframe, symbol)
    return df
