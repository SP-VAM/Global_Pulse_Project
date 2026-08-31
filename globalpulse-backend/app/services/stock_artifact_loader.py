"""
GlobalPulse Stock ML Artifact Loader & Validator
Lazy-loads and caches XGBoost model, label encoder, and feature names.
Provides startup health validation.
"""
from functools import lru_cache
import logging
import os
from typing import Any, List, Optional

try:
    import joblib
except ImportError:
    joblib = None

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
        # Ensure model_dir is normalized
        if not os.path.isabs(self._model_dir):
            # Resolve relative paths against the project root
            self._model_dir = os.path.normpath(os.path.join(os.getcwd(), self._model_dir))


    @property
    def model_path(self) -> str:
        """Resolve the primary model file path.

        Historically the project used `xgboost_model.pkl`. In some deployments
        the trained artifact may be named differently (e.g. `model_5d_binary.pkl`).
        Prefer `xgboost_model.pkl` when present; otherwise select a reasonable
        fallback by scanning the models directory for a candidate .pkl model file
        (excluding the encoder and features files).
        """
        preferred = os.path.join(self._model_dir, "xgboost_model.pkl")
        if os.path.exists(preferred):
            return preferred

        # Candidate model filenames in preference order
        candidates = [
            "model_1d_binary.pkl",
            "model_1d_3class.pkl",
            "model_5d_binary.pkl",
            "model_5d_3class.pkl",
            "model_10d_binary.pkl",
            "model_10d_3class.pkl",
        ]

        for name in candidates:
            p = os.path.join(self._model_dir, name)
            if os.path.exists(p):
                logger.warning("Primary model file '%s' not found; falling back to '%s'", os.path.basename(preferred), name)
                return p

        # Fallback: pick the first .pkl file that isn't the encoder or features
        try:
            for fname in sorted(os.listdir(self._model_dir)):
                low = fname.lower()
                if not low.endswith('.pkl'):
                    continue
                # Exclude encoder/feature files
                if 'encoder' in low or 'feature' in low or 'label_encoder' in low or 'model_features' in low:
                    continue
                return os.path.join(self._model_dir, fname)
        except Exception:
            pass

        # Default (will trigger missing-artifact error later)
        return preferred

    @property
    def encoder_path(self) -> str:
        return os.path.join(self._model_dir, "label_encoder.pkl")

    @property
    def features_path(self) -> str:
        return os.path.join(self._model_dir, "model_features.pkl")

    def validate_artifacts_exist(self) -> bool:
        """Validate that all 3 required artifact files exist on disk."""
        missing = []
        # Check model (allow fallback name)
        model_exists = os.path.exists(self.model_path)
        if not model_exists:
            missing.append(os.path.basename(self.model_path))

        for path, name in [
            (self.encoder_path, "label_encoder.pkl"),
            (self.features_path, "model_features.pkl"),
        ]:
            if not os.path.exists(path):
                missing.append(name)

        if missing:
            logger.error("Missing stock model artifacts in %s: %s", self._model_dir, missing)
            return False

        # Log resolved model diagnostics
        try:
            size = os.path.getsize(self.model_path)
            logger.info("Stock model resolved: %s (size=%d bytes)", self.model_path, size)
        except Exception:
            logger.info("Stock model resolved: %s", self.model_path)

        return True

    @lru_cache(maxsize=1)
    def load_model(self) -> Any:
        """Load and cache the trained XGBoost model."""
        if not os.path.exists(self.model_path):
            raise ModelArtifactsNotFoundError(f"XGBoost model file not found at '{self.model_path}'")
        try:
            size = os.path.getsize(self.model_path)
            logger.info("Loading stock model from %s (size=%d bytes)", self.model_path, size)
        except Exception:
            logger.info("Loading stock model from %s", self.model_path)
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
