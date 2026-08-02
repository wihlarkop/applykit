<script lang="ts">
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { loginOwner } from '$lib/auth-api';
  import { authState } from '$lib/auth-state.svelte';
  import AuthShell from '$lib/components/AuthShell.svelte';
  import { loginSuccessDestination } from '$lib/login-flow';
  import { Check, Clipboard, Eye, EyeOff, Loader2, Terminal } from '@lucide/svelte';

  const dockerCommand = 'docker compose exec backend uv run python -m app.cli auth reset-password';
  const manualCommand = 'cd backend\nuv run python -m app.cli auth reset-password';

  let password = $state('');
  let rememberDevice = $state(false);
  let showPassword = $state(false);
  let showRecovery = $state(false);
  let submitting = $state(false);
  let errorMessage = $state('');
  let copied = $state<'docker' | 'manual' | null>(null);
  let reauthComplete = $state(false);

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    if (!password || submitting) return;

    submitting = true;
    errorMessage = '';
    try {
      const session = await loginOwner({
        password,
        remember_device: rememberDevice,
      });
      authState.applySession(session);
      password = '';

      const destination = loginSuccessDestination(page.url);
      if (destination.kind === 'reauth-complete') {
        reauthComplete = true;
        setTimeout(() => window.close(), 250);
      } else {
        await goto(destination.path);
      }
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Sign in failed. Please try again.';
    } finally {
      submitting = false;
    }
  }

  async function copyCommand(kind: 'docker' | 'manual', command: string) {
    try {
      await navigator.clipboard.writeText(command);
      copied = kind;
      setTimeout(() => {
        if (copied === kind) copied = null;
      }, 1800);
    } catch {
      copied = null;
    }
  }
</script>

{#if reauthComplete}
  <AuthShell
    title="You're signed in"
    description="Your ApplyKit session has been renewed. You can return to the original tab."
  >
    <div class="space-y-5 text-center">
      <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-green-100 text-green-700 dark:bg-green-950/60 dark:text-green-300">
        <Check class="h-6 w-6" />
      </div>
      <p class="text-sm text-muted-foreground">This tab may close automatically when your browser allows it.</p>
      <button
        type="button"
        onclick={() => window.close()}
        class="inline-flex w-full items-center justify-center rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
      >
        Close this tab
      </button>
    </div>
  </AuthShell>
{:else}
  <AuthShell title="Sign in to ApplyKit" description="Enter the owner password for this installation.">
    <form class="space-y-5" onsubmit={submit}>
      {#if errorMessage}
        <div class="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-sm text-destructive" role="alert">
          {errorMessage}
        </div>
      {/if}

      <div class="space-y-2">
        <label for="password" class="text-sm font-medium">Password</label>
        <div class="relative">
          <input
            id="password"
            name="password"
            type={showPassword ? 'text' : 'password'}
            autocomplete="current-password"
            bind:value={password}
            maxlength="128"
            class="w-full rounded-lg border border-input bg-background px-3 py-2.5 pr-10 text-sm outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/20"
            required
            autofocus
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
      </div>

      <label class="flex cursor-pointer items-start gap-3 rounded-lg border border-border bg-muted/30 px-3 py-3">
        <input type="checkbox" bind:checked={rememberDevice} class="mt-0.5 h-4 w-4 rounded border-input" />
        <span>
          <span class="block text-sm font-medium">Remember this device</span>
          <span class="mt-0.5 block text-xs leading-5 text-muted-foreground">
            Keep this browser signed in for 30 days instead of 7 days.
          </span>
        </span>
      </label>

      <button
        type="submit"
        disabled={!password || submitting}
        class="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {#if submitting}<Loader2 class="h-4 w-4 animate-spin" />Signing in…{:else}Sign in{/if}
      </button>

      <div class="border-t border-border pt-4">
        <button
          type="button"
          onclick={() => showRecovery = !showRecovery}
          class="text-sm font-medium text-primary hover:underline"
          aria-expanded={showRecovery}
        >
          Forgot password?
        </button>

        {#if showRecovery}
          <div class="mt-4 space-y-4 rounded-xl border border-border bg-muted/30 p-4">
            <div class="flex items-start gap-2">
              <Terminal class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
              <p class="text-xs leading-5 text-muted-foreground">
                ApplyKit has no email recovery. Run one of these commands on the machine hosting ApplyKit.
              </p>
            </div>

            <div class="space-y-2">
              <p class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Docker</p>
              <div class="flex items-start gap-2 rounded-lg border border-border bg-background p-3">
                <code class="min-w-0 flex-1 break-all text-xs">{dockerCommand}</code>
                <button type="button" onclick={() => copyCommand('docker', dockerCommand)} class="shrink-0 text-muted-foreground hover:text-foreground" aria-label="Copy Docker reset command">
                  {#if copied === 'docker'}<Check class="h-4 w-4" />{:else}<Clipboard class="h-4 w-4" />{/if}
                </button>
              </div>
            </div>

            <div class="space-y-2">
              <p class="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Manual setup</p>
              <div class="flex items-start gap-2 rounded-lg border border-border bg-background p-3">
                <code class="min-w-0 flex-1 whitespace-pre-wrap text-xs">{manualCommand}</code>
                <button type="button" onclick={() => copyCommand('manual', manualCommand)} class="shrink-0 text-muted-foreground hover:text-foreground" aria-label="Copy manual reset command">
                  {#if copied === 'manual'}<Check class="h-4 w-4" />{:else}<Clipboard class="h-4 w-4" />{/if}
                </button>
              </div>
            </div>
          </div>
        {/if}
      </div>
    </form>
  </AuthShell>
{/if}
