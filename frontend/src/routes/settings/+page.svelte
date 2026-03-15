<script lang="ts">
  import { getSettings } from '$lib/api';
  import SettingsModal from '$lib/components/SettingsModal.svelte';
  import { settingsStore } from '$lib/settingsStore.svelte';
  import type { SettingsResponse } from '$lib/types';
  import { CircleAlert, CircleCheck, Cpu, Pencil, Plus, Settings } from '@lucide/svelte';

  let modalOpen = $state(false);
  let settings: SettingsResponse | null = $state(null);
  let loading = $state(true);

  $effect(() => {
    settingsStore.version; // refresh after saving
    loadSettings();
  });

  async function loadSettings() {
    loading = true;
    try {
      settings = await getSettings();
    } finally {
      loading = false;
    }
  }
</script>

<div class="max-w-2xl space-y-6">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold flex items-center gap-2">
        <Settings class="w-6 h-6 text-primary" />
        Settings
      </h1>
      <p class="text-sm text-muted-foreground mt-1">Manage your AI integrations.</p>
    </div>
    <button
      onclick={() => (modalOpen = true)}
      class="flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm hover:bg-primary/90 transition-colors"
    >
      <Plus class="w-4 h-4" />
      Add Integration
    </button>
  </div>

  <!-- Integrations list -->
  <div class="space-y-3">
    <h2 class="text-sm font-medium text-muted-foreground uppercase tracking-wide">Active Integrations</h2>

    {#if loading}
      <div class="border border-border rounded-lg p-4 bg-card animate-pulse h-20"></div>
    {:else if settings?.api_key_configured}
      <!-- Configured integration card -->
      <div class="border border-border rounded-lg p-4 bg-card flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-md bg-green-500/10 flex items-center justify-center">
            <Cpu class="w-5 h-5 text-green-600" />
          </div>
          <div>
            <p class="text-sm font-medium">{settings.model ?? 'LLM Provider'}</p>
            <div class="flex items-center gap-1.5 mt-0.5">
              <CircleCheck class="w-3.5 h-3.5 text-green-500" />
              <span class="text-xs text-muted-foreground">Connected
                {#if settings.source === 'env'}· from .env{/if}
              </span>
            </div>
          </div>
        </div>
        <button
          onclick={() => (modalOpen = true)}
          class="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm border border-border hover:bg-accent transition-colors text-muted-foreground"
        >
          <Pencil class="w-3.5 h-3.5" />
          Edit
        </button>
      </div>
    {:else}
      <!-- No integration configured -->
      <div class="border border-dashed border-border rounded-lg p-8 bg-card flex flex-col items-center gap-3 text-center">
        <div class="w-10 h-10 rounded-full bg-yellow-500/10 flex items-center justify-center">
          <CircleAlert class="w-5 h-5 text-yellow-500" />
        </div>
        <div>
          <p class="text-sm font-medium">No AI integration configured</p>
          <p class="text-xs text-muted-foreground mt-1">Add an integration to enable CV enhancement, cover letter generation, and CV import.</p>
        </div>
        <button
          onclick={() => (modalOpen = true)}
          class="flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm hover:bg-primary/90 mt-1"
        >
          <Plus class="w-4 h-4" />
          Add Integration
        </button>
      </div>
    {/if}
  </div>
</div>

<SettingsModal bind:open={modalOpen} />
