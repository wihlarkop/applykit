<script lang="ts">
  import type { FitAnalysisResponse } from '$lib/types';
  import { Check, AlertTriangle, TrendingUp, ChevronDown, ChevronUp, Sparkles } from '@lucide/svelte';
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
  }

  let { 
    fitResult, 
    companyName = null, 
    onReanalyze, 
    analyzing = false,
    onAcceptEmphasis,
    showInterviewPrep = $bindable(false),
    compact = false
  }: Props = $props();

  const scoreColor = $derived({
    text: fitResult.match_score >= 70 ? 'text-green-600 dark:text-green-400' :
          fitResult.match_score >= 40 ? 'text-yellow-600 dark:text-yellow-400' :
          'text-red-600 dark:text-red-400',
    bg: fitResult.match_score >= 70 ? 'bg-green-500/10 dark:bg-green-500/10' :
        fitResult.match_score >= 40 ? 'bg-yellow-500/10 dark:bg-yellow-500/10' :
        'bg-red-500/10 dark:bg-red-500/10',
    ring: fitResult.match_score >= 70 ? 'ring-green-500/30' :
          fitResult.match_score >= 40 ? 'ring-yellow-500/30' :
          'ring-red-500/30',
  });

  const scoreLabel = $derived(
    fitResult.match_score >= 70 ? 'Strong Match' :
    fitResult.match_score >= 40 ? 'Partial Match' :
    'Weak Match'
  );

  const scoreSummary = $derived(
    fitResult.match_score >= 70 ? 'Your profile covers most key requirements.' :
    fitResult.match_score >= 40 ? 'Your profile partially matches this role.' :
    'Your profile has gaps for this role.'
  );

  const fitTitle = $derived(
    fitResult.match_score >= 70 ? 'Good fit for this role' :
    fitResult.match_score >= 40 ? 'Partial fit for this role' :
    'Weak fit for this role'
  );
</script>

