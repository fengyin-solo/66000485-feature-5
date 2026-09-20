import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import type { Conformation, SamplingResult, ProteinParams, RegionDef, RegionDefPayload, ApplyMode } from '@/types'
import { cloneDefaults } from '@/utils/regions'

export const useProteinStore = defineStore('protein', () => {
  const loading = ref(false)
  const recalculating = ref(false)
  const result = ref<SamplingResult | null>(null)
  const selectedConformation = ref<Conformation | null>(null)
  const selectedRegion = ref('all')

  /** 当前生效的判定口径（允许区间上下限）及其生效范围 */
  const regionDefs = ref<RegionDef[]>(cloneDefaults())
  const applyMode = ref<ApplyMode>('all')

  /** 各区数量始终由当前落点数据派生，与图上配色保持同一份口径 */
  const regionStats = computed(() => {
    const stats: Record<string, number> = { 'alpha-helix': 0, 'beta-sheet': 0, 'left-helix': 0, disallowed: 0 }
    for (const c of result.value?.conformations || []) {
      stats[c.region] = (stats[c.region] ?? 0) + 1
    }
    return stats
  })

  function regionPayload(): RegionDefPayload[] {
    return regionDefs.value.map(({ id, group, phiMin, phiMax, psiMin, psiMax }) =>
      ({ id, group, phiMin, phiMax, psiMin, psiMax }))
  }

  async function runSampling(params: ProteinParams) {
    loading.value = true
    try {
      const { data } = await axios.post('/api/sample', { ...params, regions: regionPayload() })
      result.value = data
      selectedConformation.value = null
      selectedRegion.value = 'all'
    } finally { loading.value = false }
  }

  /** 按当前口径重算已有数据的区域判定（后端为口径唯一实现方） */
  async function reclassifyExisting() {
    const res = result.value
    if (!res || res.conformations.length === 0) return
    recalculating.value = true
    try {
      const { data } = await axios.post('/api/reclassify', {
        regions: regionPayload(),
        points: res.conformations.map(c => ({ id: c.id, phi: c.phi, psi: c.psi })),
      })
      const byId = new Map<number, string>((data.labels as { id: number; region: string }[]).map(l => [l.id, l.region]))
      result.value = {
        ...res,
        conformations: res.conformations.map(c => ({ ...c, region: byId.get(c.id) ?? c.region })),
      }
      if (selectedConformation.value) {
        selectedConformation.value =
          result.value.conformations.find(c => c.id === selectedConformation.value!.id) ?? null
      }
    } finally { recalculating.value = false }
  }

  /** 保存新口径；mode=all 时立即重算已有数据，mode=new 时仅作用于后续采样 */
  async function applyRegionConfig(defs: RegionDef[], mode: ApplyMode) {
    regionDefs.value = defs.map(d => ({ ...d }))
    applyMode.value = mode
    if (mode === 'all') await reclassifyExisting()
  }

  /** 切换生效范围；切到 all 时立即用当前口径重算已有数据，保证落点与口径同步 */
  async function setApplyMode(mode: ApplyMode) {
    applyMode.value = mode
    if (mode === 'all') await reclassifyExisting()
  }

  function selectConformation(conf: Conformation) { selectedConformation.value = conf }
  function filterByRegion(region: string) { selectedRegion.value = region }

  return {
    loading, recalculating, result, selectedConformation, selectedRegion,
    regionDefs, applyMode, regionStats,
    runSampling, applyRegionConfig, setApplyMode, selectConformation, filterByRegion,
  }
})
