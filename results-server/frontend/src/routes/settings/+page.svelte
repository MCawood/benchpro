<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type ApiToken, type ApiTokenCreated } from '$lib/api/client';
  import { formatDate } from '$lib/utils/format';

  let tokens: ApiToken[] = [];
  let loading = true;
  let error: string | null = null;
  let newTokenName = '';
  let createdToken: ApiTokenCreated | null = null;
  let creating = false;

  onMount(() => {
    loadTokens();
  });

  async function loadTokens() {
    loading = true;
    error = null;

    try {
      const response = await api.listTokens();
      tokens = response.tokens;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load tokens';
    } finally {
      loading = false;
    }
  }

  async function createToken() {
    if (!newTokenName.trim()) return;

    creating = true;
    try {
      createdToken = await api.createToken(newTokenName);
      tokens = [createdToken, ...tokens];
      newTokenName = '';
    } catch (e) {
      alert('Failed to create token');
    } finally {
      creating = false;
    }
  }

  async function revokeToken(id: number) {
    if (!confirm('Are you sure you want to revoke this token? This cannot be undone.')) return;

    try {
      await api.revokeToken(id);
      tokens = tokens.filter(t => t.id !== id);
    } catch (e) {
      alert('Failed to revoke token');
    }
  }

  function copyToken() {
    if (createdToken) {
      navigator.clipboard.writeText(createdToken.token);
    }
  }
</script>

<div class="p-6 max-w-4xl">
  <h1 class="text-2xl font-bold text-surface-100 mb-6">Settings</h1>

  <!-- API Tokens Section -->
  <div class="bg-surface-900 rounded-xl border border-surface-700">
    <div class="p-6 border-b border-surface-700">
      <h2 class="text-lg font-semibold text-surface-200">API Tokens</h2>
      <p class="text-sm text-surface-400 mt-1">
        Personal access tokens for authenticating BenchPRO clients
      </p>
    </div>

    <!-- Create token -->
    <div class="p-6 border-b border-surface-700">
      <form on:submit|preventDefault={createToken} class="flex gap-3">
        <input
          type="text"
          placeholder="Token name (e.g., 'Stampede3 login1')"
          class="flex-1 px-4 py-2 bg-surface-800 border border-surface-700 rounded-lg text-surface-100 placeholder-surface-500 focus:border-primary-500 focus:outline-none"
          bind:value={newTokenName}
        />
        <button
          type="submit"
          class="px-4 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
          disabled={creating || !newTokenName.trim()}
        >
          {creating ? 'Creating...' : 'Create Token'}
        </button>
      </form>

      <!-- Newly created token -->
      {#if createdToken}
        <div class="mt-4 p-4 bg-green-500/10 border border-green-500/50 rounded-lg">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-medium text-green-400">Token created successfully!</span>
            <button
              class="text-xs text-green-400 hover:text-green-300"
              on:click={() => createdToken = null}
            >
              Dismiss
            </button>
          </div>
          <p class="text-xs text-surface-400 mb-2">
            Copy this token now. You won't be able to see it again.
          </p>
          <div class="flex gap-2">
            <code class="flex-1 px-3 py-2 bg-surface-950 rounded text-sm font-mono text-surface-200 overflow-x-auto">
              {createdToken.token}
            </code>
            <button
              class="px-3 py-2 bg-surface-800 hover:bg-surface-700 text-surface-300 rounded transition-colors"
              on:click={copyToken}
            >
              Copy
            </button>
          </div>
        </div>
      {/if}
    </div>

    <!-- Token list -->
    <div class="divide-y divide-surface-800">
      {#if loading}
        <div class="p-8 text-center text-surface-400">Loading tokens...</div>
      {:else if error}
        <div class="p-4 text-red-400">{error}</div>
      {:else if tokens.length === 0}
        <div class="p-8 text-center text-surface-500">
          No tokens yet. Create one to authenticate BenchPRO clients.
        </div>
      {:else}
        {#each tokens as token}
          <div class="p-4 flex items-center justify-between">
            <div>
              <div class="font-medium text-surface-200">{token.name}</div>
              <div class="text-sm text-surface-500">
                Created {formatDate(token.created_at)}
                {#if token.revoked_at}
                  <span class="text-red-400"> · Revoked</span>
                {/if}
              </div>
            </div>
            {#if !token.revoked_at}
              <button
                class="px-3 py-1.5 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors"
                on:click={() => revokeToken(token.id)}
              >
                Revoke
              </button>
            {/if}
          </div>
        {/each}
      {/if}
    </div>
  </div>
</div>

