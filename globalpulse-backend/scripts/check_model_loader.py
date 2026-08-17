import os
os.environ.setdefault('DATABASE_URL', 'postgresql+asyncpg://user:pass@localhost:5432/db')
from app.services.stock_artifact_loader import StockArtifactLoader
l = StockArtifactLoader()
print('MODEL_DIR:', l._model_dir)
print('RESOLVED_MODEL_PATH:', l.model_path)
print('MODEL_EXISTS:', os.path.exists(l.model_path))
try:
    print('MODEL_SIZE:', os.path.getsize(l.model_path))
except Exception as e:
    print('MODEL_SIZE_ERROR:', e)
