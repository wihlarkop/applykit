<script lang="ts">
  import {
    applyRoleMatchOverrides,
    compareRoleMatchVersions,
    getRoleMatchVersions,
    restoreRoleMatchOverride,
  } from '$lib/role-match-api';
  import type {
    RoleMatchAnalysisResponse,
    RoleMatchComparisonResponse,
    RoleMatchOverrideInput,
    RoleMatchOverrideResponse,
    RoleMatchVersionsResponse,
  } from '$lib/role-match-types';
  import type { FitAnalysisResponse } from '$lib/types';
  import { Check } from '@lucide/svelte';
  import LegacyFitAnalysisDisplay from './FitAnalysisDisplay.svelte';
  import RoleMatchResult from './role-match/RoleMatchResult.svelte';
  import RoleMatchReviewPanel from './role-match/RoleMatchReviewPanel.svelte';
  import RoleMatchVersionCompare from './role-match/RoleMatchVersionCompare.svelte';

  interface CompatibleFitAnalysis extends FitAnalysisResponse {
    role_match_analysis_id?: number;
    role_match_analysis?: RoleMatchAnalysisResponse;
  }

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
    embedded = false,
  }: Props = $props();

  let analysis = $state<RoleMatchAnalysisResponse | null>(null);
  let reviewOpen = $state(false);
  let versions = $state<RoleMatchVersionsResponse | null>(null);
  let comparison = $state<RoleMatchComparisonResponse | null>(null);
  let historyRequestId = 0;

  const incomingAnalysis = $derived(
    (fitResult as CompatibleFitAnalysis).role_match_analysis ?? null,
  );

  $effect(() => {
    if (incomingAnalysis && incomingAnalysis.id !== analysis?.id) {
      analysis = incomingAnalysis;
    }
  });

  $effect(() => {
    if (!analysis) return;
    const requestId = ++historyRequestId;
    const current = analysis;
    void (async () => {
      try {
        const nextVersions = await getRoleMatchVersions(current.id);
        if (requestId !== historyRequestId) return;
        versions = nextVersions;
        if (current.parent_analysis_id) {
          comparison = await compareRoleMatchVersions(
            current.parent_analysis_id,
            current.id,
          );
        } else {
          comparison = null;
        }
      } catch {
        if (requestId === historyRequestId) {
          versions = null;
          comparison = null;
        }
      }
    })();
  });

  async function submitOverrides(overrides: RoleMatchOverrideInput[]) {
    if (!analysis) return;
    analysis = await applyRoleMatchOverrides(analysis.id, { overrides });
    reviewOpen = false;
  }

  async function restoreOverride(override: RoleMatchOverrideResponse) {
    if (!analysis) return;
    analysis = await restoreRoleMatchOverride(analysis.id, override.id);
  }
</script>

{#if analysis}
  <div class="space-y-4">
    <RoleMatchResult
      {analysis}
      {companyName}
      {onReanalyze}
      onReview={() => (reviewOpen = true)}
      {analyzing}
    />

    {#if reviewOpen}
      <RoleMatchReviewPanel
        {analysis}
        onSubmit={submitOverrides}
        onClose={() => (reviewOpen = false)}
      />
    {/if}

    {#if analysis.parent_analysis_id || analysis.overrides.length || versions?.items.length}
      <RoleMatchVersionCompare
        {analysis}
        {versions}
        {comparison}
        onRestore={restoreOverride}
      />
    {/if}

    {#if onAcceptEmphasis && analysis.summary?.next_step}
      <button
        type="button"
        onclick={onAcceptEmphasis}
        class="inline-flex items-center gap-2 rounded-lg border border-primary/20 bg-primary/5 px-3.5 py-2 text-xs font-semibold text-primary hover:bg-primary/10"
      >
        <Check class="h-3.5 w-3.5" aria-hidden="true" />
        Use this guidance
      </button>
    {/if}
  </div>
{:else}
  <LegacyFitAnalysisDisplay
    {fitResult}
    {companyName}
    {onReanalyze}
    {analyzing}
    {onAcceptEmphasis}
    bind:showInterviewPrep
    {compact}
    {embedded}
  />
{/if}
