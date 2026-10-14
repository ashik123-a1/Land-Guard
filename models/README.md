# LandGuard Models Directory

This directory stores model definitions, evaluation artifacts, and training configurations.

## Architecture
- Evaluated models:
  1. `Deterministic Statutory Rule Engine` (`src/landguard_models/verification_rules.py`)
  2. `Logistic Regression Baseline` (`src/landguard_models/train_baselines.py`)
  3. `Random Forest Baseline` (`src/landguard_models/train_baselines.py`)
  4. `XGBoost Classifier` (`src/landguard_models/train_xgboost.py`)

## Reproducibility
Model weights and evaluation results can be re-trained and verified anytime with:
```bash
python scripts/run_model_evaluation.py
```
Evaluation metrics and comparative CSVs are saved to:
- `evidence/metrics/model_comparison.csv`
- `evidence/metrics/model_comparison.json`
- `evidence/metrics/xgboost_feature_importance.json`
