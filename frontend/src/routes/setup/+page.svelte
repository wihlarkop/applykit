<script lang="ts">
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { setupOwner } from '$lib/auth-api';
  import { authState } from '$lib/auth-state.svelte';
  import { sanitizeReturnTo } from '$lib/auth-utils';
  import AuthShell from '$lib/components/AuthShell.svelte';
  import PasswordStrength from '$lib/components/PasswordStrength.svelte';
  import { setupFormEligible } from '$lib/setup-form';
  import { Eye, EyeOff, Loader2 } from '@lucide/svelte';

  let setupToken = $state('');
  let password = $state('');
  let confirmation = $state('');
  let showPassword = $state(false);
  let submitting = $state(false);
  let errorMessage = $state('');

  const eligible = $derived(setupFormEligible(setupToken, password, confirmation));
  const confirmationError = $derived(
    confirmation.length > 0 && password !== confirmation
      ? 'Passwords do not match.'
      : '',
  );

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    if (!eligible || submitting) return;

    submitting = true;
    errorMessage = '';
    try {
      const session = await setupOwner({
        setup_token: setupToken,
        password,
      });
      authState.applySession(session);
      setupToken = '';
      password = '';
      confirmation = '';
      await goto(sanitizeReturnTo(page.url.searchParams.get('returnTo')));
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Owner setup could not be completed.';
    } finally {
      submitting = false;
    }
  }
</script>

<AuthShell
  title="Protect your ApplyKit installation"
  description="Create one owner password for this installation. Every career profile will use the same sign-in."
>
  <form class="space-y-5" onsubmit={submit}>
    {#if errorMessage}
      <div class="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-sm text-destructive" role="alert">
        {errorMessage}
      </div>
    {/if}

    <div class="space-y-2">
      <label for="setup-token" class="text-sm font-medium">One-time setup token</label>
      <input
        id="setup-token"
        name="setup-token"
        type="text"
        autocomplete="off"
        bind:value={setupToken}
        class="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
        placeholder="Paste the token from backend logs"
        required
      />
      <p class="text-xs leading-5 text-muted-foreground">
        The token appears in the latest backend or container logs and expires after 30 minutes.
      </p>
    </div>

    <div class="space-y-2">
      <label for="password" class="text-sm font-medium">Password</label>
      <div class="relative">
        <input
          id="password"
          name="password"
          type={showPassword ? 'text' : 'password'}
          autocomplete="new-password"
          bind:value={password}
          minlength="12"
          maxlength="128"
          class="w-full rounded-lg border border-input bg-background px-3 py-2.5 pr-10 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
          required
        />
        <button
          type="button"
          onclick={() => showPassword = !showPassword}
          class="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-muted-foreground hover:text-foreground"
          aria-label={showPassword ? 'Hide password' : 'Show password'}
        >
          {#if showPassword}<EyeOff class="h-4 w-4" />{:else}<Eye class="h-4 w-4" />{/if}
        </button>
      </div>
      <PasswordStrength {password} />
      <p class="text-xs text-muted-foreground">Use 12–128 characters. Long passphrases are welcome.</p>
    </div>

    <div class="space-y-2">
      <label for="confirm-password" class="text-sm font-medium">Confirm password</label>
      <input
        id="confirm-password"
        name="confirm-password"
        type="password"
        autocomplete="new-password"
        bind:value={confirmation}
        maxlength="128"
        class="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
        aria-invalid={confirmationError ? 'true' : 'false'}
        required
      />
      {#if confirmationError}
        <p class="text-xs text-destructive">{confirmationError}</p>
      {/if}
    </div>

    <button
      type="submit"
      disabled={!eligible || submitting}
      class="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
    >
      {#if submitting}<Loader2 class="h-4 w-4 animate-spin" />Creating owner password…{:else}Create owner password{/if}
    </button>
  </form>
</AuthShell>
