<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type SavedViewSummary } from '$lib/api/client';
  import { formatDate } from '$lib/utils/format';

  let views: SavedViewSummary[] = [];
  let loading = true;
  let error: string | null = null;
  let scope: 'all' | 'mine' | 'shared' = 'all';

  onMount(() => {
    loadViews();
  });

  async function loadViews() {
    loading = true;
    error = null;

    try {
      views = await api.listSavedViews(scope);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load saved views';
    } finally {
      loading = false;
    }
  }

  async function deleteView(id: number) {
    if (!confirm('Are you sure you want to delete this saved view?')) return;

    try {
      await api.deleteSavedView(id);
      views = views.filter(v => v.id !== id);
    } catch (e) {
      alert('Failed to delete saved view');
    }
  }

  $: if (scope) loadViews();
</script>

<div class="p-6">
  <div class="flex items-center justify-between mb-6">
    <div>
      <h1 class="text-2xl font-bold text-surface-100">Saved Views</h1>
      <p class="text-surface-400 mt-1">Saved filter and display configurations</p>
    </div>
  </div>

  <!-- Scope tabs -->
  <div class="flex gap-1 mb-6">
    {#each [['all', 'All Views'], ['mine', 'My Views'], ['shared', 'Shared']] as [value, label]}
      <button
        class="px-4 py-2 text-sm font-medium rounded-lg transition-colors {scope === value
          ? 'bg-primary-600 text-white'
          : 'bg-surface-800 text-surface-400 hover:text-surface-200'}"
        on:click={() => scope = value as typeof scope}
      >
        {label}
      </button>
    {/each}
  </div>

  {#if loading}
    <div class="flex items-center justify-center h-64">
      <div class="text-surface-400">Loading...</div>
    </div>
  {:else if error}
    <div class="bg-red-500/10 border border-red-500/50 rounded-xl p-4 text-red-400">
      {error}
    </div>
  {:else if views.length === 0}
    <div class="bg-surface-900 rounded-xl border border-surface-700 p-12 text-center">
      <div class="text-4xl mb-4">💾</div>
      <h3 class="text-lg font-semibold text-surface-200 mb-2">No saved views</h3>
      <p class="text-surface-400">Create a saved view from the Results Explorer to save your filters.</p>
    </div>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {#each views as view}
        <div class="bg-surface-900 rounded-xl border border-surface-700 p-4 hover:border-surface-600 transition-colors">
          <div class="flex items-start justify-between mb-2">
            <h3 class="font-semibold text-surface-200">{view.name}</h3>
            <span class="px-2 py-0.5 rounded text-xs {view.visibility === 'public' ? 'bg-green-500/20 text-green-400' : 'bg-surface-700 text-surface-400'}">
              {view.visibility}
            </span>
          </div>
          {#if view.description}
            <p class="text-sm text-surface-400 mb-3">{view.description}</p>
          {/if}
          <div class="flex items-center justify-between text-sm">
            <span class="text-surface-500">{formatDate(view.updated_at)}</span>
            <div class="flex gap-2">
              <a
                href="/explorer?view={view.id}"
                class="text-primary-400 hover:text-primary-300"
              >
                Load
              </a>
              <button
                class="text-red-400 hover:text-red-300"
                on:click={() => deleteView(view.id)}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

