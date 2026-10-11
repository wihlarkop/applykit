<script lang="ts">
  import { Badge } from '$lib/components/ui/badge';
  import { getLatestResumeReadiness } from '$lib/resume-readiness-api';
  import { formatReadinessBand } from '$lib/resume-readiness-policy';
  import type { ResumeReadinessResponse } from '$lib/resume-readiness-types';
  import type { GeneratedCVEntry } from '$lib/types';
  import { formatDate } from '$lib/utils';
  import { ArrowRight } from '@lucide/svelte';

  interface Props {
    entry: GeneratedCVEntry;
    selected: boolean;
    onSelect: () => void;
  }

  let { entry, selected, onSelect }: Props = $props();
  let analysis = $state<ResumeReadinessResponse | null>(null);
  let loadingAnalysis = $state(true);
  let loadSequence = 0;

  $effect(() => {
    const generatedCvId = entry.id;
    const sequence = ++loadSequence;
    analysis = null;
    loadingAnalysis = true;
    getLatestResumeReadiness(generatedCvId)
      .then((result) => {
        if (sequence === loadSequence) analysis = result;
      })
      .catch(() => {
        if (sequence === loadSequence) analysis = null;
      })
      .finally(() => {
        if (sequence === loadSequence) loadingAnalysis = false;
      });
  });
</script>

<div
  class="w-full overflow-hidden rounded-xl border text-left outline-none transition-all
    {selected ? 'scale-[1.01] border-primary/50 bg-primary/5 shadow-md ring-1 ring-primary/20' : 'border-border/60 bg-card hover:border-border hover:shadow-sm'}
  "
>
  <button
    type="button"
    onclick={onSelect}
    class="w-full p-3.5 text-left transition-colors hover:bg-accent/40"
  >
    <div class="flex items-center justify-between gap-2">
      <span class="text-[13px] font-semibold text-foreground/90">{formatDate(entry.created_at)}</span>
      <div class="flex shrink-0 items-center gap-1.5">
        {#if entry.profile_label}
          <span
            class="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium"
            style="background: {entry.profile_color ?? '#6366f1'}20; color: {entry.profile_color ?? '#6366f1'}"
          >
            {entry.profile_icon ?? '💼'} {entry.profile_label}
          </span>
        {/if}
        {#if entry.enhanced}
          <Badge variant="default" class="h-4 px-1.5 text-[10px] font-medium">AI</Badge>
        {:else}
          <Badge variant="secondary" class="h-4 px-1.5 text-[10px] font-medium">Raw</Badge>
        {/if}
      </div>
    </div>

    <div class="mt-1.5 text-[11px] font-medium text-muted-foreground/70">
      Generated from Profile Snapshot
    </div>
    <div class="mt-2 flex items-center justify-between gap-2 border-t pt-2 text-[11px]">
      <span class="text-muted-foreground">Resume Readiness</span>
      {#if loadingAnalysis}
        <span class="text-muted-foreground">Checking…</span>
      {:else if analysis?.status === 'failed'}
        <span class="font-semibold text-destructive">Analysis failed</span>
      {:else if analysis?.status === 'needs_review'}
        <span class="font-semibold text-amber-700 dark:text-amber-300">Needs review</span>
      {:else if analysis?.overall.score != null}
        <span class="font-semibold">
          {analysis.overall.score} · {formatReadinessBand(analysis.overall.band)}
        </span>
      {:else}
        <span class="text-muted-foreground">Not analyzed</span>
      {/if}
    </div>
  </button>

  <a
    href="/resume?generated_cv_id={entry.id}"
    class="flex items-center justify-between border-t px-3.5 py-2 text-xs font-semibold text-primary transition-colors hover:bg-primary/5"
  >
    {analysis ? 'Open readiness analysis' : 'Analyze this saved resume'}
    <ArrowRight class="h-3.5 w-3.5" />
  </a>
</div>
