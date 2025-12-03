<script lang="ts">
  import { onMount } from 'svelte';
  import { taskRuns, filters, fetchTaskRuns, updateFilters, resetFilters, hasActiveFilters } from '$lib/stores/taskRuns';
  import { formatDate, formatDuration, getStatusBgColor } from '$lib/utils/format';
  import Chart from '$lib/components/Chart.svelte';

  let viewMode: 'table' | 'chart' = 'table';
  let chartType: 'line' | 'scatter' | 'bar' = 'scatter';

  onMount(() => {
    fetchTaskRuns();
  });

  function handleFilterSubmit() {
    fetchTaskRuns(1, $taskRuns.perPage);
  }

  function handlePageChange(newPage: number) {
    fetchTaskRuns(newPage, $taskRuns.perPage);
  }

  function handleClearFilters() {
    resetFilters();
    fetchTaskRuns(1, $taskRuns.perPage);
  }

  function exportCSV() {
    const headers = ['ID', 'Label', 'System', 'Architecture', 'Nodes', 'Runtime', 'Status', 'Submit Time'];
    const rows = $taskRuns.items.map(t => [
      t.id,
      t.label,
      t.system,
      t.architecture || '',
      t.node_count || '',
      t.runtime_seconds?.toFixed(2) || '',
      t.status,
      t.submit_time,
    ]);

    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `benchpro-results-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }
</script>

<div class="p-6">
  <!-- Header -->
  <div class="flex items-center justify-between mb-6">
    <div>
      <h1 class="text-2xl font-bold text-surface-100">Results Explorer</h1>
      <p class="text-surface-400 mt-1">
        {$taskRuns.total} task run{$taskRuns.total !== 1 ? 's' : ''} found
      </p>
    </div>
    <div class="flex items-center gap-3">
      <!-- View toggle -->
      <div class="flex bg-surface-800 rounded-lg p-1">
        <button
          class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors {viewMode === 'table' ? 'bg-surface-700 text-surface-100' : 'text-surface-400 hover:text-surface-200'}"
          on:click={() => viewMode = 'table'}
        >
          Table
        </button>
        <button
          class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors {viewMode === 'chart' ? 'bg-surface-700 text-surface-100' : 'text-surface-400 hover:text-surface-200'}"
          on:click={() => viewMode = 'chart'}
        >
          Chart
        </button>
      </div>
      <button
        class="px-4 py-2 bg-surface-800 hover:bg-surface-700 text-surface-200 rounded-lg text-sm font-medium transition-colors"
        on:click={exportCSV}
      >
        Export CSV
      </button>
    </div>
  </div>

  <div class="flex gap-6">
    <!-- Filters sidebar -->
    <aside class="w-72 flex-shrink-0">
      <div class="bg-surface-900 rounded-xl p-4 border border-surface-700">
        <div class="flex items-center justify-between mb-4">
          <h2 class="font-semibold text-surface-200">Filters</h2>
          {#if $hasActiveFilters}
            <button
              class="text-xs text-primary-400 hover:text-primary-300"
              on:click={handleClearFilters}
            >
              Clear all
            </button>
          {/if}
        </div>

        <form on:submit|preventDefault={handleFilterSubmit} class="space-y-4">
          <!-- System -->
          <div>
            <label class="block text-sm text-surface-400 mb-1.5">System</label>
            <input
              type="text"
              placeholder="e.g., stampede3"
              class="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-surface-100 text-sm placeholder-surface-500 focus:border-primary-500 focus:outline-none"
              bind:value={$filters.system[0]}
              on:input={(e) => updateFilters({ system: e.currentTarget.value ? [e.currentTarget.value] : [] })}
            />
          </div>

          <!-- Architecture -->
          <div>
            <label class="block text-sm text-surface-400 mb-1.5">Architecture</label>
            <input
              type="text"
              placeholder="e.g., intel_spr"
              class="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-surface-100 text-sm placeholder-surface-500 focus:border-primary-500 focus:outline-none"
              bind:value={$filters.architecture}
              on:input={(e) => updateFilters({ architecture: e.currentTarget.value })}
            />
          </div>

          <!-- Benchmark Label -->
          <div>
            <label class="block text-sm text-surface-400 mb-1.5">Benchmark</label>
            <input
              type="text"
              placeholder="e.g., lammps"
              class="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-surface-100 text-sm placeholder-surface-500 focus:border-primary-500 focus:outline-none"
              bind:value={$filters.benchmarkLabel}
              on:input={(e) => updateFilters({ benchmarkLabel: e.currentTarget.value })}
            />
          </div>

          <!-- Node Count Range -->
          <div>
            <label class="block text-sm text-surface-400 mb-1.5">Node Count</label>
            <div class="flex gap-2">
              <input
                type="number"
                placeholder="Min"
                class="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-surface-100 text-sm placeholder-surface-500 focus:border-primary-500 focus:outline-none"
                on:input={(e) => updateFilters({ nodeCountMin: e.currentTarget.value ? parseInt(e.currentTarget.value) : null })}
              />
              <input
                type="number"
                placeholder="Max"
                class="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-surface-100 text-sm placeholder-surface-500 focus:border-primary-500 focus:outline-none"
                on:input={(e) => updateFilters({ nodeCountMax: e.currentTarget.value ? parseInt(e.currentTarget.value) : null })}
              />
            </div>
          </div>

          <!-- Status -->
          <div>
            <label class="block text-sm text-surface-400 mb-1.5">Status</label>
            <select
              class="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-surface-100 text-sm focus:border-primary-500 focus:outline-none"
              bind:value={$filters.status}
              on:change={(e) => updateFilters({ status: e.currentTarget.value })}
            >
              <option value="">All</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="partial">Partial</option>
            </select>
          </div>

          <!-- Submit -->
          <button
            type="submit"
            class="w-full px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            Apply Filters
          </button>
        </form>
      </div>
    </aside>

    <!-- Main content -->
    <div class="flex-1 min-w-0">
      {#if $taskRuns.loading}
        <div class="flex items-center justify-center h-64">
          <div class="text-surface-400">Loading...</div>
        </div>
      {:else if $taskRuns.error}
        <div class="bg-red-500/10 border border-red-500/50 rounded-xl p-4 text-red-400">
          {$taskRuns.error}
        </div>
      {:else if viewMode === 'table'}
        <!-- Table View -->
        <div class="bg-surface-900 rounded-xl border border-surface-700 overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-surface-700">
                  <th class="text-left px-4 py-3 text-surface-400 font-medium">Label</th>
                  <th class="text-left px-4 py-3 text-surface-400 font-medium">System</th>
                  <th class="text-left px-4 py-3 text-surface-400 font-medium">Arch</th>
                  <th class="text-right px-4 py-3 text-surface-400 font-medium">Nodes</th>
                  <th class="text-right px-4 py-3 text-surface-400 font-medium">Runtime</th>
                  <th class="text-center px-4 py-3 text-surface-400 font-medium">Status</th>
                  <th class="text-left px-4 py-3 text-surface-400 font-medium">Submitted</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-surface-800">
                {#each $taskRuns.items as task}
                  <tr class="hover:bg-surface-800/50 transition-colors">
                    <td class="px-4 py-3">
                      <a href="/task/{task.id}" class="text-primary-400 hover:text-primary-300 font-medium">
                        {task.label}
                      </a>
                    </td>
                    <td class="px-4 py-3 text-surface-300">{task.system}</td>
                    <td class="px-4 py-3 text-surface-400">{task.architecture || '—'}</td>
                    <td class="px-4 py-3 text-right text-surface-300">{task.node_count ?? '—'}</td>
                    <td class="px-4 py-3 text-right text-surface-300">
                      {task.runtime_seconds ? formatDuration(task.runtime_seconds) : '—'}
                    </td>
                    <td class="px-4 py-3 text-center">
                      <span class="inline-flex px-2 py-0.5 rounded text-xs font-medium {getStatusBgColor(task.status)}">
                        {task.status}
                      </span>
                    </td>
                    <td class="px-4 py-3 text-surface-400 text-sm">
                      {formatDate(task.submit_time)}
                    </td>
                  </tr>
                {:else}
                  <tr>
                    <td colspan="7" class="px-4 py-12 text-center text-surface-500">
                      No task runs found
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>

          <!-- Pagination -->
          {#if $taskRuns.pages > 1}
            <div class="flex items-center justify-between px-4 py-3 border-t border-surface-700">
              <p class="text-sm text-surface-400">
                Showing {($taskRuns.page - 1) * $taskRuns.perPage + 1} to {Math.min($taskRuns.page * $taskRuns.perPage, $taskRuns.total)} of {$taskRuns.total}
              </p>
              <div class="flex gap-1">
                <button
                  class="px-3 py-1.5 text-sm rounded-lg transition-colors {$taskRuns.page === 1 ? 'text-surface-600 cursor-not-allowed' : 'text-surface-300 hover:bg-surface-800'}"
                  disabled={$taskRuns.page === 1}
                  on:click={() => handlePageChange($taskRuns.page - 1)}
                >
                  Previous
                </button>
                {#each Array.from({ length: Math.min(5, $taskRuns.pages) }, (_, i) => {
                  const start = Math.max(1, Math.min($taskRuns.page - 2, $taskRuns.pages - 4));
                  return start + i;
                }) as pageNum}
                  <button
                    class="w-8 h-8 text-sm rounded-lg transition-colors {pageNum === $taskRuns.page ? 'bg-primary-600 text-white' : 'text-surface-300 hover:bg-surface-800'}"
                    on:click={() => handlePageChange(pageNum)}
                  >
                    {pageNum}
                  </button>
                {/each}
                <button
                  class="px-3 py-1.5 text-sm rounded-lg transition-colors {$taskRuns.page === $taskRuns.pages ? 'text-surface-600 cursor-not-allowed' : 'text-surface-300 hover:bg-surface-800'}"
                  disabled={$taskRuns.page === $taskRuns.pages}
                  on:click={() => handlePageChange($taskRuns.page + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          {/if}
        </div>
      {:else}
        <!-- Chart View -->
        <div class="bg-surface-900 rounded-xl border border-surface-700 p-4">
          <div class="flex items-center gap-4 mb-4">
            <span class="text-sm text-surface-400">Chart Type:</span>
            <div class="flex bg-surface-800 rounded-lg p-1">
              {#each ['scatter', 'line', 'bar'] as type}
                <button
                  class="px-3 py-1 text-sm rounded-md transition-colors {chartType === type ? 'bg-surface-700 text-surface-100' : 'text-surface-400 hover:text-surface-200'}"
                  on:click={() => chartType = type as typeof chartType}
                >
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </button>
              {/each}
            </div>
          </div>
          <Chart data={$taskRuns.items} type={chartType} />
        </div>
      {/if}
    </div>
  </div>
</div>

