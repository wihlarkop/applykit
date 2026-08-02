<script lang="ts">
  import {
    changeOwnerPassword,
    getSecuritySummary,
    revokeOtherSessions,
  } from '$lib/auth-api';
  import { authState } from '$lib/auth-state.svelte';
  import PasswordStrength from '$lib/components/PasswordStrength.svelte';
  import { changePasswordEligible, otherSessionsLabel } from '$lib/security-form';
  import { toastState } from '$lib/toast.svelte';
  import { KeyRound, Loader2, LogOut, ShieldCheck } from '@lucide/svelte';

  let currentPassword = $state('');
  let newPassword = $state('');
  let confirmation = $state('');
  let changing = $state(false);
  let loadingSessions = $state(true);
  let otherSessions = $state(0);
  let confirmingRevoke = $state(false);
  let revoking = $state(false);
  let errorMessage = $state('');

  const eligible = $derived(
    changePasswordEligible(currentPassword, newPassword, confirmation),
  );
  const confirmationError = $derived(
    confirmation.length > 0 && confirmation !== newPassword
      ? 'Passwords do not match.'
      : '',
  );

  $effect(() => {
    loadSessions();
  });

  async function loadSessions() {
    loadingSessions = true;
    try {
      const summary = await getSecuritySummary();
      otherSessions = summary.other_sessions;
    } catch (error) {
      toastState.error(error instanceof Error ? error.message : 'Failed to load active sessions.');
    } finally {
      loadingSessions = false;
    }
  }

  async function submitPassword(event: SubmitEvent) {
    event.preventDefault();
    if (!eligible || changing) return;

    changing = true;
    errorMessage = '';
    try {
      const session = await changeOwnerPassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      authState.applySession(session);
      currentPassword = '';
      newPassword = '';
      confirmation = '';
      otherSessions = 0;
      toastState.success('Password changed. Other sessions were signed out.');
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Password could not be changed.';
    } finally {
      changing = false;
    }
  }

  async function signOutOthers() {
    if (revoking) return;
    revoking = true;
    try {
      await revokeOtherSessions();
      otherSessions = 0;
      confirmingRevoke = false;
      toastState.success('Other devices have been signed out.');
    } catch (error) {
      toastState.error(error instanceof Error ? error.message : 'Could not sign out other devices.');
    } finally {
      revoking = false;
    }
  }
</script>

<div class="mx-auto max-w-3xl space-y-6">
  <header>
    <h1 class="flex items-center gap-2 text-2xl font-bold tracking-tight">
      <ShieldCheck class="h-6 w-6 text-primary" />Security
    </h1>
    <p class="mt-1 text-sm text-muted-foreground">
      Change the installation owner password and control other active sessions.
    </p>
  </header>

  <section class="rounded-2xl border border-border bg-card p-5 shadow-sm sm:p-6">
    <div class="mb-5 flex items-start gap-3">
      <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
        <KeyRound class="h-5 w-5" />
      </div>
      <div>
        <h2 class="font-semibold">Change password</h2>
        <p class="mt-1 text-sm text-muted-foreground">
          Changing it keeps this browser signed in and revokes every other session.
        </p>
      </div>
    </div>

    <form class="space-y-4" onsubmit={submitPassword}>
      {#if errorMessage}
        <div class="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-sm text-destructive" role="alert">
          {errorMessage}
        </div>
      {/if}

      <div class="space-y-2">
        <label for="current-password" class="text-sm font-medium">Current password</label>
        <input
          id="current-password"
          type="password"
          autocomplete="current-password"
          bind:value={currentPassword}
          class="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
          required
        />
      </div>

      <div class="space-y-2">
        <label for="new-password" class="text-sm font-medium">New password</label>
        <input
          id="new-password"
          type="password"
          autocomplete="new-password"
          bind:value={newPassword}
          minlength="12"
          maxlength="128"
          class="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
          required
        />
        <PasswordStrength password={newPassword} />
      </div>

      <div class="space-y-2">
        <label for="confirm-new-password" class="text-sm font-medium">Confirm new password</label>
        <input
          id="confirm-new-password"
          type="password"
          autocomplete="new-password"
          bind:value={confirmation}
          maxlength="128"
          class="w-full rounded-lg border border-input bg-background px-3 py-2.5 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
          aria-invalid={confirmationError ? 'true' : 'false'}
          required
        />
        {#if confirmationError}<p class="text-xs text-destructive">{confirmationError}</p>{/if}
      </div>

      <button
        type="submit"
        disabled={!eligible || changing}
        class="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {#if changing}<Loader2 class="h-4 w-4 animate-spin" />Changing password…{:else}Change password{/if}
      </button>
    </form>
  </section>

  <section class="rounded-2xl border border-border bg-card p-5 shadow-sm sm:p-6">
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div class="flex items-start gap-3">
        <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <LogOut class="h-5 w-5" />
        </div>
        <div>
          <h2 class="font-semibold">Active sessions</h2>
          <p class="mt-1 text-sm text-muted-foreground">
            {#if loadingSessions}Checking sessions…{:else}{otherSessionsLabel(otherSessions)}{/if}
          </p>
        </div>
      </div>

      {#if !confirmingRevoke}
        <button
          type="button"
          onclick={() => confirmingRevoke = true}
          disabled={loadingSessions || otherSessions === 0}
          class="rounded-lg border border-border px-3 py-2 text-sm font-medium hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
        >
          Sign out other devices
        </button>
      {/if}
    </div>

    {#if confirmingRevoke}
      <div class="mt-5 rounded-xl border border-border bg-muted/30 p-4">
        <p class="text-sm font-medium">Sign out {otherSessionsLabel(otherSessions).toLowerCase()}?</p>
        <p class="mt-1 text-xs leading-5 text-muted-foreground">This browser will remain signed in.</p>
        <div class="mt-3 flex gap-2">
          <button type="button" onclick={signOutOthers} disabled={revoking} class="inline-flex items-center gap-2 rounded-lg bg-destructive px-3 py-2 text-sm font-semibold text-destructive-foreground disabled:opacity-50">
            {#if revoking}<Loader2 class="h-4 w-4 animate-spin" />Signing out…{:else}Confirm{/if}
          </button>
          <button type="button" onclick={() => confirmingRevoke = false} disabled={revoking} class="rounded-lg border border-border px-3 py-2 text-sm font-medium hover:bg-accent">Cancel</button>
        </div>
      </div>
    {/if}
  </section>
</div>
