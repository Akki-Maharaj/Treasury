from pathlib import Path
from typing import Tuple, Optional
import joblib

# Load the trained Pipeline once at module import time to avoid per-request overhead
MODEL_PATH = Path(__file__).resolve().parent / "models" / "category_clf.joblib"
_model = None

try:
    if MODEL_PATH.exists():
        _model = joblib.load(MODEL_PATH)
except Exception as e:
    print(f"[WARN] Could not load category classifier from {MODEL_PATH}: {e}")


# Predicts category label and confidence; returns (None, conf) if confidence < 0.45
def predict_category(text: str) -> Tuple[Optional[str], float]:
    if not text or not text.strip() or _model is None:
        return (None, 0.0)

    try:
        probs = _model.predict_proba([text.strip()])[0]
        top_idx = probs.argmax()
        label = _model.classes_[top_idx]
        confidence = float(probs[top_idx])

        # Avoid poor suggestions when uncertainty is high
        if confidence < 0.45:
            return (None, round(confidence, 3))

        return (str(label), round(confidence, 3))
    except Exception as e:
        print(f"[WARN] Error during category prediction: {e}")
        return (None, 0.0)
