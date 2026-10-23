from pathlib import Path
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import APIError
from .agent import recommend
from .models import Filters, SearchRequest
from .retrieval import Index

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
app = FastAPI(title="GearMatch", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
index = None


def get_index():
    global index
    if index is None:
        index = Index()
    return index


@app.get("/api/health")
def health():
    return {"ok": True, "model": os.getenv("OPENAI_MODEL", "gemma-4-E4B-it"), "llm_configured": bool(os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_BASE_URL")), "products": len(get_index().products)}


@app.get("/api/catalog")
def catalog():
    return {"products": get_index().products, "currency": "USD", "price_note": "Recorded manufacturer reference prices, not current Thai retail prices."}


@app.post("/api/search")
def search(request: SearchRequest):
    return {"hits": get_index().search(request.question, request.filters), "mode": "catalog_search"}


@app.post("/api/recommend")
def recommendations(request: SearchRequest):
    try:
        return recommend(request, get_index())
    except RuntimeError as exc:
        if str(exc) == "CLASS_PROXY_NOT_CONFIGURED":
            raise HTTPException(503, "Configure class proxy environment variables. Catalog search remains available.") from exc
        raise HTTPException(502, "Agent stopped without a validated answer. Refine the query and try again.") from exc
    except APIError as exc:
        raise HTTPException(502, "Class proxy request failed. Check server configuration or retry later.") from exc
