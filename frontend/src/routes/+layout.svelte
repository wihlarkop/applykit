<script lang="ts">
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { logoutOwner } from '$lib/auth-api';
  import { authState } from '$lib/auth-state.svelte';
  import ProfileSwitcher from '$lib/components/ProfileSwitcher.svelte';
  import SessionExpiryBanner from '$lib/components/SessionExpiryBanner.svelte';
  import SettingsButton from '$lib/components/SettingsButton.svelte';
  import SettingsNav from '$lib/components/SettingsNav.svelte';
  import ThemeToggle from '$lib/components/ThemeToggle.svelte';
  import Toaster from '$lib/components/Toaster.svelte';
  import {
    NAVIGATION_ITEMS,
    isNavigationItemActive,
    type NavigationItem,
  } from '$lib/navigation';
  import { themeState } from '$lib/theme.svelte';
  import { toastState } from '$lib/toast.svelte';
  import { LogOut, Menu, X, Zap } from '@lucide/svelte';
  import '../app.css';

  const WIDE_WORKSPACE_PATHS = new Set([
    '/cover-letter',
    '/resume',
    '/generate',
    '/applications',
    '/tracker',
  ]);

  let { data, children } = $props();
  const isAuthRoute = $derived(data.isAuthRoute);
  const onSettings = $derived(page.url.pathname.startsWith('/settings'));
  const shellWidth = $derived(
    WIDE_WORKSPACE_PATHS.has(page.url.pathname) ? 'max-w-[80rem]' : 'max-w-5xl',
  );
  let mobileMenuOpen = $state(false);
  let signingOut = $state(false);

  function navClass(item: NavigationItem) {
    return `px-3 py-1.5 rounded-md text-sm transition-colors ${
      isNavigationItemActive(page.url.pathname, item)
        ? 'bg-accent text-accent-foreground font-medium'
        : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
    }`;
  }

  function mobileNavClass(item: NavigationItem) {
    return `flex items-center gap-2 px-4 py-3 text-sm transition-colors border-b border-border/50 last:border-0 ${
      isNavigationItemActive(page.url.pathname, item)
        ? 'bg-accent text-accent-foreground font-medium'
        : 'text-foreground hover:bg-accent/50'
    }`;
  }

  async function signOut() {
    if (signingOut) return;
    signingOut = true;
    try {
      await logoutOwner();
      authState.clearSession('manual');
      await goto('/login');
    } catch (error) {
      toastState.error(error instanceof Error ? error.message : 'Could not sign out.');
    } finally {
      signingOut = false;
    }
  }

  $effect(() => {
    page.url.pathname;
    mobileMenuOpen = false;
  });

  $effect(() => {
    const isDark = themeState.current === 'dark';
    document.documentElement.classList.toggle('dark', isDark);
    localStorage.setItem('theme', themeState.current);
  });

  $effect(() => {
    if (
      !isAuthRoute
      && authState.authMode === 'password'
      && !authState.authenticated
      && !authState.checking
    ) {
      const returnTo = encodeURIComponent(`${page.url.pathname}${page.url.search}`);
      void goto(`/login?returnTo=${returnTo}`);
    }
  });
</script>

{#if isAuthRoute}
  {@render children()}
  <Toaster />
{:else}
  <div class="min-h-screen flex flex-col bg-muted/40">
    <header class="sticky top-0 z-60 border-b bg-card">
      <div class="mx-auto {shellWidth} px-4 py-3 flex items-center justify-between gap-3">
        <div class="flex items-center gap-4 min-w-0">
          <a
            href="/"
            class="font-bold text-lg tracking-tight hover:text-primary transition-colors shrink-0"
          >ApplyKit</a>

          <nav class="hidden lg:flex items-center gap-1 animate-in fade-in slide-in-from-left-2 duration-500">
            {#each NAVIGATION_ITEMS as item, index}
              {#if index > 0 && NAVIGATION_ITEMS[index - 1].group !== item.group}
                <span class="w-px h-4 bg-border mx-2 shrink-0"></span>
              {/if}
              <a href={item.href} class="{navClass(item)} {item.id === 'prepare' ? 'flex items-center gap-1.5' : ''}">
                {#if item.id === 'prepare'}
                  <Zap class="w-3.5 h-3.5" />
                {/if}
                {item.label}
              </a>
            {/each}
          </nav>
        </div>

        <div class="flex items-center gap-2 shrink-0">
          <ProfileSwitcher />
          <ThemeToggle />
          <SettingsButton />
          {#if authState.authMode === 'password'}
            <button
              type="button"
              onclick={signOut}
              disabled={signingOut}
              class="hidden lg:inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-50"
            >
              <LogOut class="h-4 w-4" />Sign out
            </button>
          {/if}
          <button
            onclick={() => mobileMenuOpen = !mobileMenuOpen}
            class="lg:hidden flex items-center justify-center w-8 h-8 rounded-md hover:bg-accent transition-colors"
            aria-label="Toggle menu"
          >
            {#if mobileMenuOpen}
              <X class="w-4.5 h-4.5" />
            {:else}
              <Menu class="w-4.5 h-4.5" />
            {/if}
          </button>
        </div>
      </div>

      {#if mobileMenuOpen}
        <div class="lg:hidden border-t border-border bg-card animate-in slide-in-from-top-2 duration-200">
          <nav class="mx-auto {shellWidth}">
            {#each NAVIGATION_ITEMS as item}
              <a href={item.href} class="{mobileNavClass(item)} {item.id === 'prepare' ? 'gap-2' : ''}">
                {#if item.id === 'prepare'}
                  <Zap class="w-3.5 h-3.5 text-primary" />
                {/if}
                {item.label}
              </a>
            {/each}
            {#if authState.authMode === 'password'}
              <button
                type="button"
                onclick={signOut}
                disabled={signingOut}
                class="flex w-full items-center gap-2 px-4 py-3 text-left text-sm text-foreground transition-colors hover:bg-accent/50 disabled:opacity-50"
              >
                <LogOut class="h-4 w-4" />Sign out
              </button>
            {/if}
          </nav>
        </div>
      {/if}
    </header>

    {#if authState.authMode === 'password' && authState.authenticated}
      <SessionExpiryBanner />
    {/if}

    <main class="flex-1 mx-auto w-full {shellWidth} px-4 py-8">
      {#if onSettings}
        <div class="mb-6"><SettingsNav /></div>
      {/if}
      {@render children()}
    </main>

    <Toaster />
  </div>
{/if}
