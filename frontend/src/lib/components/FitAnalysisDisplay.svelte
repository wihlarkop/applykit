<script lang="ts">
	import type { FitAnalysisResponse } from '$lib/types';
	import { getFitTitle, getScoreColor, getScoreLabel, getScoreSummary } from '$lib/utils';
	import { AlertTriangle, Check, ChevronDown, ChevronUp, Sparkles, TrendingUp } from '@lucide/svelte';
	import ScoreRing from './ScoreRing.svelte';
	import { Card, CardContent } from './ui/card';

	interface Props {
		fitResult: FitAnalysisResponse;
		companyName?: string | null;
		onReanalyze?: () => void;
		analyzing?: boolean;
		onAcceptEmphasis?: () => void;
		showInterviewPrep?: boolean;
		compact?: boolean;
		embedded?: boolean;
	}

	let {
		fitResult,
		companyName = null,
		onReanalyze,
		analyzing = false,
		onAcceptEmphasis,
		showInterviewPrep = $bindable(false),
		compact = false,
		embedded = false
	}: Props = $props();

	const scoreColor = $derived(getScoreColor(fitResult.match_score));
	const scoreLabel = $derived(getScoreLabel(fitResult.match_score));
	const scoreSummary = $derived(getScoreSummary(fitResult.match_score));
	const fitTitle = $derived(getFitTitle(fitResult.match_score));
</script>

