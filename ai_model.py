from sentence_transformers import SentenceTransformer
# ...existing code...
from typing import List, Optional

_model = None

def _load_model():
    global _model
    if _model is None:
        # heavy なライブラリはここで初めて読み込む
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def get_embedding(text: str) -> List[float]:
    model = _load_model()
    embedding = model.encode(text)
    return embedding.tolist()
# ...existing code...