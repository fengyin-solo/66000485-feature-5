export interface Conformation {
  id: number
  phi: number
  psi: number
  energy: number
  region: string
  cluster: string
}

export interface ProteinParams {
  residues: number
  conformations: number
}

export interface SamplingResult {
  params: ProteinParams
  conformations: Conformation[]
  energyRange: [number, number]
  stats: { alpha: number; beta: number; left: number; disallowed: number }
}

/** 一个允许区间的判定口径：key 固定，上下限可编辑 */
export interface RegionDef {
  key: string
  label: string
  target: string
  phi_min: number
  phi_max: number
  psi_min: number
  psi_max: number
}

/** 编辑草稿允许留空，保存前再校验 */
export type RegionDraft = Omit<RegionDef, 'phi_min' | 'phi_max' | 'psi_min' | 'psi_max'> & {
  phi_min: number | null
  phi_max: number | null
  psi_min: number | null
  psi_max: number | null
}

export type BoundField = 'phi_min' | 'phi_max' | 'psi_min' | 'psi_max'

export interface BoundError {
  region: string
  field: string
  message: string
}

/** new = 仅对后续新数据生效；all = 同时重算已有数据 */
export type ApplyMode = 'new' | 'all'
