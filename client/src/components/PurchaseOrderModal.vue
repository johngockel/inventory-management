<template>
  <Teleport to="body">
    <div v-if="isOpen && backlogItem" class="po-overlay" @click="close">
      <div class="po-container" role="dialog" aria-modal="true" :aria-label="title" @click.stop>
        <div class="po-header">
          <h3 class="po-title">{{ title }}</h3>
          <button class="po-close" :aria-label="t('common.close')" @click="close">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </button>
        </div>

        <div class="po-body">
          <div class="po-item">
            <div class="po-item-name">{{ translateProductName(backlogItem.item_name) }}</div>
            <div class="po-item-sku">{{ t('purchaseOrderModal.sku') }}: {{ backlogItem.item_sku }}</div>
          </div>

          <!-- Create mode -->
          <form v-if="mode !== 'view'" id="po-form" class="po-form" @submit.prevent="submit">
            <div class="po-stats">
              <div class="po-stat">
                <div class="po-label">{{ t('purchaseOrderModal.quantityNeeded') }}</div>
                <div class="po-value">{{ backlogItem.quantity_needed }}</div>
              </div>
              <div class="po-stat">
                <div class="po-label">{{ t('purchaseOrderModal.quantityShort') }}</div>
                <div class="po-value short">{{ shortage }}</div>
              </div>
            </div>

            <label class="po-label" for="po-quantity">{{ t('purchaseOrderModal.orderQuantity') }}</label>
            <input
              id="po-quantity"
              v-model.number="quantity"
              type="number"
              min="1"
              step="1"
              class="po-input"
              :disabled="submitting"
            />
            <p class="po-hint">{{ t('purchaseOrderModal.pricingHint') }}</p>
          </form>

          <!-- View mode -->
          <div v-else>
            <div v-if="loadingPO" class="po-state">{{ t('common.loading') }}</div>
            <div v-else-if="existingPO" class="po-existing">
              <div class="po-stats">
                <div class="po-stat">
                  <div class="po-label">{{ t('purchaseOrderModal.orderNumber') }}</div>
                  <div class="po-value">{{ existingPO.order_number }}</div>
                </div>
                <div class="po-stat">
                  <div class="po-label">{{ t('purchaseOrderModal.status') }}</div>
                  <div class="po-value"><span class="po-badge">{{ existingPO.status }}</span></div>
                </div>
                <div class="po-stat">
                  <div class="po-label">{{ t('purchaseOrderModal.expectedDelivery') }}</div>
                  <div class="po-value">{{ formatDate(existingPO.expected_delivery_date) }}</div>
                </div>
                <div class="po-stat">
                  <div class="po-label">{{ t('purchaseOrderModal.totalCost') }}</div>
                  <div class="po-value">{{ money(existingPO.total_cost) }}</div>
                </div>
              </div>
              <ul class="po-lines">
                <li v-for="line in existingPO.items" :key="line.sku" class="po-line">
                  <span>{{ line.sku }} - {{ translateProductName(line.name) }}</span>
                  <span>{{ line.quantity }} x {{ money(line.unit_cost) }}</span>
                </li>
              </ul>
            </div>
            <div v-else class="po-state">{{ t('purchaseOrderModal.notFound') }}</div>
          </div>

          <div v-if="errorMessage" class="po-error" role="alert">{{ errorMessage }}</div>
        </div>

        <div class="po-footer">
          <button type="button" class="po-btn secondary" @click="close">
            {{ mode === 'view' ? t('common.close') : t('common.cancel') }}
          </button>
          <button
            v-if="mode !== 'view'"
            type="submit"
            form="po-form"
            class="po-btn primary"
            :disabled="submitting"
          >
            {{ submitting ? t('restocking.submitting') : t('purchaseOrderModal.submit') }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

export default {
  name: 'PurchaseOrderModal',
  props: {
    isOpen: { type: Boolean, default: false },
    backlogItem: { type: Object, default: null },
    mode: { type: String, default: 'create' }
  },
  emits: ['close', 'po-created'],
  setup(props, { emit }) {
    const { t, currentCurrency, currentLocale, translateProductName } = useI18n()

    const quantity = ref(1)
    const submitting = ref(false)
    const errorMessage = ref(null)
    const existingPO = ref(null)
    const loadingPO = ref(false)

    const shortage = computed(() => {
      if (!props.backlogItem) return 0
      return Math.max(props.backlogItem.quantity_needed - props.backlogItem.quantity_available, 0)
    })

    const title = computed(() =>
      props.mode === 'view' ? t('purchaseOrderModal.viewTitle') : t('purchaseOrderModal.createTitle')
    )

    const money = (amount) => formatCurrencyWithDecimals(amount, currentCurrency.value, 2)

    const formatDate = (dateString) => {
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return dateString || '-'
      return date.toLocaleDateString(currentLocale.value === 'ja' ? 'ja-JP' : 'en-US', {
        year: 'numeric', month: 'short', day: 'numeric'
      })
    }

    const close = () => emit('close')

    const submit = async () => {
      if (submitting.value || !props.backlogItem) return
      // Mirror the server rule (quantity > 0) so we fail fast; also rejects NaN/empty input
      if (!Number.isInteger(quantity.value) || quantity.value <= 0) {
        errorMessage.value = t('purchaseOrderModal.errorQuantity')
        return
      }
      submitting.value = true
      errorMessage.value = null
      try {
        // Only sku + quantity: the server looks up unit cost and lead time itself
        // Send the backlog id so the server can link the order back to this row
        const order = await api.createPurchaseOrder({
          items: [{ sku: props.backlogItem.item_sku, quantity: quantity.value }],
          backlog_item_id: props.backlogItem.id
        })
        emit('po-created', order)
      } catch (err) {
        errorMessage.value = err.response?.data?.detail || t('restocking.errorSubmit')
        console.error('Failed to place purchase order:', err)
      } finally {
        submitting.value = false
      }
    }

    // Find the order linked to this backlog row. Match by backlog_item_id, not SKU:
    // a restocking-page order for the same SKU must not show up here.
    const loadExistingPO = async () => {
      existingPO.value = props.backlogItem?.purchase_order || null
      if (existingPO.value || !props.backlogItem) return
      loadingPO.value = true
      try {
        const orders = await api.getPurchaseOrders() // newest first
        existingPO.value = orders.find(o => o.backlog_item_id === props.backlogItem.id) || null
      } catch (err) {
        errorMessage.value = err.response?.data?.detail || t('purchaseOrderModal.errorLoad')
        console.error('Failed to load purchase orders:', err)
      } finally {
        loadingPO.value = false
      }
    }

    const onKeydown = (event) => {
      if (event.key === 'Escape') close()
    }

    // Reset state on every open; listen for Escape only while open
    watch(
      () => [props.isOpen, props.backlogItem, props.mode],
      ([open]) => {
        if (open) {
          errorMessage.value = null
          quantity.value = shortage.value || 1
          existingPO.value = null
          if (props.mode === 'view') loadExistingPO()
          document.addEventListener('keydown', onKeydown)
        } else {
          document.removeEventListener('keydown', onKeydown)
        }
      },
      { immediate: true }
    )

    onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))

    return {
      t, translateProductName, quantity, submitting, errorMessage, existingPO, loadingPO,
      shortage, title, money, formatDate, close, submit
    }
  }
}
</script>

