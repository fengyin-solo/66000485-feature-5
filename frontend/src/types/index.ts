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

/** 一个允许区间的判定口径：φ/ψ 各自的上下限 */
export interface RegionDef {
  id: string
  label: string
  /** 命中该区间时归入的区域（多个区间可同属一个区域，如两段 β-折叠） */
  group: string
  color: string
  phiMin: number
  phiMax: number
  psiMin: number
  psiMax: number
}

/** 口径生效范围：all=同时重算已有数据，new=仅对后续新数据生效 */
export type ApplyMode = 'all' | 'new'

/** 发送给后端的区间定义（与后端 RegionDefIn 对应） */
export interface RegionDefPayload {
  id: string
  group: string
  phiMin: number
  phiMax: number
  psiMin: number
  psiMax: number
}

export interface SamplingResult {
  params: ProteinParams
  conformations: Conformation[]
  energyRange: [number, number]
  stats: { alpha: number; beta: number; left: number; disallowed: number }
}
