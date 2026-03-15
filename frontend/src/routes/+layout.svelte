<script lang="ts">
  import { page } from '$app/stores';
  import StatusIndicator from '$lib/components/StatusIndicator.svelte';
  import Toaster from '$lib/components/Toaster.svelte';
  import ThemeToggle from '$lib/components/ThemeToggle.svelte';
  import { themeState } from '$lib/theme.svelte';
  import '../app.css';

  let { data, children } = $props();
  const isOnboarded = $derived(data.isOnboarded);

  const navLinks = [
    { href: '/', label: 'Dashboard' },
    { href: '/profile', label: 'Profile' },
    { href: '/generate', label: 'Generate CV' },
    { href: '/cover-letter', label: 'Cover Letter' },
    { href: '/history', label: 'History' },
  ];

  // Dark mode effect
  $effect(() => {
    if (typeof document !== 'undefined') {
      const isDark = themeState.current === 'dark';
      document.documentElement.classList.toggle('dark', isDark);
      localStorage.setItem('theme', themeState.current);
    }
  });
</script>

<div class="min-h-screen flex flex-col bg-muted/40">
  <header class="border-b bg-card">
    <div class="mx-auto max-w-5xl px-4 py-3 flex items-center justify-between">
      <div class="flex items-center gap-8">
        <a href={isOnboarded ? "/" : "/onboarding"} class="font-bold text-lg tracking-tight hover:text-primary transition-colors">ApplyKit</a>
        
        {#if isOnboarded}
          <nav class="flex items-center gap-1 animate-in fade-in slide-in-from-left-2 duration-500">
            {#each navLinks as link}
              <a
                href={link.href}
                class="px-3 py-1.5 rounded-md text-sm transition-colors
                  {$page.url.pathname === link.href
                    ? 'bg-accent text-accent-foreground font-medium'
                    : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'}"
              >
                {link.label}
              </a>
            {/each}
          </nav>
        {/if}
      </div>

      {#if isOnboarded}
        <div class="flex items-center gap-3 animate-in fade-in duration-500">
          <ThemeToggle />
          <StatusIndicator />
        </div>
      {/if}
    </div>
  </header>

  <main class="flex-1 mx-auto w-full max-w-5xl px-4 py-8">
    {@render children()}
  </main>

  <Toaster />
</div>
