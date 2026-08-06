<script lang="ts">
  import type { RoleMatchViewModel } from '$lib/role-match-presenter';
  import { CircleAlert, ListChecks, RefreshCw } from '@lucide/svelte';

  interface Props {
    view: RoleMatchViewModel;
    onReview?: () => void;
    onRetry?: () => void;
    retrying?: boolean;
  }

  let { view, onReview, onRetry, retrying = false }: Props = $props();
</script>

<section class="rounded-2xl border border-amber-500/25 bg-card p-5 shadow-sm sm:p-6" aria-labelledby="analysis-review-title">
  <div class="flex gap-4">
    <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-500/10 text-amber-700 dark:text-amber-300">
      <CircleAlert class="h-5 w-5" aria-hidden="true" />
    </span>
    <div class="min-w-0">
      <h2 id="analysis-review-title" class="text-lg font-semibold text-foreground">Analysis needs review</h2>
      <p class="mt-1.5 text-sm leading-6 text-muted-foreground">{view.reviewReason}</p>
    </div>
  </div>

  {#if view.requirements.length}
    <div class="mt-5 rounded-xl bg-muted/25 p-4">
      <p class="flex items-center gap-2 text-xs font-semibold text-foreground">
        <ListChecks class="h-4 w-4 text-primary" aria-hidden="true" />
        What we could identify
      </p>
      <ul class="mt-3 grid gap-2 sm:grid-cols-2">
        {#each view.requirements.slice(0, 6) as requirement}
          <li class="text-xs leading-5 text-muted-foreground">• {requirement.canonical_text}</li>
        {/each}
      </ul>
    </div>
  {/if}

  <div class="mt-5 flex flex-wrap gap-2">
    {#if onReview}
      <button
        type="button"
        onclick={onReview}
        class="rounded-lg bg-primary px-3.5 py-2 text-xs font-semibold text-primary-foreground transition-opacity hover:opacity-90"
      >
        Review requirements
      </button>
    {/if}
    {#if onRetry}
      <button
        type="button"
        onclick={onRetry}
        disabled={retrying}
        class="inline-flex items-center gap-2 rounded-lg border border-border px-3.5 py-2 text-xs font-semibold text-foreground hover:bg-muted disabled:cursor-not-allowed disabled:opacity-50"
      >
        <RefreshCw class="h-3.5 w-3.5 {retrying ? 'animate-spin' : ''}" aria-hidden="true" />
        {retrying ? 'Trying again…' : 'Try again'}
      </button>
    {/if}
  </div>
</section>
