<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrency, formatCurrencyWithDecimals } from '../utils/currency'

const { t, currentCurrency } = useI18n()

const demandItems = ref([])
const budget = ref(50000)
const loading = ref(true)
const error = ref(null)
const submitting = ref(false)
const submitError = ref(null)
const confirmation = ref(null)

const money = (amount) => formatCurrency(amount, currentCurrency.value)
const unitMoney = (amount) => formatCurrencyWithDecimals(amount, currentCurrency.value, 2)

const recommendations = computed(() => {
  const growing = demandItems.value
    .map(item => ({ ...item, growth: item.forecasted_demand - item.current_demand }))
    .filter(item => item.growth > 0)
    .sort((a, b) => b.growth - a.growth)

  // Greedy fill: an item that does not fit the remaining budget is skipped
  // (not a stop condition) so smaller, lower-growth items further down the
  // list can still use up the leftover budget.
  let remaining = budget.value
  const picked = []
  for (const item of growing) {
    const lineTotal = item.growth * item.unit_cost
    if (lineTotal <= remaining) {
      picked.push({
        sku: item.item_sku,
        name: item.item_name,
        trend: item.trend,
        quantity: item.growth,
        unit_cost: item.unit_cost,
        line_total: lineTotal,
        lead_time_days: item.lead_time_days,
        supplier: item.supplier
      })
      remaining -= lineTotal
    }
  }
  return picked
})

const allocated = computed(() => recommendations.value.reduce((sum, r) => sum + r.line_total, 0))
const remainingBudget = computed(() => budget.value - allocated.value)

const loadDemand = async () => {
  try {
    loading.value = true
    error.value = null
    demandItems.value = await api.getDemandForecasts()
  } catch (err) {
    error.value = t('restocking.errorLoad')
    console.error('Failed to load demand forecasts:', err)
  } finally {
    loading.value = false
  }
}

const formatDate = (dateString) => {
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return dateString
  return date.toLocaleDateString(useI18n().currentLocale.value === 'ja' ? 'ja-JP' : 'en-US', {
    year: 'numeric', month: 'short', day: 'numeric'
  })
}

const placeOrder = async () => {
  if (recommendations.value.length === 0 || submitting.value) return
  submitting.value = true
  submitError.value = null
  confirmation.value = null
  try {
    const payload = {
      items: recommendations.value.map(r => ({ sku: r.sku, quantity: r.quantity }))
    }
    const order = await api.createPurchaseOrder(payload)
    confirmation.value = {
      orderNumber: order.order_number,
      deliveryDate: formatDate(order.expected_delivery_date)
    }
    // Reset selection
    budget.value = 0
  } catch (err) {
    submitError.value = err.response?.data?.detail || t('restocking.errorSubmit')
    console.error('Failed to place purchase order:', err)
  } finally {
    submitting.value = false
  }
}

onMounted(loadDemand)
</script>

<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.subtitle') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card budget-card">
        <div class="budget-row">
          <label for="budget-slider" class="budget-label">{{ t('restocking.budgetLabel') }}</label>
          <span class="budget-value">{{ money(budget) }}</span>
        </div>
        <input
          id="budget-slider"
          v-model.number="budget"
          type="range"
          min="0"
          max="100000"
          step="1000"
          class="budget-slider"
        />
        <div class="budget-summary">
          <div>
            <span class="summary-label">{{ t('restocking.allocated') }}</span>
            <span class="summary-value">{{ money(allocated) }}</span>
          </div>
          <div>
            <span class="summary-label">{{ t('restocking.remaining') }}</span>
            <span class="summary-value">{{ money(remainingBudget) }}</span>
          </div>
        </div>
      </div>

      <div v-if="confirmation" class="notice success-notice" role="status">
        {{ t('restocking.orderPlaced', { orderNumber: confirmation.orderNumber, deliveryDate: confirmation.deliveryDate }) }}
      </div>
      <div v-if="submitError" class="notice error-notice" role="alert">{{ submitError }}</div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }} ({{ recommendations.length }})</h3>
          <button
            type="button"
            class="btn-primary"
            :disabled="recommendations.length === 0 || submitting"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.submitting') : t('restocking.placeOrder') }}
          </button>
        </div>
        <div v-if="recommendations.length === 0" class="empty-state">
          {{ t('restocking.noRecommendations') }}
        </div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.columns.sku') }}</th>
                <th>{{ t('restocking.columns.name') }}</th>
                <th>{{ t('restocking.columns.trend') }}</th>
                <th class="num">{{ t('restocking.columns.quantity') }}</th>
                <th class="num">{{ t('restocking.columns.unitCost') }}</th>
                <th class="num">{{ t('restocking.columns.lineTotal') }}</th>
                <th class="num">{{ t('restocking.columns.leadTime') }}</th>
                <th>{{ t('restocking.columns.supplier') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="rec in recommendations" :key="rec.sku">
                <td><strong>{{ rec.sku }}</strong></td>
                <td>{{ rec.name }}</td>
                <td>
                  <span :class="['badge', rec.trend]">{{ t(`trends.${rec.trend}`) }}</span>
                </td>
                <td class="num">{{ rec.quantity.toLocaleString() }}</td>
                <td class="num">{{ unitMoney(rec.unit_cost) }}</td>
                <td class="num"><strong>{{ money(rec.line_total) }}</strong></td>
                <td class="num">{{ rec.lead_time_days }}</td>
                <td>{{ rec.supplier }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.budget-card {
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.budget-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.75rem;
}

.budget-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #0f172a;
}

.budget-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
}

.budget-slider {
  width: 100%;
  accent-color: #2563eb;
  cursor: pointer;
}

.budget-summary {
  display: flex;
  gap: 2rem;
  margin-top: 1rem;
}

.summary-label {
  display: block;
  font-size: 0.75rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.summary-value {
  font-size: 1.125rem;
  font-weight: 600;
  color: #0f172a;
}

.btn-primary {
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 0.5rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.notice {
  padding: 0.75rem 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

.success-notice {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
}

.error-notice {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
}

.empty-state {
  padding: 2rem;
  text-align: center;
  color: #64748b;
}

.num {
  text-align: right;
}
</style>
