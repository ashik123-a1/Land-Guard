"""Trains classical machine learning baselines (Logistic Regression and Random Forest)."""

from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler


def train_logistic_regression(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    random_state: int = 42
) -> Tuple[LogisticRegression, StandardScaler]:
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_train)
    
    clf = LogisticRegression(C=1.0, max_iter=1000, random_state=random_state)
    clf.fit(X_scaled, y_train)
    return clf, scaler


def train_random_forest(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    n_estimators: int = 200,
    max_depth: int = 10,
    random_state: int = 42
) -> RandomForestClassifier:
    rf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)
    return rf
