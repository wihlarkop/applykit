<script lang="ts">
  import { Settings } from '@lucide/svelte';
  import { getStatus } from '$lib/api';
  import { settingsStore } from '$lib/settingsStore.svelte';
  import type { StatusResponse } from '$lib/types';

  let status: StatusResponse | null = $state(null);
  let error = $state(false);

  async function loadStatus() {
    try {
      status = await getStatus();
      error = false;
    } catch {
      error = true;
    }
  }

  $effect(() => {
    settingsStore.version;
    loadStatus();
  });

  const dotColor = $derived.by(() => {
    if (error) return 'bg-red-500';
    if (status !== null && !status.api_key_configured) return 'bg-yellow-500';
    return null;
  });
</script>

<a
  href="/settings"
  class="relative flex items-center justify-center w-8 h-8 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
  title="Settings"
  aria-label="Settings"
>
  <Settings class="w-4 h-4" />
  {#if dotColor}
    <span
      class="absolute top-0.5 right-0.5 w-2 h-2 rounded-full {dotColor} ring-1 ring-background"
    ></span>
  {/if}
</a>
