<script lang="ts">
  import { CheckCircle2, XCircle, AlertTriangle, Lightbulb, MessageSquare } from '@lucide/svelte';
  import { getScoreColor, getScoreBarColor } from '$lib/utils';
  import { Badge } from '$lib/components/ui/badge';

  interface FitAnalysis {
    match_score: number;
    pros: string[];
    cons: string[];
    missing_keywords: string[];
    red_flags: string[];
    suggested_emphasis: string;
    interview_questions: string[];
  }

  interface Props {
    analysis: FitAnalysis;
  }

  let { analysis }: Props = $props();

  const scoreColorClass = (score: number) => getScoreColor(score).text;
</script>

<div class="p-5 md:p-6 space-y-6 bg-muted/5 min-h-full">
  <!-- Match score header -->
  <div class="bg-card border border-border/50 rounded-xl p-4 shadow-sm">
    <div class="flex justify-between items-center text-sm mb-2">
      <span class="font-bold text-foreground tracking-tight">Overall Match Prediction</span>
      <span class="font-black text-lg {scoreColorClass(analysis.match_score)}">{analysis.match_score}%</span>
    </div>
    <div class="bg-muted rounded-full h-1.5 overflow-hidden">
      <div class="h-1.5 rounded-full {getScoreBarColor(analysis.match_score)}" style="width:{analysis.match_score}%"></div>
    </div>
  </div>

  <!-- Strengths / Gaps -->
  {#if analysis.pros.length > 0 || analysis.cons.length > 0}
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      {#if analysis.pros.length > 0}
        <div class="border border-green-500/20 bg-green-500/5 rounded-xl p-4 shadow-sm">
          <div class="flex items-center gap-2 mb-3">
            <CheckCircle2 class="w-4 h-4 text-green-600" />
            <h3 class="text-sm font-bold text-green-700 tracking-tight">Key Strengths</h3>
          </div>
          <ul class="space-y-2">
            {#each analysis.pros as pro}
              <li class="text-[13px] text-muted-foreground/90 flex items-start gap-2 leading-relaxed">
                <span class="text-green-500 mt-1 shrink-0 text-[10px]">●</span>
                <span>{pro}</span>
              </li>
            {/each}
          </ul>
        </div>
      {/if}

      {#if analysis.cons.length > 0}
        <div class="border border-red-500/20 bg-red-500/5 rounded-xl p-4 shadow-sm">
          <div class="flex items-center gap-2 mb-3">
            <XCircle class="w-4 h-4 text-red-500" />
            <h3 class="text-sm font-bold text-red-600 tracking-tight">Potential Gaps</h3>
          </div>
          <ul class="space-y-2">
            {#each analysis.cons as con}
              <li class="text-[13px] text-muted-foreground/90 flex items-start gap-2 leading-relaxed">
                <span class="text-red-400 mt-1 shrink-0 text-[10px]">●</span>
                <span>{con}</span>
              </li>
            {/each}
          </ul>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Missing Keywords -->
  {#if analysis.missing_keywords.length > 0}
    <div class="bg-card border border-border/50 rounded-xl p-4 shadow-sm">
      <h3 class="text-sm font-bold text-foreground mb-3 tracking-tight">Recommended Keywords</h3>
      <div class="flex flex-wrap gap-1.5">
        {#each analysis.missing_keywords as kw}
          <Badge variant="outline" class="font-medium bg-background text-muted-foreground">{kw}</Badge>
        {/each}
      </div>
    </div>
  {/if}

  <!-- Red Flags -->
  {#if analysis.red_flags.length > 0}
    <div class="border border-amber-500/30 bg-amber-500/10 rounded-xl p-4 shadow-sm">
      <div class="flex items-center gap-2 mb-3">
        <AlertTriangle class="w-4 h-4 text-amber-600" />
        <h3 class="text-sm font-bold text-amber-700 tracking-tight">Critical Red Flags</h3>
      </div>
      <ul class="space-y-2">
        {#each analysis.red_flags as flag}
          <li class="text-[13px] text-amber-900/80 dark:text-amber-200/80 flex items-start gap-2 leading-relaxed">
            <span class="text-amber-500 mt-1 shrink-0 text-[10px]">●</span>
            <span>{flag}</span>
          </li>
        {/each}
      </ul>
    </div>
  {/if}

  <!-- Suggested Emphasis -->
  {#if analysis.suggested_emphasis}
    <div class="bg-primary/5 border border-primary/20 rounded-xl p-4 shadow-sm">
      <div class="flex items-center gap-2 mb-2">
        <Lightbulb class="w-4 h-4 text-primary" />
        <h3 class="text-sm font-bold text-primary tracking-tight">Strategic Emphasis</h3>
      </div>
      <p class="text-[13px] text-muted-foreground/90 leading-relaxed pl-6">{analysis.suggested_emphasis}</p>
    </div>
  {/if}

  <!-- Interview Questions -->
  {#if analysis.interview_questions.length > 0}
    <div class="bg-card border border-border/50 rounded-xl p-4 shadow-sm">
      <div class="flex items-center gap-2 mb-4">
        <MessageSquare class="w-4 h-4 text-foreground/80" />
        <h3 class="text-sm font-bold text-foreground tracking-tight">Predicted Interview Questions</h3>
      </div>
      <div class="space-y-3 pl-2">
        {#each analysis.interview_questions as q, i}
          <div class="flex gap-3 items-start">
            <span class="font-black text-muted-foreground/40 text-sm shrink-0 w-4">{i + 1}.</span>
            <p class="text-[13px] font-medium text-muted-foreground/90 leading-relaxed pt-0.5">{q}</p>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>
