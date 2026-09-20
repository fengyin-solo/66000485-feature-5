export const ANGLE_MIN = -180;
export const ANGLE_MAX = 180;
export const REGION_COLORS = {
    'alpha-helix': '#4ecdc4',
    'beta-sheet': '#ff6b6b',
    'left-helix': '#45b7d1',
    'disallowed': '#dddddd',
};
export const REGION_LABELS = {
    'alpha-helix': 'α-螺旋',
    'beta-sheet': 'β-折叠',
    'left-helix': '左手螺旋',
    'disallowed': '禁阻区',
};
/** 默认允许区间，与后端 app/regions.py 的 DEFAULT_REGIONS 保持一致 */
export const DEFAULT_REGIONS = [
    { id: 'alpha-helix', label: 'α-螺旋', group: 'alpha-helix', color: REGION_COLORS['alpha-helix'], phiMin: -100, phiMax: -30, psiMin: -80, psiMax: -10 },
    { id: 'beta-sheet', label: 'β-折叠', group: 'beta-sheet', color: REGION_COLORS['beta-sheet'], phiMin: -180, phiMax: -45, psiMin: 60, psiMax: 180 },
    { id: 'beta-sheet-2', label: 'β-折叠（下）', group: 'beta-sheet', color: REGION_COLORS['beta-sheet'], phiMin: -180, phiMax: -45, psiMin: -180, psiMax: -60 },
    { id: 'left-helix', label: '左手螺旋', group: 'left-helix', color: REGION_COLORS['left-helix'], phiMin: 20, phiMax: 100, psiMin: -40, psiMax: 80 },
];
export function cloneDefaults() {
    return DEFAULT_REGIONS.map(r => ({ ...r }));
}
export const BOUND_FIELDS = ['phiMin', 'phiMax', 'psiMin', 'psiMax'];
export const BOUND_FIELD_LABELS = {
    phiMin: 'φ 下限', phiMax: 'φ 上限', psiMin: 'ψ 下限', psiMax: 'ψ 上限',
};
export function toDrafts(defs) {
    return defs.map(d => ({
        id: d.id, label: d.label, group: d.group, color: d.color,
        phiMin: String(d.phiMin), phiMax: String(d.phiMax),
        psiMin: String(d.psiMin), psiMax: String(d.psiMax),
    }));
}
export function errKey(id, field) {
    return `${id}.${field}`;
}
/**
 * 校验草稿并解析为数值区间。
 * 规则：不能为空、须为数字、须在 [-180, 180]、下限不得大于上限（填反）。
 */
export function validateRegionDrafts(drafts) {
    const errors = {};
    const parsed = drafts.map(d => ({
        id: d.id, label: d.label, group: d.group, color: d.color,
        phiMin: NaN, phiMax: NaN, psiMin: NaN, psiMax: NaN,
    }));
    drafts.forEach((d, i) => {
        for (const f of BOUND_FIELDS) {
            const raw = d[f].trim();
            const key = errKey(d.id, f);
            if (raw === '') {
                errors[key] = '不能为空';
                continue;
            }
            const v = Number(raw);
            if (Number.isNaN(v)) {
                errors[key] = '须为有效数字';
                continue;
            }
            if (v < ANGLE_MIN || v > ANGLE_MAX) {
                errors[key] = `须在 ${ANGLE_MIN} ~ ${ANGLE_MAX} 之间`;
                continue;
            }
            parsed[i][f] = v;
        }
        for (const [loF, hiF] of [['phiMin', 'phiMax'], ['psiMin', 'psiMax']]) {
            const lo = parsed[i][loF], hi = parsed[i][hiF];
            if (!Number.isNaN(lo) && !Number.isNaN(hi) && lo > hi) {
                const msg = `下限(${lo})大于上限(${hi})，上下限填反`;
                if (!errors[errKey(d.id, loF)])
                    errors[errKey(d.id, loF)] = msg;
                if (!errors[errKey(d.id, hiF)])
                    errors[errKey(d.id, hiF)] = msg;
            }
        }
    });
    return { errors, parsed };
}
