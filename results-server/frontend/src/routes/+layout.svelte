<script lang="ts">
  import '../app.css';
  import { page } from '$app/stores';

  const navItems = [
    { href: '/explorer', label: 'Results Explorer', icon: '📊' },
    { href: '/saved-views', label: 'Saved Views', icon: '💾' },
    { href: '/settings', label: 'Settings', icon: '⚙️' },
  ];

  $: currentPath = $page.url.pathname;
</script>

<div class="flex min-h-screen">
  <!-- Sidebar -->
  <aside class="w-64 bg-surface-900 border-r border-surface-700 flex flex-col">
    <!-- Logo -->
    <div class="p-4 border-b border-surface-700">
      <a href="/" class="flex items-center gap-3">
        <div class="w-10 h-10 bg-gradient-to-br from-primary-500 to-accent-500 rounded-lg flex items-center justify-center text-xl font-bold">
          B
        </div>
        <div>
          <h1 class="text-lg font-semibold text-surface-100">BenchPRO</h1>
          <p class="text-xs text-surface-500">Results Portal</p>
        </div>
      </a>
    </div>

    <!-- Navigation -->
    <nav class="flex-1 p-4">
      <ul class="space-y-1">
        {#each navItems as item}
          <li>
            <a
              href={item.href}
              class="flex items-center gap-3 px-3 py-2 rounded-lg transition-colors {currentPath.startsWith(item.href)
                ? 'bg-primary-500/20 text-primary-400'
                : 'text-surface-400 hover:text-surface-100 hover:bg-surface-800'}"
            >
              <span class="text-lg">{item.icon}</span>
              <span class="font-medium">{item.label}</span>
            </a>
          </li>
        {/each}
      </ul>
    </nav>

    <!-- Footer -->
    <div class="p-4 border-t border-surface-700">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 bg-surface-700 rounded-full flex items-center justify-center text-surface-400">
          👤
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-surface-200 truncate">Development User</p>
          <p class="text-xs text-surface-500">Admin</p>
        </div>
      </div>
    </div>
  </aside>

  <!-- Main content -->
  <main class="flex-1 overflow-auto">
    <slot />
  </main>
</div>
