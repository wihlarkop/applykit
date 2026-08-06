<script lang="ts">
  import type { RoleMatchViewModel } from '$lib/role-match-presenter';
  import { CircleCheck, RefreshCw, ShieldCheck } from '@lucide/svelte';

  interface Props {
    view: RoleMatchViewModel;
    companyName?: string | null;
    onReanalyze?: () => void;
    analyzing?: boolean;
  }

  let {
    view,
    companyName = null,
    onReanalyze,
    analyzing = false,
  }: Props = $props();
</script>

<section class="rounded-2xl border border-border bg-card p-5 shadow-sm sm:p-6" aria-labelledby="role-match-title">
  <div class="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
    <div class="min-w-0 space-y-2">
      <div class="flex items-center gap-2 text-xs font-semibold text-muted-foreground">
        <ShieldCheck class="h-4 w-4 text-primary" aria-hidden="true" />
        <span>Role Evidence Match{companyName ? ` · ${companyName}` : ''}</span>
      </div>
      <h2 id="role-match-title" class="text-xl font-semibold tracking-tight text-foreground">
        {view.headline}
      </h2>
      <p class="max-w-2xl text-sm leading-6 text-muted-foreground">{view.description}</p>
    </div>

    {#if onReanalyze}
      <button
        type="button"
        onclick={onReanalyze}
        disabled={analyzing}
        class="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg border border-border px-3 py-2 text-xs font-semibold text-foreground transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
      >
        <RefreshCw class="h-3.5 w-3.5 {analyzing ? 'animate-spin' : ''}" aria-hidden="true" />
        {analyzing ? 'Analyzing…' : 'Re-analyze'}
      </button>
    {/if}
  </div>

  <div class="mt-5 grid gap-3 sm:grid-cols-[auto_1fr]">
    <div class="flex min-h-28 min-w-32 flex-col items-center justify-center rounded-xl border border-primary/20 bg-primary/5 px-5 py-4 text-center">
      <span class="text-3xl font-semibold tracking-tight text-foreground">{view.score}</span>
      <span class="mt-1 text-xs font-medium text-muted-foreground">out of 100</span>
      {#if view.scoreBandLabel}
        <span class="mt-2 rounded-full bg-background px-2.5 py-1 text-[11px] font-semibold text-primary ring-1 ring-primary/20">
          {view.scoreBandLabel}
        </span>
      {/if}
    </div>

    <div class="grid gap-3 sm:grid-cols-2">
      <div class="rounded-xl border border-border bg-muted/25 p-4">
        <p class="text-xs font-semibold text-muted-foreground">Confidence</p>
        <p class="mt-1 flex items-center gap-2 text-sm font-semibold text-foreground">
          <CircleCheck class="h-4 w-4 text-emerald-600 dark:text-emerald-400" aria-hidden="true" />
          {view.confidenceLabel ?? 'Not available'}
        </p>
        <p class="mt-1.5 text-xs leading-5 text-muted-foreground">
          Based on the coverage and reliability of the evidence in your profile.
        </p>
      </div>

      <div class="rounded-xl border border-border bg-muted/25 p-4">
        <p class="text-xs font-semibold text-muted-foreground">Eligibility</p>
        <p class="mt-1 text-sm font-semibold text-foreground">{view.eligibilityLabel}</p>
        <p class="mt-1.5 text-xs leading-5 text-muted-foreground">
          Checked separately from your evidence match so missing information is not treated as failure.
        </p>
      </div>
    </div>
  </div>
</section>
