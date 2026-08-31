<script lang="ts">
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { logoutOwner } from '$lib/auth-api';
  import { authState } from '$lib/auth-state.svelte';
  import ProfileSwitcher from '$lib/components/ProfileSwitcher.svelte';
  import SessionExpiryBanner from '$lib/components/SessionExpiryBanner.svelte';
  import Sidebar from '$lib/components/Sidebar.svelte';
  import SettingsButton from '$lib/components/SettingsButton.svelte';
  import SettingsNav from '$lib/components/SettingsNav.svelte';
  import ThemeToggle from '$lib/components/ThemeToggle.svelte';
  import Toaster from '$lib/components/Toaster.svelte';
  import { themeState } from '$lib/theme.svelte';
  import { toastState } from '$lib/toast.svelte';
  import { LogOut } from '@lucide/svelte';
  import '../app.css';

  let { data, children } = $props();
  const isAuthRoute = $derived(data.isAuthRoute);
  const onSettings = $derived(page.url.pathname.startsWith('/settings'));
  const shellWidth = $derived(
    page.url.pathname === '/cover-letter' ? 'max-w-[80rem]' : 'max-w-5xl',
  );
  let signingOut = $state(false);

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
  <div class="min-h-screen flex bg-muted/40">
    <Sidebar />

    <div class="flex-1 flex flex-col min-w-0">
      <header class="sticky top-0 z-60 border-b bg-card">
        <div class="px-4 py-3 flex items-center justify-between gap-3">
          <a
            href="/"
            class="font-bold text-lg tracking-tight hover:text-primary transition-colors shrink-0"
          >ApplyKit</a>

          <div class="flex items-center gap-2 shrink-0">
            <ProfileSwitcher />
            <ThemeToggle />
            <div class="md:hidden"><SettingsButton /></div>
            {#if authState.authMode === 'password'}
              <button
                type="button"
                onclick={signOut}
                disabled={signingOut}
                class="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-50"
              >
                <LogOut class="h-4 w-4" />
                <span class="hidden sm:inline">Sign out</span>
              </button>
            {/if}
          </div>
        </div>
      </header>

      {#if authState.authMode === 'password' && authState.authenticated}
        <SessionExpiryBanner />
      {/if}

      <main class="flex-1 w-full mx-auto {shellWidth} px-4 py-8 pb-24 md:pb-8">
        {#if onSettings}
          <div class="mb-6"><SettingsNav /></div>
        {/if}
        {@render children()}
      </main>
    </div>

    <Toaster />
  </div>
{/if}
