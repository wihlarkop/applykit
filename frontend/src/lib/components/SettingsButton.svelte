<script lang="ts">
  import { page } from '$app/state';
  import { Settings } from '@lucide/svelte';

  const dotColor = $derived(page.data.isApiKeyConfigured ? null : 'bg-yellow-500');
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
