<script lang="ts">
  import { page } from '$app/state';

  const readiness = $derived(page.data.readiness);
</script>

<div class="flex items-center gap-2 text-sm">
  {#if readiness === null || readiness === undefined}
    <span class="size-2 rounded-full bg-muted animate-pulse"></span>
    <span class="text-muted-foreground">Checking readiness…</span>
  {:else if readiness.ai.ready}
    <span class="size-2 rounded-full bg-green-500"></span>
    <span class="text-muted-foreground">{readiness.ai.provider ?? 'AI'} verified</span>
  {:else if readiness.ai.status === 'not_configured'}
    <span class="size-2 rounded-full bg-yellow-500"></span>
    <span class="text-muted-foreground">AI not configured — open Settings</span>
  {:else}
    <span class="size-2 rounded-full bg-yellow-500"></span>
    <span class="text-muted-foreground">AI connection needs attention</span>
  {/if}
</div>
