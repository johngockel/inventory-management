<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from '../composables/useI18n'
import LanguageSwitcher from './LanguageSwitcher.vue'
import ProfileMenu from './ProfileMenu.vue'

defineProps({
  collapsed: { type: Boolean, default: false },
  mobileOpen: { type: Boolean, default: false }
})

const emit = defineEmits(['toggle-collapse', 'show-profile-details', 'show-tasks'])

const { t } = useI18n()
const route = useRoute()

// Icons are 20x20 stroke paths (currentColor), no icon font.
const navItems = computed(() => [
  { path: '/', label: t('nav.overview'), icon: ['M3 10.5L10 4l7 6.5', 'M5 9v7h4v-4h2v4h4V9'] },
  { path: '/inventory', label: t('nav.inventory'), icon: ['M3 6l7-3 7 3-7 3-7-3z', 'M3 6v8l7 3 7-3V6', 'M10 9v8'] },
  { path: '/orders', label: t('nav.orders'), icon: ['M5 3h10v14H5z', 'M8 7h4', 'M8 10h4', 'M8 13h2'] },
  { path: '/spending', label: t('nav.finance'), icon: ['M10 2.5v15', 'M13.5 6c-.6-1-1.9-1.5-3.5-1.5-2 0-3.5 1-3.5 2.5s1.5 2.2 3.5 2.5 3.5 1 3.5 2.5-1.500 2.500-3.500 2.500c-1.600 0-2.900-.5-3.500-1.500'] },
  { path: '/demand', label: t('nav.demandForecast'), icon: ['M3 16l4-5 3 3 6-8', 'M12 6h4v4'] },
  { path: '/restocking', label: t('nav.restocking'), icon: ['M16 10a6 6 0 10-1.800 4.300', 'M16 4v4h-4'] },
  // Literal on purpose: there is no nav.reports i18n key.
  { path: '/reports', label: 'Reports', icon: ['M4 16V9', 'M10 16V4', 'M16 16v-5'] }
])

const isActive = (path) => route.path === path
</script>

<template>
  <aside
    class="app-sidebar"
    :class="{ collapsed, 'mobile-open': mobileOpen }"
    :aria-label="t('nav.mainNavigation')"
  >
    <div class="sidebar-brand">
      <div class="logo-mark" aria-hidden="true">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 6l7-3 7 3-7 3-7-3z" />
          <path d="M3 6v8l7 3 7-3V6" />
        </svg>
      </div>
      <div class="brand-text">
        <h1 class="brand-name">{{ t('nav.companyName') }}</h1>
        <span class="brand-subtitle">{{ t('nav.subtitle') }}</span>
      </div>
    </div>

    <nav class="sidebar-nav">
      <ul class="nav-list">
        <li v-for="item in navItems" :key="item.path">
          <router-link
            :to="item.path"
            class="nav-link"
            :class="{ active: isActive(item.path) }"
            :aria-current="isActive(item.path) ? 'page' : undefined"
            :title="collapsed ? item.label : undefined"
            :aria-label="item.label"
          >
            <svg class="nav-icon" width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path v-for="d in item.icon" :key="d" :d="d" />
            </svg>
            <span class="nav-label">{{ item.label }}</span>
          </router-link>
        </li>
      </ul>
    </nav>

    <div class="sidebar-footer">
      <LanguageSwitcher />
      <ProfileMenu
        @show-profile-details="emit('show-profile-details')"
        @show-tasks="emit('show-tasks')"
      />
      <button
        type="button"
        class="collapse-toggle"
        :aria-label="collapsed ? t('nav.expandSidebar') : t('nav.collapseSidebar')"
        :aria-expanded="!collapsed"
        @click="emit('toggle-collapse')"
      >
        <svg class="collapse-icon" width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M12 5l-5 5 5 5" />
        </svg>
        <span class="nav-label">{{ collapsed ? t('nav.expand') : t('nav.collapse') }}</span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
