<script lang="ts">
  import type { RoleMatchAnalysisResponse } from '$lib/role-match-types';
  import { ChevronDown, ChevronUp, Info } from '@lucide/svelte';

  interface Props {
    analysis: RoleMatchAnalysisResponse;
  }

  let { analysis }: Props = $props();
  let open = $state(false);
  let methodologyOpen = $state(false);

  const categoryLabels: Record<string, string> = {
    essential_qualifications: 'Essential qualifications',
    relevant_competencies: 'Relevant competencies',
    relevant_work_tasks: 'Relevant work and tasks',
    preferred_qualifications: 'Preferred qualifications',
    contextual_alignment: 'Contextual alignment',
  };

  const matchLabels: Record<string, string> = {
    strong: 'Strong match',
    moderate: 'Moderate match',
    weak: 'Weak match',
    no_evidence: 'No supporting evidence',
    unknown: 'Needs confirmation',
    contradictory_evidence: 'Conflicting information',
  };
</script>

<section class="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
  <button
    type="button"
    class="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition-colors hover:bg-muted/30"
    onclick={() => (open = !open)}
    aria-expanded={open}
  >
    <span>
      <span class="block text-sm font-semibold text-foreground">See detailed breakdown</span>
      <span class="mt-0.5 block text-xs text-muted-foreground">
        Review categories, requirements, and the evidence used for each assessment.
      </span>
    </span>
    {#if open}
      <ChevronUp class="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
    {:else}
      <ChevronDown class="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
    {/if}
  </button>

  {#if open}
    <div class="space-y-6 border-t border-border px-5 py-5">
      {#if analysis.category_breakdown.length}
        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {#each analysis.category_breakdown as category}
            <div class="rounded-xl border border-border bg-muted/20 p-3.5">
              <div class="flex items-start justify-between gap-3">
                <p class="text-xs font-semibold text-foreground">
                  {categoryLabels[category.category] ?? category.category.replaceAll('_', ' ')}
                </p>
                <span class="text-sm font-semibold text-primary">{Math.round(category.score * 100)}</span>
              </div>
              <div class="mt-3 h-1.5 overflow-hidden rounded-full bg-muted">
                <div
                  class="h-full rounded-full bg-primary"
                  style={`width: ${Math.round(category.score * 100)}%`}
                ></div>
              </div>
              <p class="mt-2 text-[11px] text-muted-foreground">
                {category.requirement_count} requirement{category.requirement_count === 1 ? '' : 's'} reviewed
              </p>
            </div>
          {/each}
        </div>
      {/if}

      <div class="space-y-3">
        {#each analysis.requirements as requirement}
          <article class="rounded-xl border border-border p-4">
            <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p class="text-sm font-medium text-foreground">{requirement.canonical_text}</p>
                <p class="mt-1 text-xs text-muted-foreground">
                  {categoryLabels[requirement.primary_category] ?? requirement.primary_category.replaceAll('_', ' ')}
                  · {requirement.importance}
                  {requirement.mention_count > 1 ? ` · mentioned ${requirement.mention_count} times` : ''}
                </p>
              </div>
              <span class="w-fit rounded-full bg-muted px-2.5 py-1 text-[11px] font-semibold text-foreground">
                {matchLabels[requirement.match_level ?? 'unknown'] ?? 'Needs review'}
              </span>
            </div>

            {#if requirement.explanation}
              <p class="mt-3 text-xs leading-5 text-muted-foreground">{requirement.explanation}</p>
            {/if}

            {#if requirement.importance_conflict}
              <p class="mt-3 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-xs text-amber-800 dark:text-amber-200">
                This requirement is emphasized inconsistently in the job description and was treated using its strongest explicit wording.
              </p>
            {/if}

            {#if requirement.evidence.length}
              <div class="mt-3 space-y-2">
                {#each requirement.evidence as evidence}
                  <div class="rounded-lg bg-muted/25 px-3 py-2.5">
                    <p class="text-xs text-foreground">{evidence.source_text}</p>
                    <p class="mt-1 text-[11px] text-muted-foreground">
                      {evidence.source_type.replaceAll('_', ' ')} · {evidence.relationship.replaceAll('_', ' ')}
                    </p>
                  </div>
                {/each}
              </div>
            {/if}
          </article>
        {/each}
      </div>

      {#if analysis.excluded_items.length}
        <div class="rounded-xl border border-border bg-muted/20 p-4">
          <p class="text-xs font-semibold text-foreground">
            {analysis.excluded_items.length} requirement{analysis.excluded_items.length === 1 ? '' : 's'} excluded from scoring
          </p>
          <ul class="mt-2 space-y-1.5">
            {#each analysis.excluded_items as item}
              <li class="text-xs leading-5 text-muted-foreground">{item.text}</li>
            {/each}
          </ul>
        </div>
      {/if}

      <div class="rounded-xl border border-border">
        <button
          type="button"
          class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
          onclick={() => (methodologyOpen = !methodologyOpen)}
          aria-expanded={methodologyOpen}
        >
          <span class="flex items-center gap-2 text-xs font-semibold text-foreground">
            <Info class="h-4 w-4 text-primary" aria-hidden="true" />
            How this assessment works
          </span>
          {#if methodologyOpen}
            <ChevronUp class="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          {:else}
            <ChevronDown class="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          {/if}
        </button>
        {#if methodologyOpen}
          <div class="border-t border-border px-4 py-4 text-xs leading-5 text-muted-foreground">
            ApplyKit identifies job-related requirements, links them to evidence from your profile, and applies fixed rules for evidence source, depth, relevance, and recency. Eligibility and confidence are reported separately. This is guidance for tailoring an application, not a prediction of a hiring decision.
          </div>
        {/if}
      </div>
    </div>
  {/if}
</section>
