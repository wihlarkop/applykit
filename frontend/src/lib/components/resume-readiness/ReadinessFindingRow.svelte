<script lang="ts">
  import type { ResumeReadinessFinding } from '$lib/resume-readiness-types';
  import { ChevronDown } from '@lucide/svelte';

  interface Props {
    finding: ResumeReadinessFinding;
  }

  let { finding }: Props = $props();
  let expanded = $state(false);

  const locationLabel = $derived(
    finding.locations.length > 0 ? finding.locations.join(', ') : null,
  );
</script>

<div class="rounded-lg border bg-card/60 p-3">
  <button
    type="button"
    class="flex w-full items-start justify-between gap-3 text-left"
    aria-expanded={expanded}
    onclick={() => (expanded = !expanded)}
  >
    <div class="min-w-0">
      <div class="flex flex-wrap items-center gap-2">
        <span class="font-semibold">{finding.title}</span>
        <span class="rounded border px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
          {finding.category}
        </span>
      </div>
      <p class="mt-1 text-sm leading-relaxed text-muted-foreground">{finding.explanation}</p>
      {#if locationLabel}
        <p class="mt-1 text-xs text-muted-foreground">Affected: {locationLabel}</p>
      {/if}
    </div>
    <ChevronDown class="mt-1 h-4 w-4 shrink-0 transition-transform {expanded ? 'rotate-180' : ''}" />
  </button>

  {#if expanded}
    <div class="mt-3 border-t pt-3 text-xs text-muted-foreground">
      <div class="grid gap-1 sm:grid-cols-2">
        <span>Rule: <code>{finding.rule_id}</code></span>
        <span>Outcome: {finding.outcome}</span>
        <span>Score impact: {finding.score_delta}</span>
        {#if finding.score_cap != null}
          <span>Score cap: {finding.score_cap}</span>
        {/if}
      </div>
      {#if Object.keys(finding.evidence).length > 0}
        <pre class="mt-3 max-h-48 overflow-auto whitespace-pre-wrap rounded bg-muted p-2 text-[11px]">{JSON.stringify(finding.evidence, null, 2)}</pre>
      {/if}
    </div>
  {/if}
</div>
