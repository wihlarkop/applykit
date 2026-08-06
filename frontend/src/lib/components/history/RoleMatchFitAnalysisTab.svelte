<script lang="ts">
  import type { RoleMatchAnalysisResponse } from '$lib/role-match-types';
  import RoleMatchResult from '../role-match/RoleMatchResult.svelte';
  import LegacyFitAnalysisTab from './FitAnalysisTab.svelte';

  interface LegacyAnalysis {
    match_score: number;
    pros: string[];
    cons: string[];
    missing_keywords: string[];
    red_flags: string[];
    suggested_emphasis: string;
    interview_questions: string[];
    role_match_analysis?: RoleMatchAnalysisResponse;
  }

  interface Props {
    analysis: LegacyAnalysis;
  }

  let { analysis }: Props = $props();
  const roleMatchAnalysis = $derived(analysis.role_match_analysis ?? null);
</script>

{#if roleMatchAnalysis}
  <div class="p-5 md:p-6">
    <RoleMatchResult analysis={roleMatchAnalysis} />
  </div>
{:else}
  <LegacyFitAnalysisTab {analysis} />
{/if}
