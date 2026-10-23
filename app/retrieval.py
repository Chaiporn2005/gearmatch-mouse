"""Reproducible lexical-vector RAG. No pretrained semantic model is claimed."""
from collections import Counter
from pathlib import Path
import json
import math
import re
import numpy as np
from .models import Filters

ROOT = Path(__file__).resolve().parents[1]
ALIASES = {
    "ไร้สาย": "wireless bluetooth 2.4ghz", "บลูทูธ": "bluetooth",
    "เล่นเกม": "gaming", "เกม": "gaming", "fps": "gaming lightweight",
    "ทำงาน": "office productivity", "เงียบ": "silent quiet",
    "เบา": "lightweight", "พกพา": "travel compact", "มือซ้าย": "left",
    "แนวตั้ง": "vertical ergonomic", "ergonomic": "vertical ergonomic",
    "quiet": "silent", "silent": "quiet", "portable": "travel compact",
    "wireless": "bluetooth 2.4ghz", "esports": "gaming lightweight",
}


def tokens(text, expand=False):
    value = text.lower()
    if expand:
        value += " " + " ".join(v for k, v in ALIASES.items() if k in value)
    return re.findall(r"[a-z0-9]+|[\u0e00-\u0e7f]+", value)


def product_text(p):
    # Match the web runtime's canonical JSON/list representation exactly.
    return " ".join([p["name"],p["brand"],*p["connection"],p.get("handedness") or "",p.get("shape") or "",*p["use_cases"],*p["features"],json.dumps(p["specs"],ensure_ascii=False,separators=(",",":")),p["source_excerpt"]])


def matches(p, f):
    if f.budget is not None and (p.get("price") is None or p["price"] > f.budget):
        return False
    if f.max_weight is not None and (p.get("weight_g") is None or p["weight_g"] > f.max_weight):
        return False
    if f.connection and f.connection not in p.get("connection", []):
        return False
    if f.handedness and p.get("handedness") != f.handedness:
        return False
    if f.use_case and f.use_case not in p.get("use_cases", []):
        return False
    return True


class Index:
    def __init__(self, products=None):
        self.products = products if products is not None else json.loads((ROOT / "data/catalog.json").read_text())
        self.by_id = {p["id"]: p for p in self.products}
        self.documents = [tokens(product_text(p)) for p in self.products]
        self.counts = [Counter(doc) for doc in self.documents]
        self.vocab = sorted({word for doc in self.documents for word in doc})
        self.word_index = {word: i for i, word in enumerate(self.vocab)}
        n = len(self.products)
        self.df = {word: sum(word in doc for doc in self.counts) for word in self.vocab}
        self.idf = {word: math.log(1 + (n - self.df[word] + 0.5) / (self.df[word] + 0.5)) for word in self.vocab}
        self.avg_len = sum(map(len, self.documents)) / max(n, 1)
        self.matrix = np.array([self.vector(doc) for doc in self.documents])

    def vector(self, doc):
        counts = Counter(doc)
        vector = np.zeros(len(self.vocab), dtype=float)
        for word, count in counts.items():
            if word in self.word_index:
                vector[self.word_index[word]] = (1 + math.log(count)) * self.idf[word]
        norm = np.linalg.norm(vector)
        return vector / norm if norm else vector

    def search(self, query, filters=None, k=3, improved=True, strategy=None):
        f = filters or Filters()
        strategy = strategy or ("hybrid" if improved else "bm25")
        expanded = strategy == "hybrid"
        constrained = strategy != "bm25"
        words = tokens(query, expand=expanded)
        lexical = []
        for i, counts in enumerate(self.counts):
            length = len(self.documents[i])
            score = sum(self.idf.get(w, 0) * counts[w] * 2.5 /
                        (counts[w] + 1.5 * (0.25 + 0.75 * length / max(self.avg_len, 1)))
                        for w in words if counts[w])
            lexical.append(score)
        eligible = [i for i, p in enumerate(self.products) if not constrained or matches(p, f)]
        bm = sorted((i for i in eligible if lexical[i] > 0), key=lambda i: (-lexical[i], i))
        if strategy != "hybrid":
            return [{"product": self.products[i], "score": round(lexical[i], 6)} for i in bm[:k]]
        q = self.vector(words)
        cosine = self.matrix @ q if self.products else []
        vr = sorted((i for i in eligible if cosine[i] > 0), key=lambda i: (-cosine[i], i))
        fused = Counter()
        for ranking in (bm, vr):
            for rank, i in enumerate(ranking, 1):
                fused[i] += 1 / (60 + rank)
        # Filters alone may be meaningful even if query vocabulary does not overlap.
        if not fused and any(v is not None for v in f.model_dump().values()):
            return [{"product": self.products[i], "score": 0.0} for i in eligible[:k]]
        order = sorted(fused, key=lambda i: (-fused[i], i))
        return [{"product": self.products[i], "score": round(fused[i], 6)} for i in order[:k]]

    def filter(self, filters, k=6):
        return [p for p in self.products if matches(p, filters)][:k]
