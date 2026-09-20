<template>
  <div class="config-card">
    <div class="config-header">
      <h3>⚙️ 区域判定口径（允许区间上下限，单位 °）</h3>
      <span class="hint">禁阻区为各允许区之外的部分——调整允许区（含左手螺旋）边界即同步调整禁阻区边界</span>
    </div>

    <table class="region-table">
      <thead>
        <tr>
          <th>区域</th>
          <th v-for="f in BOUND_FIELDS" :key="f">{{ BOUND_FIELD_LABELS[f] }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="d in drafts" :key="d.id">
          <td class="region-name">
            <span class="swatch" :style="{ background: d.color }"></span>{{ d.label }}
          </td>
          <td v-for="f in BOUND_FIELDS" :key="f">
            <el-input
              v-model="d[f]"
              size="small"
              :class="{ 'is-error': errors[errKey(d.id, f)] }"
              placeholder="-180 ~ 180"
              @input="clearRowErrors(d.id)"
            />
            <div class="err-msg" v-if="errors[errKey(d.id, f)]">{{ errors[errKey(d.id, f)] }}</div>
          </td>
        </tr>
      </tbody>
    </table>

    <el-alert v-if="errorList.length" type="error" :closable="false" class="err-summary" show-icon>
      <template #title>存在 {{ errorList.length }} 项不合格，未保存：</template>
      <ul class="err-list">
        <li v-for="(e, i) in errorList" :key="i">{{ e }}</li>
      </ul>
    </el-alert>

    <div class="actions">
      <el-radio-group v-model="mode">
        <el-radio label="all">同时重算已有数据</el-radio>
        <el-radio label="new">仅对后续新数据生效</el-radio>
      </el-radio-group>
      <div class="btns">
        <el-button size="small" @click="resetDefaults">恢复默认</el-button>
        <el-button size="small" type="primary" :loading="store.recalculating" @click="save">保存口径</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useProteinStore } from '../store/protein'
import type { ApplyMode } from '../types'
import {
  BOUND_FIELDS, BOUND_FIELD_LABELS, cloneDefaults, toDrafts,
  validateRegionDrafts, errKey, type RegionDraft, type RegionErrors,
} from '../utils/regions'

const store = useProteinStore()
const drafts = ref<RegionDraft[]>(toDrafts(store.regionDefs))
const errors = ref<RegionErrors>({})

// 生效范围直接绑定 store：切换到“同时重算已有数据”会立即按当前口径重算，保证落点与口径同步
const mode = computed<ApplyMode>({
  get: () => store.applyMode,
  set: (v) => {
    store.setApplyMode(v).catch(() => ElMessage.error('重算已有数据失败，请检查后端服务'))
  },
})

// 口径被外部更新（如保存生效）时同步草稿
watch(() => store.regionDefs, (defs) => { drafts.value = toDrafts(defs) }, { deep: true })

const errorList = computed(() =>
  Object.entries(errors.value).map(([key, msg]) => {
    const [id, field] = key.split('.') as [string, keyof typeof BOUND_FIELD_LABELS]
    const label = drafts.value.find(d => d.id === id)?.label ?? id
    return `「${label}」${BOUND_FIELD_LABELS[field]}：${msg}`
  })
)

function clearRowErrors(id: string) {
  const next = { ...errors.value }
  for (const f of BOUND_FIELDS) delete next[errKey(id, f)]
  errors.value = next
}

function resetDefaults() {
  drafts.value = toDrafts(cloneDefaults())
  errors.value = {}
}

async function save() {
  const { errors: errs, parsed } = validateRegionDrafts(drafts.value)
  errors.value = errs
  const n = Object.keys(errs).length
  if (n > 0) {
    ElMessage.error(`存在 ${n} 项不合格（上下限填反 / 越界 / 留空），未保存`)
    return
  }
  try {
    await store.applyRegionConfig(parsed, store.applyMode)
    ElMessage.success(store.applyMode === 'all'
      ? '已保存新口径，并按同一份口径重算已有数据'
      : '已保存新口径，将对后续采样数据生效')
  } catch {
    ElMessage.error('口径已保存，但重算已有数据失败，请检查后端服务')
  }
}
</script>

<style scoped>
.config-card { background: #fff; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,.08); }
.config-header { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.config-header h3 { color: #333; font-size: 15px; }
.hint { font-size: 12px; color: #999; }
.region-table { border-collapse: collapse; width: 100%; }
.region-table th, .region-table td { padding: 6px 8px; text-align: left; font-size: 13px; vertical-align: top; }
.region-table th { color: #666; font-weight: 600; border-bottom: 1px solid #eee; }
.region-name { white-space: nowrap; color: #333; }
.swatch { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 6px; vertical-align: middle; }
.region-table .el-input { width: 110px; }
.is-error :deep(.el-input__wrapper) { box-shadow: 0 0 0 1px #f56c6c inset; }
.err-msg { color: #f56c6c; font-size: 12px; margin-top: 2px; max-width: 150px; }
.err-summary { margin-top: 12px; }
.err-list { margin: 4px 0 0; padding-left: 18px; }
.actions { display: flex; justify-content: space-between; align-items: center; margin-top: 14px; flex-wrap: wrap; gap: 10px; }
</style>
