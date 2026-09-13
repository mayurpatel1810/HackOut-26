"""Function-aware circular retrieval (Master Spec sections 21, 24, 25).

The whole point: retrieval is driven by what the material DOES in this factory's
process, not by its name. "Silica sand" as a moulding medium and "silica sand"
as a polishing abrasive need different alternatives, and a name-only search
cannot tell them apart.

Ranking is hybrid. Cosine similarity alone is never trusted: it is one term
among industry, process, function, material, node relevance, region, maturity,
evidence confidence and budget fit, and every term that fired is recorded in
`reasons` so the UI can explain the ranking.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol, Sequence, Tuple

import numpy as np

from .embeddings import Embedder, build_embedder
from .impact import FootprintState
from .knowledge_base import Intervention
from .models import ActivityRecord, FactoryContext, Hotspot

COLLECTIONS = ("material_knowledge", "process_interventions", "circular_loops")

TYPE_COLLECTION = {
    "material_substitution": "material_knowledge",
    "circular_procurement": "material_knowledge",
    "process_improvement": "process_interventions",
    "energy_efficiency": "process_interventions",
    "renewable_energy": "process_interventions",
    "recycling_loop": "circular_loops",
    "waste_recovery": "circular_loops",
    "industrial_symbiosis": "circular_loops",
}

HYBRID_WEIGHTS = {
    "semantic": 0.30,
    "node_relevance": 0.22,
    "function": 0.14,
    "process": 0.10,
    "industry": 0.08,
    "material": 0.08,
    "region": 0.04,
    "maturity": 0.02,
    "confidence": 0.02,
}


@dataclass
class RetrievalContext:
    """Everything that shapes the query (Master Spec section 21)."""
    industry: str
    country_code: str
    processes: List[str] = field(default_factory=list)
    materials: List[str] = field(default_factory=list)
    material_grades: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    waste_streams: List[str] = field(default_factory=list)
    energy_carriers: List[str] = field(default_factory=list)
    hot_nodes: List[str] = field(default_factory=list)
    budget_inr: Optional[float] = None
    target_reduction_pct: Optional[float] = None

    @classmethod
    def build(cls, ctx: FactoryContext, records: Sequence[ActivityRecord],
              hotspots: Sequence[Hotspot]) -> "RetrievalContext":
        return cls(
            industry=ctx.industry, country_code=ctx.country_code,
            processes=[r.process_name for r in records if r.process_name],
            materials=[r.material or r.label for r in records
                       if r.record_type == "MATERIAL"],
            material_grades=[r.material_grade for r in records if r.material_grade],
            functions=[r.function for r in records if r.function],
            waste_streams=[f"{r.label} ({r.treatment})" for r in records
                           if r.record_type == "WASTE"],
            energy_carriers=[r.key for r in records if r.record_type == "ENERGY"],
            hot_nodes=[h.node_key for h in hotspots],
            budget_inr=ctx.budget_inr,
            target_reduction_pct=ctx.target_reduction_pct)

    def to_query(self) -> str:
        """The semantic query. Note it is a technical sentence about function and
        conditions, not 'find sustainable X'."""
        bits = [f"{self.industry} factory in {self.country_code}"]
        if self.processes:
            bits.append("processes: " + ", ".join(dict.fromkeys(self.processes)))
        for m, f in zip(self.materials, self.functions + [""] * len(self.materials)):
            bits.append(f"uses {m}" + (f" for {f}" if f else ""))
        if self.functions:
            bits.append("required functions: " + ", ".join(dict.fromkeys(self.functions)))
        if self.material_grades:
            bits.append("material grades: " + ", ".join(dict.fromkeys(self.material_grades)))
        if self.waste_streams:
            bits.append("waste streams: " + ", ".join(dict.fromkeys(self.waste_streams)))
        if self.energy_carriers:
            bits.append("energy carriers: " + ", ".join(dict.fromkeys(self.energy_carriers)))
        if self.hot_nodes:
            bits.append("largest emission sources: " + ", ".join(self.hot_nodes[:4]))
        bits.append("seeking technically compatible lower-carbon circular alternatives")
        if self.budget_inr:
            bits.append(f"within a capital budget of about INR {self.budget_inr:,.0f}")
        return ". ".join(bits)


@dataclass
class Retrieved:
    intervention: Intervention
    collection: str
    semantic: float
    hybrid: float
    reasons: List[str]

    def to_dict(self) -> dict:
        return {"slug": self.intervention.slug, "collection": self.collection,
                "semantic_score": round(self.semantic, 4),
                "hybrid_score": round(self.hybrid, 4), "reasons": self.reasons}


class VectorStore(Protocol):
    def upsert(self, collection: str, ids: Sequence[str], vectors: np.ndarray,
               payloads: Sequence[dict]) -> None: ...
    def search(self, collection: Optional[str], query: np.ndarray, k: int
               ) -> List[Tuple[str, float, dict]]: ...


class InMemoryVectorStore:
    """Used by tests and by any deployment without pgvector. Exact cosine."""

    def __init__(self):
        self._data: Dict[str, Tuple[List[str], np.ndarray, List[dict]]] = {}

    def upsert(self, collection, ids, vectors, payloads):
        self._data[collection] = (list(ids), np.asarray(vectors, dtype=np.float32),
                                  list(payloads))

    def search(self, collection, query, k):
        out: List[Tuple[str, float, dict]] = []
        cols = [collection] if collection else list(self._data)
        q = np.asarray(query, dtype=np.float32).reshape(-1)
        for c in cols:
            if c not in self._data:
                continue
            ids, mat, payloads = self._data[c]
            if mat.size == 0:
                continue
            sims = mat @ q
            for i in np.argsort(-sims)[:k]:
                out.append((ids[i], float(sims[i]), payloads[i]))
        out.sort(key=lambda t: -t[1])
        return out[:k]


class PgVectorStore:
    """pgvector-backed store. Same interface, same cosine ordering."""

    def __init__(self, conn_factory, model_name: str):
        self._conn_factory = conn_factory
        self._model = model_name

    def upsert(self, collection, ids, vectors, payloads):
        import json
        rows = [(collection, p.get("ref_type", "intervention"), i, 0,
                 p.get("content", ""), json.dumps(p), self._model,
                 "[" + ",".join(f"{x:.7f}" for x in vec) + "]")
                for i, vec, p in zip(ids, vectors, payloads)]
        with self._conn_factory() as conn, conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO embeddings (collection, ref_type, ref_id, chunk_index,"
                " content, metadata, model, embedding)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s,%s::vector)"
                " ON CONFLICT (collection, ref_type, ref_id, chunk_index)"
                " DO UPDATE SET content=EXCLUDED.content, metadata=EXCLUDED.metadata,"
                " model=EXCLUDED.model, embedding=EXCLUDED.embedding", rows)
            conn.commit()

    def search(self, collection, query, k):
        vec = "[" + ",".join(f"{x:.7f}" for x in np.asarray(query).reshape(-1)) + "]"
        sql = ("SELECT ref_id, 1 - (embedding <=> %s::vector) AS score, metadata "
               "FROM embeddings WHERE (%s IS NULL OR collection = %s) "
               "ORDER BY embedding <=> %s::vector LIMIT %s")
        with self._conn_factory() as conn, conn.cursor() as cur:
            cur.execute(sql, (vec, collection, collection, vec, k))
            return [(r[0], float(r[1]), r[2]) for r in cur.fetchall()]


class CircularRetriever:
    def __init__(self, interventions: Sequence[Intervention],
                 embedder: Optional[Embedder] = None,
                 store: Optional[VectorStore] = None):
        self.interventions = list(interventions)
        self.by_slug = {i.slug: i for i in self.interventions}
        self.embedder = embedder or build_embedder()
        self.store = store or InMemoryVectorStore()
        self._index()

    def _index(self) -> None:
        docs = [i.retrieval_document() for i in self.interventions]
        self.embedder.fit(docs)
        vecs = self.embedder.encode(docs)
        buckets: Dict[str, List[int]] = {}
        for idx, iv in enumerate(self.interventions):
            buckets.setdefault(TYPE_COLLECTION.get(iv.type, "process_interventions"),
                               []).append(idx)
        for col, idxs in buckets.items():
            self.store.upsert(col, [self.interventions[i].slug for i in idxs],
                              vecs[idxs],
                              [{"ref_type": "intervention", "collection": col,
                                "content": docs[i], "slug": self.interventions[i].slug}
                               for i in idxs])

    # ------------------------------------------------------------------ API
    def retrieve(self, rc: RetrievalContext, k: int = 24,
                 collection: Optional[str] = None) -> List[Retrieved]:
        qvec = self.embedder.encode([rc.to_query()])[0]
        hits = self.store.search(collection, qvec, k=max(k, len(self.interventions)))
        sem = {slug: score for slug, score, _ in hits}
        out: List[Retrieved] = []
        for iv in self.interventions:
            if collection and TYPE_COLLECTION.get(iv.type) != collection:
                continue
            s = sem.get(iv.slug, 0.0)
            hybrid, reasons = self._rerank(iv, rc, s)
            out.append(Retrieved(iv, TYPE_COLLECTION.get(iv.type, "process_interventions"),
                                 s, hybrid, reasons))
        out.sort(key=lambda r: -r.hybrid)
        return out[:k]

    # --------------------------------------------------------------- rerank
    @staticmethod
    def _rerank(iv: Intervention, rc: RetrievalContext, semantic: float
                ) -> Tuple[float, List[str]]:
        reasons: List[str] = []
        c: Dict[str, float] = {"semantic": max(0.0, min(1.0, (semantic + 1) / 2))}

        # node relevance - does it act where the emissions actually are?
        node = iv.impact_target_node or ""
        if node and node in rc.hot_nodes:
            pos = rc.hot_nodes.index(node)
            c["node_relevance"] = max(0.3, 1.0 - 0.15 * pos)
            reasons.append(f"acts on '{node}', which is leak #{pos + 1}")
        elif node and any(n.split(".")[0] == node.split(".")[0] for n in rc.hot_nodes):
            c["node_relevance"] = 0.45
            reasons.append(f"acts on the same family as a ranked leak ({node})")
        else:
            c["node_relevance"] = 0.05

        def contains(hay: Sequence[str], needle: Optional[str]) -> bool:
            if not needle:
                return False
            n = needle.lower()
            return any(n in h.lower() or h.lower() in n for h in hay if h)

        c["function"] = 1.0 if contains(rc.functions, iv.function) else (
            0.4 if not rc.functions else 0.0)
        if c["function"] == 1.0:
            reasons.append(f"matches the required function '{iv.function}'")

        c["process"] = 0.0
        if "*" in iv.process:
            c["process"] = 0.5
        elif any(contains(rc.processes, p) for p in iv.process):
            c["process"] = 1.0
            reasons.append("matches a process recorded for this factory")

        c["industry"] = 0.5 if "*" in iv.industry else (
            1.0 if any(i.lower() in rc.industry.lower() for i in iv.industry) else 0.0)
        if c["industry"] == 1.0:
            reasons.append("documented for this industry")

        c["material"] = 0.0
        if iv.current_material and contains(rc.materials, iv.current_material):
            c["material"] = 1.0
            reasons.append(f"replaces '{iv.current_material}', which this factory uses")
        elif not iv.current_material:
            c["material"] = 0.3

        c["region"] = 1.0 if ("*" in iv.regions or rc.country_code in iv.regions) else 0.0
        if c["region"] == 0.0:
            reasons.append("not documented for this country")

        c["maturity"] = {"COMMERCIAL": 1.0, "EMERGING": 0.6, "PILOT": 0.35,
                         "RESEARCH": 0.15}.get(iv.maturity, 0.3)
        c["confidence"] = {"high": 1.0, "medium": 0.7, "low": 0.35}.get(iv.confidence, 0.35)

        total = sum(HYBRID_WEIGHTS[k] * v for k, v in c.items())
        reasons.append("hybrid score components: " + ", ".join(
            f"{k}={v:.2f}" for k, v in c.items()))
        return total, reasons

    def search(self, collection, query, k):
        vec = "[" + ",".join(f"{x:.7f}" for x in np.asarray(query).reshape(-1)) + "]"
        sql = ("SELECT ref_id, 1 - (embedding <=> %s::vector) AS score, metadata "
               "FROM embeddings WHERE (%s::text IS NULL OR collection = %s::text) "
               "ORDER BY embedding <=> %s::vector LIMIT %s")