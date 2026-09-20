import math
import random
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .regions import DEFAULT_REGIONS, classify_region, validate_regions

app = FastAPI(title="Protein Folding Analyzer")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def lennard_jones_energy(phi: float, psi: float, sigma: float = 3.4, epsilon: float = 0.5) -> float:
    """Simplified Lennard-Jones potential for phi-psi angle pair"""
    r = math.sqrt(phi * phi + psi * psi) / 180.0 * 3.0 + 2.0
    r = max(r, 1.0)
    ratio = sigma / r
    return 4 * epsilon * (ratio ** 12 - ratio ** 6) + epsilon

class RegionDefIn(BaseModel):
    id: str
    group: str
    phiMin: float
    phiMax: float
    psiMin: float
    psiMax: float

class SampleRequest(BaseModel):
    residues: int = 10
    conformations: int = 1000
    regions: Optional[List[RegionDefIn]] = None  # 未提供时使用默认口径

class PointIn(BaseModel):
    id: int
    phi: float
    psi: float

class ReclassifyRequest(BaseModel):
    regions: List[RegionDefIn]
    points: List[PointIn]

class ConformationOut(BaseModel):
    id: int
    phi: float
    psi: float
    energy: float
    region: str
    cluster: str

class SampleResponse(BaseModel):
    params: dict
    conformations: list[ConformationOut]
    energyRange: list[float]
    stats: dict

def resolve_regions(regions: Optional[List[RegionDefIn]]) -> list:
    """取请求自带口径；缺省用默认。口径不合格时拒绝（422）。"""
    if not regions:
        return DEFAULT_REGIONS
    raw = [r.model_dump() for r in regions]
    errors = validate_regions(raw)
    if errors:
        raise HTTPException(status_code=422, detail=errors)
    return raw

def region_stats(labels: list) -> dict:
    return {"alpha": labels.count("alpha-helix"), "beta": labels.count("beta-sheet"),
            "left": labels.count("left-helix"), "disallowed": labels.count("disallowed")}

@app.post("/api/sample", response_model=SampleResponse)
def sample_conformations(req: SampleRequest):
    regions = resolve_regions(req.regions)
    confs = []
    for i in range(req.conformations):
        phi = random.uniform(-180, 180)
        psi = random.uniform(-180, 180)
        energy = lennard_jones_energy(phi, psi) + random.gauss(0, 0.05)
        region = classify_region(phi, psi, regions)
        confs.append({
            "id": i + 1, "phi": round(phi, 2), "psi": round(psi, 2),
            "energy": round(energy, 3), "region": region
        })

    energies = [c["energy"] for c in confs]
    e_min, e_max = min(energies), max(energies)
    clusters = ["low-energy", "mid-energy", "high-energy"]
    for c in confs:
        t = (c["energy"] - e_min) / (e_max - e_min or 1)
        c["cluster"] = clusters[0] if t < 0.33 else (clusters[1] if t < 0.67 else clusters[2])

    labels = [c["region"] for c in confs]
    return SampleResponse(
        params={"residues": req.residues, "conformations": req.conformations},
        conformations=confs, energyRange=[e_min, e_max], stats=region_stats(labels)
    )

@app.post("/api/reclassify")
def reclassify_conformations(req: ReclassifyRequest):
    """按新口径重算已有数据：返回每个点的区域判定与各区数量。"""
    regions = resolve_regions(req.regions)
    labels = [{"id": p.id, "region": classify_region(p.phi, p.psi, regions)} for p in req.points]
    return {"labels": labels, "stats": region_stats([l["region"] for l in labels])}
