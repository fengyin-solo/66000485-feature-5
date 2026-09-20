import copy
import math
import random
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Protein Folding Analyzer")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

ANGLE_MIN, ANGLE_MAX = -180.0, 180.0
REGION_FIELDS = ("phi_min", "phi_max", "psi_min", "psi_max")

# 允许区间的默认口径；禁阻区为所有允许区间之外的区域
DEFAULT_REGIONS = [
    {"key": "alpha-helix",  "label": "α-螺旋区",   "target": "alpha-helix",
     "phi_min": -100.0, "phi_max": -30.0, "psi_min": -80.0,  "psi_max": -10.0},
    {"key": "beta-sheet",   "label": "β-折叠区 1", "target": "beta-sheet",
     "phi_min": -180.0, "phi_max": -45.0, "psi_min": 60.0,   "psi_max": 180.0},
    {"key": "beta-sheet-2", "label": "β-折叠区 2", "target": "beta-sheet",
     "phi_min": -180.0, "phi_max": -45.0, "psi_min": -180.0, "psi_max": -60.0},
    {"key": "left-helix",   "label": "左手螺旋区", "target": "left-helix",
     "phi_min": 20.0,   "phi_max": 100.0, "psi_min": -40.0,  "psi_max": 80.0},
]

app.state.regions = copy.deepcopy(DEFAULT_REGIONS)


def classify_region(phi: float, psi: float, regions: list) -> str:
    """按给定口径判定所属区间，列表顺序即优先匹配顺序"""
    for region in regions:
        if (region["phi_min"] <= phi <= region["phi_max"]
                and region["psi_min"] <= psi <= region["psi_max"]):
            return region["target"]
    return "disallowed"


def compute_stats(region_names: list) -> dict:
    return {"alpha": region_names.count("alpha-helix"),
            "beta": region_names.count("beta-sheet"),
            "left": region_names.count("left-helix"),
            "disallowed": region_names.count("disallowed")}


def lennard_jones_energy(phi: float, psi: float, sigma: float = 3.4, epsilon: float = 0.5) -> float:
    """Simplified Lennard-Jones potential for phi-psi angle pair"""
    r = math.sqrt(phi * phi + psi * psi) / 180.0 * 3.0 + 2.0
    r = max(r, 1.0)
    ratio = sigma / r
    return 4 * epsilon * (ratio ** 12 - ratio ** 6) + epsilon


class SampleRequest(BaseModel):
    residues: int = 10
    conformations: int = 1000


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


class RegionDefIn(BaseModel):
    key: str
    phi_min: Optional[float] = None
    phi_max: Optional[float] = None
    psi_min: Optional[float] = None
    psi_max: Optional[float] = None


class RegionsPayload(BaseModel):
    regions: list[RegionDefIn]


class ConformationIn(BaseModel):
    id: int
    phi: float
    psi: float
    energy: float
    cluster: str


class ReclassifyRequest(BaseModel):
    conformations: list[ConformationIn]


def validate_regions(payload: RegionsPayload) -> list:
    """逐项校验区间上下限，返回全部不合格项（空列表表示通过）"""
    errors = []
    known = {r["key"] for r in DEFAULT_REGIONS}
    seen = set()
    for r in payload.regions:
        if r.key not in known:
            errors.append({"region": r.key, "field": "key", "message": "未知区间"})
            continue
        seen.add(r.key)
        vals = {}
        for f in REGION_FIELDS:
            v = getattr(r, f)
            if v is None:
                errors.append({"region": r.key, "field": f, "message": "不能为空"})
            elif not (ANGLE_MIN <= v <= ANGLE_MAX):
                errors.append({"region": r.key, "field": f,
                               "message": f"超出允许范围 [{ANGLE_MIN:.0f}, {ANGLE_MAX:.0f}]"})
            else:
                vals[f] = v
        if "phi_min" in vals and "phi_max" in vals and vals["phi_min"] > vals["phi_max"]:
            errors.append({"region": r.key, "field": "phi", "message": "φ 下限不能大于上限"})
        if "psi_min" in vals and "psi_max" in vals and vals["psi_min"] > vals["psi_max"]:
            errors.append({"region": r.key, "field": "psi", "message": "ψ 下限不能大于上限"})
    for key in known - seen:
        errors.append({"region": key, "field": "key", "message": "缺少该区间的定义"})
    return errors


@app.get("/api/regions")
def get_regions():
    return {"regions": app.state.regions}


@app.get("/api/regions/defaults")
def get_region_defaults():
    return {"regions": DEFAULT_REGIONS}


@app.put("/api/regions")
def put_regions(payload: RegionsPayload):
    errors = validate_regions(payload)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})
    by_key = {r.key: r for r in payload.regions}
    new_regions = []
    for d in DEFAULT_REGIONS:
        src = by_key[d["key"]]
        new_regions.append({**d, **{f: getattr(src, f) for f in REGION_FIELDS}})
    app.state.regions = new_regions
    return {"regions": new_regions}


@app.post("/api/reclassify")
def reclassify_conformations(req: ReclassifyRequest):
    """用当前口径重算已有数据的所属区间与各区数量"""
    regions = app.state.regions
    confs = []
    for c in req.conformations:
        confs.append({"id": c.id, "phi": c.phi, "psi": c.psi, "energy": c.energy,
                      "region": classify_region(c.phi, c.psi, regions), "cluster": c.cluster})
    return {"conformations": confs, "stats": compute_stats([c["region"] for c in confs])}


@app.post("/api/sample", response_model=SampleResponse)
def sample_conformations(req: SampleRequest):
    regions = app.state.regions
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

    return SampleResponse(
        params={"residues": req.residues, "conformations": req.conformations},
        conformations=confs, energyRange=[e_min, e_max],
        stats=compute_stats([c["region"] for c in confs])
    )