<Card class={embedded ? 'border-0 shadow-none' : 'shadow-sm'}>
  <CardContent class={embedded ? 'space-y-5 p-0' : 'space-y-5 p-6'}>
    {#if onReanalyze}
      <div class="flex items-center justify-between gap-3">
        <h2 class="flex items-center gap-2 text-sm font-semibold">
          <TrendingUp class="h-4 w-4 text-primary" />
          Fit Analysis{companyName ? ` · ${companyName}` : ''}
        </h2>
        <button
          onclick={onReanalyze}
          disabled={analyzing}
          class="cursor-pointer text-xs text-muted-foreground underline transition-colors hover:text-foreground disabled:opacity-50"
        >
          Re-analyze
        </button>
      </div>
    {/if}

    <div class="flex items-center gap-5 rounded-xl p-4 {scoreColor.bg} ring-1 {scoreColor.ring}">
      <ScoreRing score={fitResult.match_score} size={compact ? 64 : 80} />

      <div class="min-w-0 flex-1">
        <span class="mb-1.5 inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10.5px] font-bold uppercase tracking-wide {scoreColor.text} {scoreColor.bg} ring-1 {scoreColor.ring}">
          <Check class="h-3 w-3" /> {scoreLabel}
        </span>
        <p class="mb-0.5 text-sm font-semibold text-foreground">
          {fitTitle}
        </p>
        <p class="text-xs leading-5 text-muted-foreground">{scoreSummary}</p>
      </div>
    </div>

    {#if fitResult.pros.length > 0 || fitResult.cons.length > 0}
      <div class="grid gap-4 2xl:grid-cols-2">
        {#if fitResult.pros.length > 0}
          <div class="space-y-3 rounded-xl border border-green-500/20 bg-green-500/8 p-4 dark:bg-green-500/10">
            <p class="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-green-600 dark:text-green-400">
              <Check class="h-3.5 w-3.5" /> Strengths
            </p>
            <ul class="space-y-3">
              {#each fitResult.pros as pro}
                <li class="flex gap-2 text-sm leading-6 text-foreground/85">
                  <span class="mt-0.5 shrink-0 font-bold text-green-500">·</span>
                  <span>{pro}</span>
                </li>
              {/each}
            </ul>
          </div>
        {/if}

        {#if fitResult.cons.length > 0}
          <div class="space-y-3 rounded-xl border border-red-500/20 bg-red-500/8 p-4 dark:bg-red-500/10">
            <p class="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-red-600 dark:text-red-400">
              <AlertTriangle class="h-3.5 w-3.5" /> Gaps
            </p>
            <ul class="space-y-3">
              {#each fitResult.cons as con}
                <li class="flex gap-2 text-sm leading-6 text-foreground/85">
                  <span class="mt-0.5 shrink-0 font-bold text-red-500">·</span>
                  <span>{con}</span>
                </li>
              {/each}
            </ul>
          </div>
        {/if}
      </div>
    {/if}

    {#if fitResult.red_flags && fitResult.red_flags.length > 0}
      <div class="space-y-1.5 rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-900 dark:bg-red-950/30">
        <div class="mb-2 flex items-center gap-1.5">
          <AlertTriangle class="h-3.5 w-3.5 shrink-0 text-red-500" />
          <span class="text-xs font-bold uppercase tracking-wide text-red-600 dark:text-red-400">Red Flags</span>
        </div>
        <ul class="space-y-2">
          {#each fitResult.red_flags as flag}
            <li class="flex gap-2 text-sm leading-6 text-red-700 dark:text-red-300">
              <span class="mt-0.5 shrink-0">⚠</span>
              <span>{flag}</span>
            </li>
          {/each}
        </ul>
      </div>
    {/if}

    {#if fitResult.missing_keywords.length > 0}
      <div class="space-y-2">
        <p class="text-[10px] font-bold uppercase tracking-wide text-muted-foreground">Missing Keywords</p>
        <div class="flex flex-wrap gap-1.5">
          {#each fitResult.missing_keywords as kw}
            <span class="inline-block rounded-full border border-red-500/20 bg-red-500/8 px-2.5 py-0.5 font-mono text-[11px] font-medium text-red-600 dark:bg-red-500/10 dark:text-red-400">{kw}</span>
          {/each}
        </div>
      </div>
    {/if}

    <div class="border-t border-border"></div>

    {#if onAcceptEmphasis}
      <div class="space-y-2.5 rounded-xl border border-primary/20 bg-primary/5 p-4 dark:bg-primary/10">
        <p class="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wide text-primary">
          <Sparkles class="h-3 w-3" /> AI Suggested Emphasis
        </p>
        <p class="text-sm leading-6 text-foreground/80">{fitResult.suggested_emphasis}</p>
        <button
          onclick={onAcceptEmphasis}
          class="inline-flex cursor-pointer items-center gap-1.5 text-xs font-semibold text-primary transition-colors hover:underline"
        >
          <Check class="h-3 w-3" /> Use this suggestion
        </button>
      </div>
    {:else if fitResult.suggested_emphasis}
      <div class="space-y-2 rounded-xl border border-primary/20 bg-primary/5 p-4 dark:bg-primary/10">
        <p class="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wide text-primary">
          <Sparkles class="h-3 w-3" /> AI Suggested Emphasis
        </p>
        <p class="text-sm leading-6 text-foreground/80">{fitResult.suggested_emphasis}</p>
      </div>
    {/if}

    {#if fitResult.interview_questions.length > 0}
      <div class="overflow-hidden rounded-lg border border-border">
        <button
          class="flex w-full cursor-pointer items-center justify-between bg-muted/30 px-4 py-3 text-sm font-semibold transition-colors hover:bg-muted/50"
          onclick={() => showInterviewPrep = !showInterviewPrep}
          aria-expanded={showInterviewPrep}
        >
          <span class="flex items-center gap-2">
            Interview Prep Questions
            <span class="rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-bold text-primary">{fitResult.interview_questions.length}</span>
          </span>
          {#if showInterviewPrep}
            <ChevronUp class="h-4 w-4 text-muted-foreground" />
          {:else}
            <ChevronDown class="h-4 w-4 text-muted-foreground" />
          {/if}
        </button>
        {#if showInterviewPrep}
          <ul class="divide-y divide-border">
            {#each fitResult.interview_questions as q, i}
              <li class="flex gap-3 px-4 py-4 text-sm leading-6 text-muted-foreground">
                <span class="mt-0.5 shrink-0 font-mono text-xs font-bold text-primary">Q{i + 1}</span>
                <span>{q}</span>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
    {/if}
  </CardContent>
</Card>