<Card class="shadow-sm">
  <CardContent class="p-6 space-y-5">
    <!-- Header -->
    {#if onReanalyze}
      <div class="flex items-center justify-between">
        <h2 class="font-semibold text-sm flex items-center gap-2">
          <TrendingUp class="w-4 h-4 text-primary" />
          Fit Analysis{companyName ? ` · ${companyName}` : ''}
        </h2>
        <button
          onclick={onReanalyze}
          disabled={analyzing}
          class="text-xs text-muted-foreground hover:text-foreground transition-colors underline cursor-pointer disabled:opacity-50"
        >
          Re-analyze
        </button>
      </div>
    {/if}

    <!-- Score ring + summary -->
    <div class="flex items-center gap-5 p-4 rounded-xl {scoreColor.bg} ring-1 {scoreColor.ring}">
      <ScoreRing score={fitResult.match_score} size={compact ? 64 : 80} />
      
      <!-- Summary -->
      <div class="flex-1 min-w-0">
        <span class="inline-flex items-center gap-1.5 text-[10.5px] font-bold {scoreColor.text} uppercase tracking-wide mb-1.5
          px-2 py-0.5 rounded-full {scoreColor.bg} ring-1 {scoreColor.ring}">
          <Check class="w-3 h-3" /> {scoreLabel}
        </span>
        <p class="text-sm font-semibold text-foreground mb-0.5">
          {fitTitle}
        </p>
        <p class="text-xs text-muted-foreground">{scoreSummary}</p>
      </div>
    </div>

    <!-- Strengths & Gaps side by side -->
    {#if fitResult.pros.length > 0 || fitResult.cons.length > 0}
      <div class="grid grid-cols-2 gap-3">
        <!-- Strengths -->
        {#if fitResult.pros.length > 0}
          <div class="rounded-lg p-3 bg-green-500/8 dark:bg-green-500/10 border border-green-500/20 space-y-2">
            <p class="text-[10px] font-bold text-green-600 dark:text-green-400 uppercase tracking-wide flex items-center gap-1.5">
              <Check class="w-3 h-3" /> Strengths
            </p>
            <ul class="space-y-1.5">
              {#each fitResult.pros as pro}
                <li class="text-xs text-foreground/85 flex gap-1.5 leading-relaxed">
                  <span class="text-green-500 shrink-0 mt-0.5 font-bold">·</span>
                  <span>{pro}</span>
                </li>
              {/each}
            </ul>
          </div>
        {/if}
        
        <!-- Gaps & Red flags -->
        {#if fitResult.cons.length > 0 || fitResult.red_flags.length > 0}
          <div class="rounded-lg p-3 bg-red-500/8 dark:bg-red-500/10 border border-red-500/20 space-y-2">
            <p class="text-[10px] font-bold text-red-600 dark:text-red-400 uppercase tracking-wide flex items-center gap-1.5">
              <AlertTriangle class="w-3 h-3" /> Gaps
            </p>
            <ul class="space-y-1.5">
              {#each fitResult.cons as con}
                <li class="text-xs text-foreground/85 flex gap-1.5 leading-relaxed">
                  <span class="text-red-500 shrink-0 mt-0.5 font-bold">·</span>
                  <span>{con}</span>
                </li>
              {/each}
              {#each fitResult.red_flags as flag}
                <li class="text-xs text-red-600/80 flex gap-1.5 leading-relaxed">
                  <span class="shrink-0 mt-0.5 font-bold">·</span>
                  <span>{flag}</span>
                </li>
              {/each}
            </ul>
          </div>
        {/if}
      </div>
    {/if}

    <!-- Missing keywords -->
    {#if fitResult.missing_keywords.length > 0}
      <div class="space-y-2">
        <p class="text-[10px] font-bold text-muted-foreground uppercase tracking-wide">Missing Keywords</p>
        <div class="flex flex-wrap gap-1.5">
          {#each fitResult.missing_keywords as kw}
            <span class="inline-block bg-red-500/8 dark:bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 rounded-full px-2.5 py-0.5 text-[11px] font-medium font-mono">{kw}</span>
          {/each}
        </div>
      </div>
    {/if}

    <div class="border-t border-border"></div>

    <!-- Suggested emphasis -->
    {#if onAcceptEmphasis}
      <div class="rounded-lg border border-primary/20 bg-primary/5 dark:bg-primary/10 p-4 space-y-2.5">
        <p class="text-[10px] font-bold text-primary uppercase tracking-wide flex items-center gap-1.5">
          <Sparkles class="w-3 h-3" /> AI Suggested Emphasis
        </p>
        <p class="text-sm text-foreground/80 leading-relaxed">{fitResult.suggested_emphasis}</p>
        <button
          onclick={onAcceptEmphasis}
          class="inline-flex items-center gap-1.5 text-xs text-primary font-semibold hover:underline cursor-pointer transition-colors"
        >
          <Check class="w-3 h-3" /> Use this suggestion
        </button>
      </div>
    {:else if fitResult.suggested_emphasis}
      <div class="rounded-lg border border-primary/20 bg-primary/5 dark:bg-primary/10 p-4 space-y-2">
        <p class="text-[10px] font-bold text-primary uppercase tracking-wide flex items-center gap-1.5">
          <Sparkles class="w-3 h-3" /> AI Suggested Emphasis
        </p>
        <p class="text-sm text-foreground/80 leading-relaxed">{fitResult.suggested_emphasis}</p>
      </div>
    {/if}

    <!-- Interview prep collapsible -->
    {#if fitResult.interview_questions.length > 0}
      <div class="border border-border rounded-lg overflow-hidden">
        <button
          class="flex items-center justify-between w-full text-sm font-semibold cursor-pointer px-4 py-3 bg-muted/30 hover:bg-muted/50 transition-colors"
          onclick={() => showInterviewPrep = !showInterviewPrep}
        >
          <span class="flex items-center gap-2">
            Interview Prep Questions
            <span class="text-[10px] font-bold bg-primary/10 text-primary px-1.5 py-0.5 rounded-full">{fitResult.interview_questions.length}</span>
          </span>
          {#if showInterviewPrep}
            <ChevronUp class="w-4 h-4 text-muted-foreground" />
          {:else}
            <ChevronDown class="w-4 h-4 text-muted-foreground" />
          {/if}
        </button>
        {#if showInterviewPrep}
          <ul class="divide-y divide-border">
            {#each fitResult.interview_questions as q, i}
              <li class="px-4 py-3 text-sm text-muted-foreground flex gap-3">
                <span class="shrink-0 font-bold text-primary font-mono text-xs mt-0.5">Q{i + 1}</span>
                <span>{q}</span>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
    {/if}
  </CardContent>
</Card>
