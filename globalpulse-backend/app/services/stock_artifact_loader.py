"""
GlobalPulse Stock ML Artifact Loader & Validator
Lazy-loads and caches XGBoost model, label encoder, and feature names.
Provides startup health validation.
"""
from functools import lru_cache
import logging
import os
from typing import Any, List, Optional

import joblib

from app.core.config import get_settings
from app.core.exceptions import GlobalPulseError

logger = logging.getLogger(__name__)


class ModelArtifactsNotFoundError(GlobalPulseError):
    """Raised when required stock model artifacts are missing from disk."""
    pass


class StockArtifactLoader:
    """Lazy loader and validator for XGBoost model artifacts."""

    def __init__(self, model_dir: Optional[str] = None) -> None:
        settings = get_settings()
        self._model_dir = model_dir or settings.STOCK_MODEL_DIR

    @property
    def model_path(self) -> str:
        return os.path.join(self._model_dir, "xgboost_model.pkl")

    @property
    def encoder_path(self) -> str:
        return os.path.join(self._model_dir, "label_encoder.pkl")

    @property
    def features_path(self) -> str:
        return os.path.join(self._model_dir, "model_features.pkl")

    def validate_artifacts_exist(self) -> bool:
        """Validate that all 3 required artifact files exist on disk."""
        missing = []
        for path, name in [
            (self.model_path, "xgboost_model.pkl"),
            (self.encoder_path, "label_encoder.pkl"),
            (self.features_path, "model_features.pkl"),
        ]:
            if not os.path.exists(path):
                missing.append(name)

        if missing:
            logger.error("Missing stock model artifacts in %s: %s", self._model_dir, missing)
            return False
        return True

    @lru_cache(maxsize=1)
    def load_model(self) -> Any:
        """Load and cache the trained XGBoost model."""
        if not os.path.exists(self.model_path):
            raise ModelArtifactsNotFoundError(f"XGBoost model file not found at '{self.model_path}'")
        logger.info("Loading stock XGBoost model from %s", self.model_path)
        return joblib.load(self.model_path)

    @lru_cache(maxsize=1)
    def load_label_encoder(self) -> Any:
        """Load and cache the label encoder."""
        if not os.path.exists(self.encoder_path):
            raise ModelArtifactsNotFoundError(f"Label encoder file not found at '{self.encoder_path}'")
        return joblib.load(self.encoder_path)

    @lru_cache(maxsize=1)
    def load_model_features(self) -> List[str]:
        """Load and cache the expected feature column names."""
        if not os.path.exists(self.features_path):
            raise ModelArtifactsNotFoundError(f"Model features file not found at '{self.features_path}'")
        features = joblib.load(self.features_path)
        return list(features)


@lru_cache(maxsize=1)
def get_stock_artifact_loader() -> StockArtifactLoader:
    """Return singleton artifact loader."""
    return StockArtifactLoader()
