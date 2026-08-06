<script lang="ts">
  import { buildRoleMatchViewModel } from '$lib/role-match-presenter';
  import type { RoleMatchAnalysisResponse } from '$lib/role-match-types';
  import AnalysisNeedsReview from './AnalysisNeedsReview.svelte';
  import RoleMatchBreakdown from './RoleMatchBreakdown.svelte';
  import RoleMatchInsights from './RoleMatchInsights.svelte';
  import RoleMatchSummary from './RoleMatchSummary.svelte';

  interface Props {
    analysis: RoleMatchAnalysisResponse;
    companyName?: string | null;
    onReanalyze?: () => void;
    onReview?: () => void;
    analyzing?: boolean;
  }

  let {
    analysis,
    companyName = null,
    onReanalyze,
    onReview,
    analyzing = false,
  }: Props = $props();

  const view = $derived(buildRoleMatchViewModel(analysis));
</script>

<div class="space-y-4">
  {#if view.showScore}
    <RoleMatchSummary {view} {companyName} {onReanalyze} {analyzing} />
    <RoleMatchInsights {view} />
  {:else}
    <AnalysisNeedsReview {view} {onReview} onRetry={onReanalyze} retrying={analyzing} />
  {/if}
  <RoleMatchBreakdown {analysis} />
</div>
