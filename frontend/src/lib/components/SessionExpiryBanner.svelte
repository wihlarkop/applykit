<script lang="ts">
  import { authState } from '$lib/auth-state.svelte';
  import { nextExpiryState } from '$lib/session-expiry';
  import { Clock3, ExternalLink } from '@lucide/svelte';

  let now = $state(Date.now());
  const expiryState = $derived(nextExpiryState(authState.sessionExpiresAt, now));

  $effect(() => {
    const timer = window.setInterval(() => {
      now = Date.now();
    }, 1000);
    return () => window.clearInterval(timer);
  });

  $effect(() => {
    if (expiryState === 'expired') authState.markExpired();
  });

  $effect(() => {
    async function refreshSession() {
      if (document.visibilityState !== 'visible') return;
      try {
        await authState.refresh();
        now = Date.now();
      } catch {
        // The existing state remains authoritative until the next request or refresh.
      }
    }

    window.addEventListener('focus', refreshSession);
    document.addEventListener('visibilitychange', refreshSession);
    return () => {
      window.removeEventListener('focus', refreshSession);
      document.removeEventListener('visibilitychange', refreshSession);
    };
  });

  function openReauthentication() {
    window.open('/login?reauth=1', '_blank', 'noopener');
  }
</script>

{#if expiryState === 'active'}
  <div class="border-b border-amber-300 bg-amber-50 text-amber-950 dark:border-amber-800 dark:bg-amber-950/70 dark:text-amber-100" role="status">
    <div class="mx-auto flex max-w-5xl flex-col gap-2 px-4 py-2.5 sm:flex-row sm:items-center sm:justify-between">
      <p class="flex items-center gap-2 text-sm font-medium">
        <Clock3 class="h-4 w-4 shrink-0" />
        Your session expires in 5 minutes.
      </p>
      <button
        type="button"
        onclick={openReauthentication}
        class="inline-flex w-fit items-center gap-1.5 rounded-md bg-amber-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-800 dark:bg-amber-200 dark:text-amber-950 dark:hover:bg-amber-100"
      >
        Sign in again <ExternalLink class="h-3.5 w-3.5" />
      </button>
    </div>
  </div>
{/if}
