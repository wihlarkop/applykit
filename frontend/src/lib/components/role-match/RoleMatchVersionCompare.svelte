<script lang="ts">
  import type {
    RoleMatchAnalysisResponse,
    RoleMatchComparisonResponse,
    RoleMatchOverrideResponse,
    RoleMatchVersionsResponse,
  } from '$lib/role-match-types';
  import { History, RotateCcw } from '@lucide/svelte';

  interface Props {
    analysis: RoleMatchAnalysisResponse;
    versions?: RoleMatchVersionsResponse | null;
    comparison?: RoleMatchComparisonResponse | null;
    onRestore?: (override: RoleMatchOverrideResponse) => Promise<void> | void;
  }

  let { analysis, versions = null, comparison = null, onRestore }: Props = $props();
  let restoringId = $state<number | null>(null);

  const statusLabels = {
    carried_forward: 'Carried forward',
    needs_review: 'Needs review',
    not_applicable: 'Not applicable',
  } as const;

  async function restore(override: RoleMatchOverrideResponse) {
    if (!onRestore) return;
    restoringId = override.id;
    try {
      await onRestore(override);
    } finally {
      restoringId = null;
    }
  }
</script>

<section class="rounded-2xl border border-border bg-card p-5 shadow-sm" aria-labelledby="analysis-history-title">
  <h3 id="analysis-history-title" class="flex items-center gap-2 text-sm font-semibold text-foreground">
    <History class="h-4 w-4 text-primary" aria-hidden="true" />
    Analysis history
  </h3>

  {#if comparison?.score_change !== null && comparison?.score_change !== undefined}
    <p class="mt-3 rounded-xl bg-primary/5 px-4 py-3 text-sm text-foreground">
      {#if comparison.score_change > 0}
        Your match increased from the previous version by {comparison.score_change} points.
      {:else if comparison.score_change < 0}
        Your match decreased from the previous version by {Math.abs(comparison.score_change)} points.
      {:else}
        Your match score did not change in this version.
      {/if}
    </p>
  {:else}
    <p class="mt-3 text-xs leading-5 text-muted-foreground">
      Your match increased from a previous version when new evidence raises the deterministic score.
    </p>
  {/if}

  {#if versions?.items.length}
    <ol class="mt-4 space-y-2">
      {#each versions.items as version, index}
        <li class="flex items-center justify-between gap-3 rounded-xl border border-border px-3.5 py-3">
          <div>
            <p class="text-xs font-semibold text-foreground">Version {index + 1}</p>
            <p class="mt-0.5 text-[11px] text-muted-foreground">
              {new Date(version.created_at).toLocaleString()} · {version.state.replaceAll('_', ' ')}
            </p>
          </div>
          <span class="text-sm font-semibold text-foreground">{version.score ?? '—'}</span>
        </li>
      {/each}
    </ol>
  {/if}

  {#if analysis.overrides.length}
    <div class="mt-5 space-y-2">
      <p class="text-xs font-semibold text-muted-foreground">Corrections in this version</p>
      {#each analysis.overrides as override}
        <div class="rounded-xl border border-border p-3.5">
          <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p class="text-sm font-medium text-foreground">{override.requirement_key.replaceAll('_', ' ')}</p>
              <p class="mt-1 text-xs leading-5 text-muted-foreground">{override.reason}</p>
              <span class="mt-2 inline-block rounded-full bg-muted px-2 py-1 text-[11px] font-semibold text-foreground">
                {statusLabels[override.carry_status]}
              </span>
            </div>
            {#if onRestore && override.source === 'user'}
              <button
                type="button"
                onclick={() => restore(override)}
                disabled={restoringId === override.id}
                class="inline-flex shrink-0 items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs font-semibold text-foreground hover:bg-muted disabled:opacity-50"
              >
                <RotateCcw class="h-3.5 w-3.5" aria-hidden="true" />
                {restoringId === override.id ? 'Restoring…' : 'Restore original analysis'}
              </button>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</section>