<style scoped>
.po-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 1rem;
}

.po-container {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);
  width: 100%;
  max-width: 520px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.po-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #e2e8f0;
}

.po-title { margin: 0; font-size: 1.125rem; color: #0f172a; }

.po-close {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 4px;
  display: flex;
}
.po-close:hover { color: #0f172a; }

.po-body { padding: 1.25rem; overflow-y: auto; }

.po-item { margin-bottom: 1rem; }
.po-item-name { font-weight: 600; color: #0f172a; }
.po-item-sku { font-size: 0.875rem; color: #64748b; }

.po-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.po-stat { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 0.75rem; }
.po-label { display: block; font-size: 0.75rem; color: #64748b; margin-bottom: 4px; }
.po-value { font-weight: 600; color: #0f172a; overflow-wrap: anywhere; }
.po-value.short { color: #ef4444; }

.po-input {
  width: 100%;
  box-sizing: border-box;
  padding: 0.5rem 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 1rem;
  color: #0f172a;
}
.po-input:focus { outline: 2px solid #3b82f6; outline-offset: 1px; }
.po-hint { font-size: 0.75rem; color: #64748b; margin: 0.5rem 0 0; }

.po-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.75rem;
  background: #dbeafe;
  color: #1d4ed8;
}

.po-lines { list-style: none; margin: 0; padding: 0; }
.po-line {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.5rem 0;
  border-bottom: 1px solid #e2e8f0;
  font-size: 0.875rem;
  color: #0f172a;
}

.po-state { color: #64748b; text-align: center; padding: 1rem 0; }

.po-error {
  margin-top: 1rem;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  font-size: 0.875rem;
}

.po-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 1rem 1.25rem;
  border-top: 1px solid #e2e8f0;
}

.po-btn {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid #e2e8f0;
}
.po-btn.secondary { background: #fff; color: #0f172a; }
.po-btn.primary { background: #0f172a; border-color: #0f172a; color: #fff; }
.po-btn:disabled { opacity: 0.6; cursor: not-allowed; }

@media (max-width: 480px) {
  .po-footer { flex-direction: column-reverse; }
  .po-btn { width: 100%; }
}
</style>
