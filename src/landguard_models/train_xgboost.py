"""Trains XGBoost fraud-risk benchmark classifier with early stopping on validation split."""

from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
from xgboost import XGBClassifier


def train_xgboost_model(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    X_val: pd.DataFrame,
    y_val: np.ndarray,
    params: dict = None,
    early_stopping_rounds: int = 25
) -> XGBClassifier:
    default_params = {
        "n_estimators": 250,
        "max_depth": 5,
        "learning_rate": 0.05,
        "subsample": 0.85,
        "colsample_bytree": 0.85,
        "eval_metric": "logloss",
        "random_state": 42,
        "n_jobs": -1
    }
    if params:
        default_params.update(params)
        
    model = XGBClassifier(**default_params)
    
    # Fit with evaluation set
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )
    
    return model


def get_feature_importances(model: XGBClassifier, feature_names: list) -> Dict[str, float]:
    importances = model.feature_importances_
    return {name: round(float(imp), 4) for name, imp in sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)}
