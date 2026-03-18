<script lang="ts">
  import { page } from '$app/state';
  import { getStatus } from '$lib/api';
  import type { StatusResponse } from '$lib/types';

  let status: StatusResponse | null = $state(null);
  let error = $state(false);

  // Re-fetch whenever the layout re-runs (e.g. after invalidateAll() from settings save)
  $effect(() => {
    page.data.isApiKeyConfigured;
    getStatus()
      .then((s) => { status = s; error = false; })
      .catch(() => { error = true; });
  });
</script>

<div class="flex items-center gap-2 text-sm">
  {#if error}
    <span class="size-2 rounded-full bg-red-500"></span>
    <span class="text-muted-foreground">Backend unreachable</span>
  {:else if status === null}
    <span class="size-2 rounded-full bg-muted animate-pulse"></span>
    <span class="text-muted-foreground">Connecting…</span>
  {:else if status.api_key_configured}
    <span class="size-2 rounded-full bg-green-500"></span>
    <span class="text-muted-foreground">
      {status.provider ?? 'LLM'} connected
    </span>
  {:else}
    <span class="size-2 rounded-full bg-yellow-500"></span>
    <span class="text-muted-foreground">API key not set — click ⚙ to configure</span>
  {/if}
</div>
