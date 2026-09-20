import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'
import type { ApplyMode, Conformation, RegionDef, SamplingResult, ProteinParams } from '@/types'

export const useProteinStore = defineStore('protein', () => {
  const loading = ref(false)
  const result = ref<SamplingResult | null>(null)
  const selectedConformation = ref<Conformation | null>(null)
  const selectedRegion = ref('all')
  const regions = ref<RegionDef[]>([])
  /** 已有数据仍按旧口径判定、等待下次采样应用新口径时为 true */
  const staleCriteria = ref(false)

  async function fetchRegions() {
    const { data } = await axios.get('/api/regions')
    regions.value = data.regions
  }

  async function fetchRegionDefaults(): Promise<RegionDef[]> {
    const { data } = await axios.get('/api/regions/defaults')
    return data.regions
  }

  async function runSampling(params: ProteinParams) {
    loading.value = true
    try {
      const { data } = await axios.post('/api/sample', params)
      result.value = data
      selectedConformation.value = null
      selectedRegion.value = 'all'
      staleCriteria.value = false
    } finally { loading.value = false }
  }

  /** 保存新口径；mode 为 all 且已有数据时，立即用同一份口径重算落点与统计 */
  async function saveRegions(defs: RegionDef[], mode: ApplyMode) {
    const { data } = await axios.put('/api/regions', { regions: defs })
    regions.value = data.regions
    if (result.value) staleCriteria.value = true
    if (mode === 'all' && result.value) {
      const resp = await axios.post('/api/reclassify', { conformations: result.value.conformations })
      result.value = { ...result.value, conformations: resp.data.conformations, stats: resp.data.stats }
      staleCriteria.value = false
    }
  }

  function selectConformation(conf: Conformation) { selectedConformation.value = conf }
  function filterByRegion(region: string) { selectedRegion.value = region }

  return {
    loading, result, selectedConformation, selectedRegion, regions, staleCriteria,
    fetchRegions, fetchRegionDefaults, runSampling, saveRegions, selectConformation, filterByRegion
  }
})
