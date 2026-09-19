from typing import Optional, Dict, List
from fastapi import APIRouter
from pydantic import BaseModel
from app.ml.category import predict_category
from app.ml.schema import CATEGORY_FIELDS, DEFAULT_FIELDS
from app.ml.extract import extract_attributes
from app.ml.describe import generate_description

router = APIRouter(prefix="/api", tags=["AI"])


class PredictCategoryRequest(BaseModel):
    title: str
    description: Optional[str] = ""


# Public JSON endpoint predicting category suggestion for /sell form
@router.post("/predict-category")
def api_predict_category(payload: PredictCategoryRequest):
    combined_text = f"{payload.title.strip()} {payload.description.strip() if payload.description else ''}".strip()
    category, confidence = predict_category(combined_text)
    return {
        "category": category,
        "confidence": confidence
    }


class SellAnalyzeRequest(BaseModel):
    text: str
    answers: Optional[Dict[str, str]] = None
    skipped_in_a_row: Optional[int] = 0
    skipped_keys: Optional[List[str]] = None


@router.post("/sell/analyze")
def api_sell_analyze(payload: SellAnalyzeRequest):
    answers = payload.answers or {}
    skipped_in_a_row = payload.skipped_in_a_row or 0
    skipped_keys = set(payload.skipped_keys or [])

    category, confidence = predict_category(payload.text)
    extracted = extract_attributes(payload.text, category)

    # Merge extracted with answers (answers win)
    filled = {**extracted, **answers}

    expected_fields = CATEGORY_FIELDS.get(category, DEFAULT_FIELDS)

    # Missing fields are expected fields not filled and not in skipped_keys
    missing = [
        (k, q) for k, q in expected_fields
        if k not in filled and k not in skipped_keys
    ]

    done = False
    next_question = None
    message = ""

    if skipped_in_a_row >= 2:
        done = True
        message = "No problem, you can add more details later."
    elif not missing:
        done = True
        message = "Great! All key details have been captured."
    else:
        next_k, next_q = missing[0]
        next_question = {"key": next_k, "text": next_q}

    description = ""
    if done:
        description = generate_description(
            title=f"{filled.get('brand', '')} {filled.get('model', '')} {filled.get('year', '')}".strip(),
            category=category,
            attrs=filled
        )

    return {
        "category": category,
        "confidence": confidence,
        "filled": filled,
        "next_question": next_question,
        "done": done,
        "message": message,
        "description": description
    }

