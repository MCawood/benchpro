<script lang="ts">
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { api, type TaskRunDetail, type TaskProvenance } from '$lib/api/client';
  import { formatDate, formatDuration, getStatusBgColor, formatBytes } from '$lib/utils/format';

  let task: TaskRunDetail | null = null;
  let provenance: TaskProvenance | null = null;
  let loading = true;
  let error: string | null = null;
  let activeTab: 'summary' | 'fom' | 'provenance' = 'summary';
  let selectedArtifact: { id: number; content: string } | null = null;
  let artifactLoading = false;

  $: taskId = parseInt($page.params.id);

  onMount(async () => {
    await loadTask();
  });

  async function loadTask() {
    loading = true;
    error = null;

    try {
      task = await api.getTaskRun(taskId);
      provenance = await api.getTaskProvenance(taskId);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load task';
    } finally {
      loading = false;
    }
  }

  async function loadArtifact(id: number) {
    artifactLoading = true;
    try {
      const content = await api.getArtifactText(id, 50000);
      selectedArtifact = { id, content: content.content || '' };
    } catch (e) {
      console.error('Failed to load artifact:', e);
    } finally {
      artifactLoading = false;
    }
  }
</script>

<div class="p-6">
  <!-- Header -->
  <div class="mb-6">
    <a href="/explorer" class="text-sm text-surface-400 hover:text-surface-200 mb-2 inline-flex items-center gap-1">
      ← Back to Explorer
    </a>

    {#if task}
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-surface-100">{task.label}</h1>
          <p class="text-surface-400 mt-1">
            Task ID: {task.id} · UUID: <span class="font-mono text-xs">{task.task_uuid}</span>
          </p>
        </div>
        <span class="px-3 py-1 rounded-lg text-sm font-medium {getStatusBgColor(task.status)}">
          {task.status}
        </span>
      </div>
    {/if}
  </div>

  {#if loading}
    <div class="flex items-center justify-center h-64">
      <div class="text-surface-400">Loading task details...</div>
    </div>
  {:else if error}
    <div class="bg-red-500/10 border border-red-500/50 rounded-xl p-4 text-red-400">
      {error}
    </div>
  {:else if task}
    <!-- Tabs -->
    <div class="flex gap-1 mb-6 border-b border-surface-700">
      {#each [['summary', 'Summary'], ['fom', 'Figures of Merit'], ['provenance', 'Provenance']] as [id, label]}
        <button
          class="px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px {activeTab === id
            ? 'text-primary-400 border-primary-400'
            : 'text-surface-400 border-transparent hover:text-surface-200'}"
          on:click={() => activeTab = id as typeof activeTab}
        >
          {label}
        </button>
      {/each}
    </div>

    <!-- Tab content -->
    {#if activeTab === 'summary'}
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Task Info -->
        <div class="bg-surface-900 rounded-xl border border-surface-700 p-6">
          <h2 class="text-lg font-semibold text-surface-200 mb-4">Task Information</h2>
          <dl class="space-y-3">
            <div class="flex justify-between">
              <dt class="text-surface-400">System</dt>
              <dd class="text-surface-100 font-medium">{task.system}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-surface-400">Architecture</dt>
              <dd class="text-surface-100">{task.architecture || '—'}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-surface-400">Node Count</dt>
              <dd class="text-surface-100">{task.node_count ?? '—'}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-surface-400">Runtime</dt>
              <dd class="text-surface-100">{task.runtime_seconds ? formatDuration(task.runtime_seconds) : '—'}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-surface-400">BenchPRO Version</dt>
              <dd class="text-surface-100 font-mono text-sm">{task.benchpro_version || '—'}</dd>
            </div>
          </dl>
        </div>

        <!-- Timing -->
        <div class="bg-surface-900 rounded-xl border border-surface-700 p-6">
          <h2 class="text-lg font-semibold text-surface-200 mb-4">Timing</h2>
          <dl class="space-y-3">
            <div class="flex justify-between">
              <dt class="text-surface-400">Submitted</dt>
              <dd class="text-surface-100">{formatDate(task.submit_time)}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-surface-400">Started</dt>
              <dd class="text-surface-100">{task.start_time ? formatDate(task.start_time) : '—'}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-surface-400">Ended</dt>
              <dd class="text-surface-100">{task.end_time ? formatDate(task.end_time) : '—'}</dd>
            </div>
            <div class="flex justify-between">
              <dt class="text-surface-400">Created</dt>
              <dd class="text-surface-100">{formatDate(task.created_at)}</dd>
            </div>
          </dl>
        </div>
      </div>

    {:else if activeTab === 'fom'}
      <div class="bg-surface-900 rounded-xl border border-surface-700 overflow-hidden">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-surface-700">
              <th class="text-left px-4 py-3 text-surface-400 font-medium">Name</th>
              <th class="text-right px-4 py-3 text-surface-400 font-medium">Value</th>
              <th class="text-left px-4 py-3 text-surface-400 font-medium">Unit</th>
              <th class="text-center px-4 py-3 text-surface-400 font-medium">Type</th>
              <th class="text-center px-4 py-3 text-surface-400 font-medium">Primary</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-surface-800">
            {#each task.figures_of_merit as fom}
              <tr class="hover:bg-surface-800/50 {fom.is_primary ? 'bg-primary-500/5' : ''}">
                <td class="px-4 py-3 font-medium {fom.is_primary ? 'text-primary-400' : 'text-surface-100'}">
                  {fom.name}
                </td>
                <td class="px-4 py-3 text-right font-mono text-surface-200">
                  {typeof fom.value === 'number' ? fom.value.toLocaleString() : fom.value}
                </td>
                <td class="px-4 py-3 text-surface-400">{fom.unit || '—'}</td>
                <td class="px-4 py-3 text-center">
                  <span class="px-2 py-0.5 rounded text-xs {fom.value_type === 'numeric' ? 'bg-blue-500/20 text-blue-400' : 'bg-purple-500/20 text-purple-400'}">
                    {fom.value_type}
                  </span>
                </td>
                <td class="px-4 py-3 text-center">
                  {#if fom.is_primary}
                    <span class="text-primary-400">★</span>
                  {:else}
                    <span class="text-surface-600">—</span>
                  {/if}
                </td>
              </tr>
            {:else}
              <tr>
                <td colspan="5" class="px-4 py-8 text-center text-surface-500">
                  No figures of merit recorded
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

    {:else if activeTab === 'provenance' && provenance}
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Structured provenance -->
        <div class="lg:col-span-1 space-y-4">
          {#if provenance.modules?.length}
            <div class="bg-surface-900 rounded-xl border border-surface-700 p-4">
              <h3 class="text-sm font-semibold text-surface-300 mb-2">Modules</h3>
              <div class="space-y-1">
                {#each provenance.modules as mod}
                  <div class="text-sm font-mono text-surface-400">{mod}</div>
                {/each}
              </div>
            </div>
          {/if}

          {#if provenance.scheduler}
            <div class="bg-surface-900 rounded-xl border border-surface-700 p-4">
              <h3 class="text-sm font-semibold text-surface-300 mb-2">Scheduler</h3>
              <dl class="space-y-1 text-sm">
                {#each Object.entries(provenance.scheduler) as [key, value]}
                  <div class="flex justify-between">
                    <dt class="text-surface-500">{key}</dt>
                    <dd class="text-surface-300 font-mono">{value}</dd>
                  </div>
                {/each}
              </dl>
            </div>
          {/if}

          {#if provenance.git_commit}
            <div class="bg-surface-900 rounded-xl border border-surface-700 p-4">
              <h3 class="text-sm font-semibold text-surface-300 mb-2">Git Commit</h3>
              <div class="font-mono text-sm text-surface-400">{provenance.git_commit}</div>
            </div>
          {/if}
        </div>

        <!-- Artifacts -->
        <div class="lg:col-span-2">
          <div class="bg-surface-900 rounded-xl border border-surface-700">
            <div class="p-4 border-b border-surface-700">
              <h3 class="font-semibold text-surface-200">Artifacts</h3>
            </div>
            <div class="divide-y divide-surface-800">
              {#each provenance.artifacts as artifact}
                <div class="p-4 flex items-center justify-between">
                  <div>
                    <div class="font-medium text-surface-200">{artifact.name}</div>
                    <div class="text-sm text-surface-500">
                      {artifact.content_type} · {formatBytes(artifact.size_bytes)}
                    </div>
                  </div>
                  <button
                    class="px-3 py-1.5 text-sm bg-surface-800 hover:bg-surface-700 text-surface-300 rounded-lg transition-colors"
                    on:click={() => loadArtifact(artifact.id)}
                  >
                    View
                  </button>
                </div>
              {:else}
                <div class="p-8 text-center text-surface-500">
                  No artifacts available
                </div>
              {/each}
            </div>
          </div>

          <!-- Artifact viewer -->
          {#if selectedArtifact}
            <div class="mt-4 bg-surface-900 rounded-xl border border-surface-700">
              <div class="p-4 border-b border-surface-700 flex items-center justify-between">
                <h3 class="font-semibold text-surface-200">Artifact Content</h3>
                <button
                  class="text-surface-400 hover:text-surface-200"
                  on:click={() => selectedArtifact = null}
                >
                  ✕
                </button>
              </div>
              <pre class="p-4 text-sm font-mono text-surface-300 overflow-auto max-h-96 whitespace-pre-wrap">{selectedArtifact.content}</pre>
            </div>
          {/if}
        </div>
      </div>
    {/if}
  {/if}
</div>

