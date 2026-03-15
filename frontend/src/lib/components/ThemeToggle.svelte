<script lang="ts">
  import { themeState } from '$lib/theme.svelte';
  import { Moon, Sun } from '@lucide/svelte';
  import { fade, scale } from 'svelte/transition';

  let currentTheme = $derived(themeState.current);
</script>

<button
  onclick={() => themeState.toggle()}
  class="relative inline-flex h-9 w-9 items-center justify-center rounded-md border bg-background text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 shadow-sm"
  title="Toggle Theme"
>
  <div class="relative flex items-center justify-center w-full h-full">
    {#if currentTheme === 'light'}
      <div in:scale={{ duration: 200, start: 0.8 }} out:fade={{ duration: 100 }}>
        <Sun class="h-4 w-4" />
      </div>
    {:else}
      <div in:scale={{ duration: 200, start: 0.8 }} out:fade={{ duration: 100 }}>
        <Moon class="h-4 w-4" />
      </div>
    {/if}
  </div>
</button>
