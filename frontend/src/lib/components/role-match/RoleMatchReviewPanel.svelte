<script lang="ts">
  import type {
    RoleMatchAnalysisResponse,
    RoleMatchOverrideInput,
    RoleMatchRequirementResponse,
  } from '$lib/role-match-types';
  import { Link2Off, Save, X } from '@lucide/svelte';

  interface Props {
    analysis: RoleMatchAnalysisResponse;
    onSubmit: (overrides: RoleMatchOverrideInput[]) => Promise<void> | void;
    onClose?: () => void;
  }

  let { analysis, onSubmit, onClose }: Props = $props();
  let selectedKey = $state(analysis.requirements[0]?.canonical_key ?? '');
  let action = $state<'importance' | 'no_experience' | 'not_in_profile' | 'evidence_unlink'>('importance');
  let priority = $state<'critical' | 'important' | 'supporting'>('important');
  let evidenceId = $state('');
  let reason = $state('');
  let saving = $state(false);
  let error = $state('');

  const selectedRequirement = $derived(
    analysis.requirements.find((item) => item.canonical_key === selectedKey) ?? null,
  );

  function selectRequirement(requirement: RoleMatchRequirementResponse) {
    selectedKey = requirement.canonical_key;
    evidenceId = requirement.evidence[0]?.evidence_id ?? '';
    priority =
      requirement.importance === 'critical' ||
      requirement.importance === 'important' ||
      requirement.importance === 'supporting'
        ? requirement.importance
        : 'important';
  }

  async function saveCorrection() {
    if (!selectedRequirement) return;
    if (!reason.trim()) {
      error = 'Add a short reason so this correction remains auditable.';
      return;
    }

    let override: RoleMatchOverrideInput;
    if (action === 'importance') {
      override = {
        requirement_key: selectedRequirement.canonical_key,
        field_name: 'importance',
        effective_value: priority,
        reason: reason.trim(),
      };
    } else if (action === 'evidence_unlink') {
      if (!evidenceId) {
        error = 'Choose the evidence that should be unlinked.';
        return;
      }
      override = {
        requirement_key: selectedRequirement.canonical_key,
        field_name: 'evidence_unlink',
        effective_value: evidenceId,
        reason: reason.trim(),
      };
    } else {
      override = {
        requirement_key: selectedRequirement.canonical_key,
        field_name: 'experience_status',
        effective_value: action,
        reason: reason.trim(),
      };
    }

    saving = true;
    error = '';
    try {
      await onSubmit([override]);
      reason = '';
    } catch (caught) {
      error = caught instanceof Error ? caught.message : 'The correction could not be saved.';
    } finally {
      saving = false;
    }
  }
</script>

<section class="rounded-2xl border border-border bg-card shadow-sm" aria-labelledby="review-requirements-title">
  <header class="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
    <div>
      <h2 id="review-requirements-title" class="text-base font-semibold text-foreground">Review requirements</h2>
      <p class="mt-1 text-xs leading-5 text-muted-foreground">
        Correct a requirement or evidence link when the automated interpretation is not accurate.
      </p>
    </div>
    {#if onClose}
      <button type="button" onclick={onClose} class="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-foreground" aria-label="Close review">
        <X class="h-4 w-4" aria-hidden="true" />
      </button>
    {/if}
  </header>

  <div class="grid gap-5 p-5 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
    <div class="space-y-2">
      <p class="text-xs font-semibold text-muted-foreground">Choose a requirement</p>
      <div class="max-h-96 space-y-2 overflow-y-auto pr-1">
        {#each analysis.requirements as requirement}
          <button
            type="button"
            onclick={() => selectRequirement(requirement)}
            class="w-full rounded-xl border px-3.5 py-3 text-left transition-colors {selectedKey === requirement.canonical_key ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted/30'}"
          >
            <span class="block text-sm font-medium text-foreground">{requirement.canonical_text}</span>
            <span class="mt-1 block text-[11px] text-muted-foreground">
              {requirement.primary_category.replaceAll('_', ' ')} · {requirement.importance}
            </span>
          </button>
        {/each}
      </div>
    </div>

    <div class="space-y-4">
      <div>
        <label for="review-action" class="text-xs font-semibold text-muted-foreground">Correction</label>
        <select id="review-action" bind:value={action} class="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm text-foreground">
          <option value="importance">Change requirement priority</option>
          <option value="no_experience">I don’t have this experience</option>
          <option value="not_in_profile">Not included in my profile</option>
          <option value="evidence_unlink">Unlink this evidence</option>
        </select>
      </div>

      {#if action === 'importance'}
        <div>
          <label for="review-priority" class="text-xs font-semibold text-muted-foreground">New priority</label>
          <select id="review-priority" bind:value={priority} class="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm text-foreground">
            <option value="critical">Essential</option>
            <option value="important">Important</option>
            <option value="supporting">Preferred or supporting</option>
          </select>
        </div>
      {:else if action === 'evidence_unlink'}
        <div>
          <label for="review-evidence" class="text-xs font-semibold text-muted-foreground">Evidence to unlink</label>
          <select id="review-evidence" bind:value={evidenceId} class="mt-2 w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm text-foreground">
            <option value="">Choose evidence</option>
            {#each selectedRequirement?.evidence ?? [] as evidence}
              <option value={evidence.evidence_id}>{evidence.source_text}</option>
            {/each}
          </select>
          <p class="mt-2 flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <Link2Off class="h-3.5 w-3.5" aria-hidden="true" />
            The source text stays in the audit history; only this link is removed.
          </p>
        </div>
      {/if}

      <div>
        <label for="review-reason" class="text-xs font-semibold text-muted-foreground">Reason for this correction</label>
        <textarea
          id="review-reason"
          bind:value={reason}
          rows="3"
          placeholder="Explain what the job description or your experience actually says."
          class="mt-2 w-full resize-y rounded-lg border border-border bg-background px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground"
        ></textarea>
      </div>

      <div class="rounded-xl border border-border bg-muted/20 p-3 text-xs leading-5 text-muted-foreground">
        <p>This correction only changes this analysis and creates a new auditable version.</p>
        <button type="button" class="mt-1 font-semibold text-primary hover:underline">
          Add this evidence to my profile separately
        </button>
      </div>

      {#if error}
        <p class="text-xs text-destructive" role="alert">{error}</p>
      {/if}

      <button
        type="button"
        onclick={saveCorrection}
        disabled={saving || !selectedRequirement}
        class="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-xs font-semibold text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
      >
        <Save class="h-3.5 w-3.5" aria-hidden="true" />
        {saving ? 'Saving…' : 'Save correction'}
      </button>
    </div>
  </div>
</section>
