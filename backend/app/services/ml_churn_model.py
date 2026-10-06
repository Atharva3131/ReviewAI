"""
ML Churn Risk Prediction Model
Simple XGBoost-based customer churn prediction using review-based features
"""

import json
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

# Model storage paths
MODELS_DIR = Path(__file__).parent.parent.parent / "models"
MODELS_DIR.mkdir(exist_ok=True)

LR_MODEL_PATH = MODELS_DIR / "lr_churn_model.pkl"
SCALER_PATH = MODELS_DIR / "feature_scaler.pkl"
XGB_MODEL_PATH = MODELS_DIR / "xgboost_churn_model.json"


class MLChurnModel:
    """ML-based customer churn risk prediction"""

    FEATURE_NAMES = [
        "rating",
        "urgency_level",
        "negative_review_count",
        "support_ticket_count",
        "days_since_last_interaction",
        "account_tenure_days",
        "avg_previous_rating",
    ]

    def __init__(self, model_type: str = "xgboost"):
        """
        Initialize ML model

        Args:
            model_type: 'xgboost' or 'logistic_regression'
        """
        self.model_type = model_type
        self.model: Optional[xgb.XGBClassifier | LogisticRegression] = None
        self.scaler: Optional[StandardScaler] = None
        self.is_trained = False
        self.model_version = "1.0.0"

    async def train_or_load(self, force_train: bool = False) -> bool:
        """
        Load existing model or train new one

        Args:
            force_train: Force retraining even if model exists

        Returns:
            True if model is ready
        """
        if not force_train and self.model_type == "xgboost":
            if XGB_MODEL_PATH.exists() and SCALER_PATH.exists():
                return await self._load_xgboost()

        # Train new model
        logger.info(
            f"Training {self.model_type} churn model with synthetic data..."
        )
        return await self._train_model()

    async def _train_model(self) -> bool:
        """Train model with synthetic data"""
        try:
            # Generate synthetic training data
            X_train, y_train = self._generate_synthetic_data(n_samples=200)

            # Initialize scaler
            self.scaler = StandardScaler()
            X_train_scaled = self.scaler.fit_transform(X_train)

            if self.model_type == "xgboost":
                self.model = xgb.XGBClassifier(
                    n_estimators=50,
                    max_depth=4,
                    learning_rate=0.1,
                    random_state=42,
                    use_label_encoder=False,
                    eval_metric="logloss",
                )
            else:
                self.model = LogisticRegression(
                    max_iter=100, random_state=42, solver="lbfgs"
                )

            self.model.fit(X_train_scaled, y_train)
            self.is_trained = True

            # Save model
            if self.model_type == "xgboost":
                self.model.save_model(str(XGB_MODEL_PATH))
                import pickle

                with open(SCALER_PATH, "wb") as f:
                    pickle.dump(self.scaler, f)
                logger.info(
                    f"Model saved to {XGB_MODEL_PATH}\n"
                    "Note: Trained on synthetic demo data"
                )

            return True

        except Exception as e:
            logger.error(f"Failed to train model: {e}")
            return False

    async def _load_xgboost(self) -> bool:
        """Load saved XGBoost model"""
        try:
            import pickle

            self.model = xgb.XGBClassifier()
            self.model.load_model(str(XGB_MODEL_PATH))

            with open(SCALER_PATH, "rb") as f:
                self.scaler = pickle.load(f)

            self.is_trained = True
            logger.info("XGBoost model loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    async def predict(self, features: dict) -> dict:
        """
        Predict churn risk for a customer

        Args:
            features: Dictionary with feature values

        Returns:
            {churn_probability, confidence, top_features}
        """
        if not self.is_trained:
            await self.train_or_load()

        try:
            # Extract and order features
            X = np.array(
                [[features.get(name, 0.0) for name in self.FEATURE_NAMES]]
            )

            # Scale
            if self.scaler:
                X_scaled = self.scaler.transform(X)
            else:
                X_scaled = X

            # Predict
            proba = self.model.predict_proba(X_scaled)[0]
            churn_prob = float(proba[1])  # Class 1 = churn

            return {
                "churn_probability": churn_prob,
                "confidence": float(max(proba)),
                "prediction": "high_churn_risk"
                if churn_prob > 0.7
                else "low_churn_risk",
            }

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return {
                "churn_probability": 0.5,
                "confidence": 0.3,
                "error": str(e),
            }

    @staticmethod
    def _generate_synthetic_data(
        n_samples: int = 200,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Generate synthetic training data
        
        This is for demonstration purposes.
        In production, use real customer interaction data.
        """
        np.random.seed(42)

        data = []
        labels = []

        for _ in range(n_samples):
            # Rating: lower rating -> higher churn risk
            rating = np.random.randint(1, 6)
            churn = int(rating <= 2)

            # Urgency level: higher urgency -> higher churn risk
            urgency = np.random.randint(1, 6)
            if urgency >= 4:
                churn = max(churn, np.random.choice([0, 1], p=[0.3, 0.7]))

            # Other features add noise
            negative_reviews = (
                np.random.randint(0, 5) if churn else np.random.randint(0, 2)
            )
            support_tickets = (
                np.random.randint(0, 4) if churn else np.random.randint(0, 1)
            )
            days_inactive = (
                np.random.randint(30, 365) if churn else np.random.randint(0, 60)
            )
            tenure = np.random.randint(30, 1095)
            avg_rating = np.random.uniform(2.5, 4.8)

            data.append(
                [
                    rating,
                    urgency,
                    negative_reviews,
                    support_tickets,
                    days_inactive,
                    tenure,
                    avg_rating,
                ]
            )
            labels.append(churn)

        return np.array(data), np.array(labels)


# Global model instance
_ml_model: Optional[MLChurnModel] = None


async def get_ml_churn_model() -> MLChurnModel:
    """Get or create ML churn model instance"""
    global _ml_model
    if _ml_model is None:
        _ml_model = MLChurnModel(model_type="xgboost")
        await _ml_model.train_or_load()
    return _ml_model
