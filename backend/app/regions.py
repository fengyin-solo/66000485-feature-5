"""Ramachandran 区域判定口径：默认区间、校验与分类的唯一实现。

采样(/api/sample)与重算(/api/reclassify)共用本模块，保证同一份口径。
"""

ANGLE_MIN = -180.0
ANGLE_MAX = 180.0

# 默认允许区间；禁阻区(disallowed)为所有允许区之外的部分
DEFAULT_REGIONS = [
    {"id": "alpha-helix",  "group": "alpha-helix", "phiMin": -100.0, "phiMax": -30.0, "psiMin": -80.0,  "psiMax": -10.0},
    {"id": "beta-sheet",   "group": "beta-sheet",  "phiMin": -180.0, "phiMax": -45.0, "psiMin": 60.0,   "psiMax": 180.0},
    {"id": "beta-sheet-2", "group": "beta-sheet",  "phiMin": -180.0, "phiMax": -45.0, "psiMin": -180.0, "psiMax": -60.0},
    {"id": "left-helix",   "group": "left-helix",  "phiMin": 20.0,   "phiMax": 100.0, "psiMin": -40.0,  "psiMax": 80.0},
]

_FIELDS = (("phi", "phiMin", "phiMax"), ("psi", "psiMin", "psiMax"))


def validate_regions(regions) -> list:
    """校验区间定义，返回错误信息列表（空列表表示合格）。

    规则：上下限不能为空、须落在 [-180, 180]、下限不得大于上限。
    """
    errors = []
    for r in regions:
        rid = r.get("id", "?")
        for axis, lo_key, hi_key in _FIELDS:
            lo, hi = r.get(lo_key), r.get(hi_key)
            if lo is None or hi is None:
                errors.append(f"{rid}: {axis} 上下限不能为空")
                continue
            if not (ANGLE_MIN <= lo <= ANGLE_MAX and ANGLE_MIN <= hi <= ANGLE_MAX):
                errors.append(f"{rid}: {axis} 上下限须位于 [{ANGLE_MIN:g}, {ANGLE_MAX:g}]")
            elif lo > hi:
                errors.append(f"{rid}: {axis} 下限({lo:g})大于上限({hi:g})")
    return errors


def classify_region(phi: float, psi: float, regions=None) -> str:
    """按给定区间判定 (phi, psi) 所属区域；不在任何允许区内则为 disallowed。"""
    for r in (regions or DEFAULT_REGIONS):
        if r["phiMin"] <= phi <= r["phiMax"] and r["psiMin"] <= psi <= r["psiMax"]:
            return r["group"]
    return "disallowed"
