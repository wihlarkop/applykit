<script lang="ts">
  import { onMount } from 'svelte';
  import { getStatus } from '$lib/api';
  import type { StatusResponse } from '$lib/types';
  import { Settings, Cpu, Info } from '@lucide/svelte';

  let status: StatusResponse | null = $state(null);
  let error = $state(false);

  onMount(async () => {
    try {
      status = await getStatus();
    } catch {
      error = true;
    }
  });
</script>

<div class="max-w-2xl space-y-8">
  <div>
    <h1 class="text-2xl font-bold flex items-center gap-2">
      <Settings class="w-6 h-6 text-primary" />
      Settings
    </h1>
    <p class="text-sm text-muted-foreground mt-1">View your current configuration. To make changes, edit your <code class="px-1 py-0.5 rounded bg-muted text-xs font-mono">.env</code> file.</p>
  </div>

  <!-- AI Model -->
  <div class="border rounded-xl p-6 bg-card space-y-4">
    <h2 class="font-semibold flex items-center gap-2 text-base">
      <Cpu class="w-4 h-4 text-primary" />
      AI Model
    </h2>

    {#if error}
      <div class="flex items-center gap-2 text-sm text-destructive">
        <span class="w-2 h-2 rounded-full bg-red-500 shrink-0"></span>
        Backend unreachable — make sure the server is running.
      </div>
    {:else if status === null}
      <div class="flex items-center gap-2 text-sm text-muted-foreground">
        <span class="w-2 h-2 rounded-full bg-muted animate-pulse shrink-0"></span>
        Checking connection…
      </div>
    {:else if status.api_key_configured}
      <div class="space-y-3">
        <div class="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
          <span class="w-2 h-2 rounded-full bg-green-500 shrink-0"></span>
          Connected
        </div>
        <div class="text-sm">
          <span class="text-muted-foreground">Provider / Model:</span>
          <code class="ml-2 px-2 py-0.5 rounded bg-muted text-foreground text-xs font-mono">{status.provider}</code>
        </div>
      </div>
    {:else}
      <div class="flex items-center gap-2 text-sm text-yellow-600 dark:text-yellow-400">
        <span class="w-2 h-2 rounded-full bg-yellow-500 shrink-0"></span>
        API key not configured
      </div>
    {/if}

    <div class="pt-3 border-t space-y-2">
      <p class="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Info class="w-3.5 h-3.5 shrink-0" />
        To change the model or API key, update your <code class="px-1 py-0.5 rounded bg-muted font-mono">.env</code> file and restart the backend.
      </p>
      <div class="rounded-lg bg-muted/60 px-3 py-2 font-mono text-xs space-y-1 text-foreground/80">
        <div>LLM_PROVIDER=<span class="text-primary">gemini/gemini-2.5-flash-lite</span></div>
        <div>LLM_API_KEY=<span class="text-primary">your-api-key</span></div>
      </div>
    </div>
  </div>
</div>
