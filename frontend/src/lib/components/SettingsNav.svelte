<script lang="ts">
  import { page } from '$app/state';
  import { authState } from '$lib/auth-state.svelte';
  import { settingsTabs } from '$lib/settings-nav';

  const tabs = $derived(settingsTabs(authState.authMode));

  function isActive(href: string): boolean {
    return href === '/settings'
      ? page.url.pathname === '/settings'
      : page.url.pathname.startsWith(href);
  }
</script>

<nav class="inline-flex rounded-lg border border-border bg-muted/40 p-1" aria-label="Settings sections">
  {#each tabs as tab}
    <a
      href={tab.href}
      class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors {isActive(tab.href) ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground hover:text-foreground'}"
      aria-current={isActive(tab.href) ? 'page' : undefined}
    >
      {tab.label}
    </a>
  {/each}
</nav>
