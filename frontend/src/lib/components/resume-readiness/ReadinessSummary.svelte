<script lang="ts">
  import type { ResumeReadinessResponse } from '$lib/resume-readiness-types';
  import ReadinessCategoryCard from './ReadinessCategoryCard.svelte';
  import ReadinessStatusBadge from './ReadinessStatusBadge.svelte';

  interface Props {
    analysis: ResumeReadinessResponse;
  }

  let { analysis }: Props = $props();
</script>

<section class="rounded-2xl border bg-card p-5 shadow-sm" aria-labelledby="resume-readiness-heading">
  <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
    <div>
      <p class="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Resume Readiness</p>
      <h3 id="resume-readiness-heading" class="mt-1 text-2xl font-black">
        {#if analysis.status === 'failed'}
          Analysis failed
        {:else if analysis.status === 'needs_review'}
          Analysis needs review
        {:else if analysis.overall.score != null}
          {analysis.overall.score} / 100
        {:else}
          Not scored
        {/if}
      </h3>
      <p class="mt-1 text-sm text-muted-foreground">
        {analysis.mode === 'job_specific'
          ? 'Parseability, quality, and job tailoring were assessed.'
          : 'Parseability and resume quality were assessed without a target job.'}
      </p>
    </div>
    <ReadinessStatusBadge status={analysis.status} band={analysis.overall.band} />
  </div>

  {#if analysis.overall.hard_gate}
    <div class="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-sm">
      A critical rule capped the result: <code>{analysis.overall.hard_gate}</code>
    </div>
  {/if}

  {#if analysis.failure_code}
    <div class="mt-4 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
      The analysis did not produce a score. Error reference: <code>{analysis.failure_code}</code>
    </div>
  {/if}

  <div class="mt-5 grid gap-3 md:grid-cols-3">
    <ReadinessCategoryCard
      title="ATS Parseability"
      description="Can software extract the resume's essential information?"
      result={analysis.categories.parseability}
    />
    <ReadinessCategoryCard
      title="Resume Quality"
      description="Is the content clear, consistent, and evidence-based?"
      result={analysis.categories.quality}
    />
    <ReadinessCategoryCard
      title="Job Tailoring"
      description="Does this version surface supported evidence for the target job?"
      result={analysis.categories.tailoring}
    />
  </div>

  <div class="mt-4 flex flex-wrap gap-2 text-xs text-muted-foreground">
    <span>{analysis.summary.critical} critical</span>
    <span>•</span>
    <span>{analysis.summary.important} important</span>
    <span>•</span>
    <span>{analysis.summary.improvements} improvements</span>
    <span>•</span>
    <span>{analysis.summary.passed} passed</span>
  </div>
</section>
