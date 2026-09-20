<template>
  <div class="control-card">
    <div class="panel-head" @click="collapsed = !collapsed">
      <h3>⚙️ 区间判定口径（φ-ψ 允许区间上下限）</h3>
      <span class="toggle">{{ collapsed ? '展开 ▾' : '收起 ▴' }}</span>
    </div>

    <div v-show="!collapsed" class="panel-body">
      <el-alert
        v-if="store.staleCriteria"
        type="warning"
        :closable="false"
        class="stale-alert"
        title="当前图上的已有数据仍按旧口径判定，新口径将在下次采样时生效；如需立即同步，请选择“同时重算已有数据”后保存。"
      />

      <table class="region-table">
        <thead>
          <tr>
            <th>允许区间</th>
            <th>φ 下限 (°)</th>
            <th>φ 上限 (°)</th>
            <th>ψ 下限 (°)</th>
            <th>ψ 上限 (°)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in draft" :key="row.key">
            <td class="region-name">{{ row.label }}</td>
            <td v-for="f in BOUND_FIELDS" :key="f">
              <el-input-number
                v-model="row[f]"
                :controls="false"
                :precision="1"
                :step="5"
                placeholder="-180 ~ 180"
                class="bound-input"
                :class="{ 'is-invalid': invalidFields.has(row.key + ':' + f) }"
                @change="dirty = true"
              />
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="errors.length" class="error-list">
        <p v-for="(e, i) in errors" :key="i" class="error-item">
          ❌ {{ regionLabel(e.region) }} · {{ fieldLabel(e.field) }}：{{ e.message }}
        </p>
      </div>

      <div class="actions">
        <el-radio-group v-model="applyMode" class="apply-mode">
          <el-radio label="new">仅对后续新数据生效</el-radio>
          <el-radio label="all">同时重算已有数据</el-radio>
        </el-radio-group>
        <el-button type="primary" :loading="saving" @click="onSave">保存口径</el-button>
        <el-button @click="onResetDefaults">恢复默认</el-button>
      </div>

      <p class="hint">
        禁阻区 = 以上各允许区间之外的区域，调整任一区间的上下限即同步调整禁阻区边界；
        区间重叠时按列表顺序优先匹配。上下限取值范围 [-180°, 180°]，留空、越界或下限大于上限时不允许保存。
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useProteinStore } from '../store/protein'
import type { ApplyMode, BoundError, BoundField, RegionDef, RegionDraft } from '../types'

const store = useProteinStore()

const BOUND_FIELDS: BoundField[] = ['phi_min', 'phi_max', 'psi_min', 'psi_max']
const FIELD_LABELS: Record<string, string> = {
  phi_min: 'φ 下限', phi_max: 'φ 上限',
  psi_min: 'ψ 下限', psi_max: 'ψ 上限',
  phi: 'φ 区间', psi: 'ψ 区间', key: '区间'
}

const collapsed = ref(false)
const draft = ref<RegionDraft[]>([])
const errors = ref<BoundError[]>([])
const applyMode = ref<ApplyMode>('new')
const saving = ref(false)
const dirty = ref(false)

const clone = (defs: RegionDef[]): RegionDraft[] => JSON.parse(JSON.stringify(defs))

watch(() => store.regions, (defs) => {
  if (!dirty.value && defs.length) draft.value = clone(defs)
}, { immediate: true, deep: true })

const invalidFields = computed(() => {
  const set = new Set<string>()
  for (const e of errors.value) {
    if (e.field === 'phi') { set.add(e.region + ':phi_min'); set.add(e.region + ':phi_max') }
    else if (e.field === 'psi') { set.add(e.region + ':psi_min'); set.add(e.region + ':psi_max') }
    else set.add(e.region + ':' + e.field)
  }
  return set
})

function regionLabel(key: string) {
  return store.regions.find(r => r.key === key)?.label
    ?? draft.value.find(r => r.key === key)?.label ?? key
}
function fieldLabel(field: string) { return FIELD_LABELS[field] ?? field }

function validate(defs: RegionDraft[]): BoundError[] {
  const errs: BoundError[] = []
  for (const d of defs) {
    const vals: Partial<Record<BoundField, number>> = {}
    for (const f of BOUND_FIELDS) {
      const v = d[f]
      if (v === null || v === undefined || Number.isNaN(v)) {
        errs.push({ region: d.key, field: f, message: '不能为空' })
      } else if (v < -180 || v > 180) {
        errs.push({ region: d.key, field: f, message: '超出允许范围 [-180, 180]' })
      } else {
        vals[f] = v
      }
    }
    if (vals.phi_min !== undefined && vals.phi_max !== undefined && vals.phi_min > vals.phi_max)
      errs.push({ region: d.key, field: 'phi', message: '下限不能大于上限' })
    if (vals.psi_min !== undefined && vals.psi_max !== undefined && vals.psi_min > vals.psi_max)
      errs.push({ region: d.key, field: 'psi', message: '下限不能大于上限' })
  }
  return errs
}

async function onSave() {
  errors.value = validate(draft.value)
  if (errors.value.length) {
    ElMessage.error(`存在 ${errors.value.length} 项不合格，未保存`)
    return
  }
  saving.value = true
  try {
    await store.saveRegions(draft.value as RegionDef[], applyMode.value)
    dirty.value = false
    ElMessage.success(applyMode.value === 'all'
      ? '口径已保存，已有数据已按新口径重算'
      : '口径已保存，将对后续采样数据生效')
  } catch (e: any) {
    const srv = e?.response?.data?.detail?.errors
    if (Array.isArray(srv)) {
      errors.value = srv
      ElMessage.error('服务器校验未通过，未保存')
    } else {
      ElMessage.error('保存失败，请稍后重试')
    }
  } finally {
    saving.value = false
  }
}

async function onResetDefaults() {
  draft.value = clone(await store.fetchRegionDefaults())
  errors.value = []
  dirty.value = true
  ElMessage.info('已填入默认口径，点击“保存口径”后生效')
}
</script>

<style scoped>
.control-card { background: #fff; border-radius: 8px; padding: 16px 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,.08); }
.panel-head { display: flex; justify-content: space-between; align-items: center; cursor: pointer; user-select: none; }
.panel-head h3 { color: #333; font-size: 15px; }
.toggle { color: #999; font-size: 13px; }
.panel-body { margin-top: 12px; }
.stale-alert { margin-bottom: 12px; }
.region-table { border-collapse: collapse; width: 100%; }
.region-table th, .region-table td { padding: 6px 8px; text-align: left; font-size: 13px; }
.region-table th { color: #666; font-weight: 600; border-bottom: 1px solid #eee; }
.region-name { color: #333; white-space: nowrap; }
.bound-input { width: 110px; }
.bound-input.is-invalid :deep(.el-input__wrapper) { box-shadow: 0 0 0 1px #f56c6c inset; }
.error-list { margin: 10px 0 4px; padding: 10px 12px; background: #fef0f0; border-radius: 6px; }
.error-item { color: #f56c6c; font-size: 13px; line-height: 1.7; }
.actions { display: flex; align-items: center; gap: 12px; margin-top: 12px; flex-wrap: wrap; }
.apply-mode { margin-right: auto; }
.hint { margin-top: 10px; font-size: 12px; color: #999; line-height: 1.6; }
</style>