/*
 * The aside itself does not clip (overflow: visible) so the language/profile
 * dropdowns, which are wider than the sidebar, can overlay the content.
 * Scrolling is handled by .sidebar-nav instead of the aside.
 */
.app-sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  z-index: 110;
  min-width: 0;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border);
  min-height: 4.5rem;
}

.logo-mark {
  width: 2.25rem;
  height: 2.25rem;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius);
  background: var(--color-primary);
  color: var(--color-surface);
}

.brand-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.brand-name {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.025em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.brand-subtitle {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4) var(--space-3);
}

.nav-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.nav-link,
.collapse-toggle {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  padding: var(--space-3);
  border: none;
  background: none;
  border-radius: var(--radius);
  color: var(--color-text-muted);
  font-family: inherit;
  font-size: 0.938rem;
  font-weight: 500;
  text-decoration: none;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.nav-link:hover,
.collapse-toggle:hover {
  color: var(--color-text);
  background: #f1f5f9;
}

.nav-link.active {
  color: var(--color-primary);
  background: #eff6ff;
}

.nav-icon,
.collapse-icon {
  flex-shrink: 0;
}

.nav-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-footer {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3);
  border-top: 1px solid var(--color-border);
}

/* Footer widgets fill the sidebar width. */
.sidebar-footer :deep(.language-button),
.sidebar-footer :deep(.profile-button) {
  width: 100%;
}

.sidebar-footer :deep(.profile-name) {
  flex: 1;
  text-align: left;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-footer :deep(.language-label) {
  flex: 1;
  text-align: left;
}

/* Footer sits at the bottom of the viewport, so dropdowns open upward. */
.sidebar-footer :deep(.dropdown-menu) {
  top: auto;
  bottom: calc(100% + var(--space-2));
  left: 0;
  right: auto;
}

.collapse-toggle {
  display: none;
}

.collapse-toggle .collapse-icon {
  transition: transform 0.2s ease;
}

/* Focus rings */
.nav-link:focus-visible,
.collapse-toggle:focus-visible,
.sidebar-footer :deep(button:focus-visible) {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

/* Desktop */
@media (min-width: 768px) {
  .collapse-toggle {
    display: flex;
  }

  .app-sidebar.collapsed .brand-text,
  .app-sidebar.collapsed .nav-label,
  .app-sidebar.collapsed :deep(.language-label),
  .app-sidebar.collapsed :deep(.profile-name),
  .app-sidebar.collapsed :deep(.chevron) {
    display: none;
  }

  .app-sidebar.collapsed .sidebar-brand {
    justify-content: center;
    padding-left: var(--space-2);
    padding-right: var(--space-2);
  }

  .app-sidebar.collapsed .nav-link,
  .app-sidebar.collapsed .collapse-toggle,
  .app-sidebar.collapsed :deep(.language-button),
  .app-sidebar.collapsed :deep(.profile-button) {
    justify-content: center;
  }

  .app-sidebar.collapsed :deep(.language-button),
  .app-sidebar.collapsed :deep(.profile-button) {
    padding-left: var(--space-2);
    padding-right: var(--space-2);
  }

  .app-sidebar.collapsed .collapse-icon {
    transform: rotate(180deg);
  }
}

/* Mobile: off-canvas drawer */
@media (max-width: 767px) {
  .app-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: var(--sidebar-width);
    z-index: 200;
    transform: translateX(-100%);
    visibility: hidden;
    transition: transform 0.25s ease, visibility 0s linear 0.25s;
  }

  .app-sidebar.mobile-open {
    transform: translateX(0);
    visibility: visible;
    transition: transform 0.25s ease, visibility 0s;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
  }

  /* Keep the dropdown inside the 240px drawer. */
  .sidebar-footer :deep(.dropdown-menu) {
    min-width: 0;
    width: calc(var(--sidebar-width) - var(--space-6));
  }
}
</style>
