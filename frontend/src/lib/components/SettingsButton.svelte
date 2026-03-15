<script lang="ts">
  import { onMount } from 'svelte';
  import { Settings } from '@lucide/svelte';
  import { getStatus } from '$lib/api';
  import type { StatusResponse } from '$lib/types';

  let status: StatusResponse | null = $state(null);
  let error = $state(false);

  onMount(async () => {
    try {
      status = await getStatus();
    } catch {
      error = true;
    }
  });

  function getDotColor(): string | null {
    if (error) return 'bg-red-500';
    if (status && !status.api_key_configured) return 'bg-yellow-500';
    return null;
  }

  const dotColor = $derived(getDotColor());
</script>

<a
  href="/settings"
  class="relative flex items-center justify-center w-8 h-8 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
  title="Settings"
>
  <Settings class="w-4 h-4" />
  {#if dotColor}
    <span class="absolute top-0.5 right-0.5 w-2 h-2 rounded-full {dotColor} ring-1 ring-background"></span>
  {/if}
</a>
