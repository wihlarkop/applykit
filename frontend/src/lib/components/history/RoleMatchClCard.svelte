<script lang="ts">
  import { goto } from '$app/navigation';
  import { STATUS_CONFIG } from '$lib/constants';
  import type { GeneratedCoverLetterEntry } from '$lib/types';
  import { formatDateShort, getScoreBarColor, getScoreColor } from '$lib/utils';

  interface SourceAwareEntry extends GeneratedCoverLetterEntry {
    match_score_source?: 'role_evidence_match' | 'legacy_llm_score' | 'none';
    role_match_analysis_id?: number | null;
  }

  interface Props {
    entry: SourceAwareEntry;
    selected: boolean;
    onSelect: () => void;
    selectedForBatch?: boolean;
    onToggleBatchSelect?: () => void;
    onStatusChange: (id: number, status: string | null) => void;
  }

  let {
    entry,
    selected,
    onSelect,
    selectedForBatch = false,
    onToggleBatchSelect,
    onStatusChange,
  }: Props = $props();

  const STATUS_PIPELINE = Object.entries(STATUS_CONFIG).map(([value, config]) => ({
    value,
    ...config,
  }));

  function displayCompany(value: GeneratedCoverLetterEntry): string {
    if (value.company_name) return value.company_name;
    const firstLine = value.job_description
      .split('\n')[0]
      .trim()
      .replace(/^(title|job title|position|role)\s*:\s*/i, '');
    const atMatch = firstLine.match(/\bat\s+([^,(\n]+)/i);
    if (atMatch) return atMatch[1].trim().slice(0, 30);
    const dashMatch = firstLine.match(/\s[-–]\s*([A-Za-z]\S+)/);
    if (dashMatch) return dashMatch[1].slice(0, 30);
    return firstLine.length > 30 ? `${firstLine.slice(0, 27)}…` : firstLine;
  }

  function displayRole(value: GeneratedCoverLetterEntry): string {
    const firstLine = value.job_description
      .split('\n')[0]
      .trim()
      .replace(/^(title|job title|position|role)\s*:\s*/i, '');
    const text = firstLine.replace(/\s[-–]\s*\S+.*$/, '').trim() || firstLine;
    return text.length > 50 ? `${text.slice(0, 47)}…` : text;
  }

  function scoreColorClass(score: number): string {
    const colors = getScoreColor(score);
    return `${colors.bg} ${colors.text}`;
  }

  const role = $derived(displayRole(entry));
  const company = $derived(displayCompany(entry));
  const sourceLabel = $derived(
    entry.match_score_source === 'role_evidence_match'
      ? 'Evidence match'
      : entry.match_score_source === 'legacy_llm_score'
        ? 'Legacy score'
        : 'Match',
  );
</script>

<div class="group relative flex items-start gap-1.5">
  {#if onToggleBatchSelect}
    <input
      type="checkbox"
      class="z-10 mt-3.5 shrink-0 rounded"
      checked={selectedForBatch}
      onclick={(event) => event.stopPropagation()}
      onchange={onToggleBatchSelect}
    />
  {/if}

  <div
    role="button"
    tabindex="0"
    onclick={onSelect}
    onkeydown={(event) => {
      if (event.key === 'Enter' || event.key === ' ') onSelect();
    }}
    class="relative flex-1 cursor-pointer overflow-hidden rounded-xl border p-3.5 text-left outline-none transition-all {selected ? 'scale-[1.01] border-primary/50 bg-primary/5 shadow-md ring-1 ring-primary/20' : 'border-border/60 bg-card hover:border-border hover:bg-accent/50 hover:shadow-sm'}"
  >
    <div class="mb-1 flex items-center justify-between gap-2">
      <span class="truncate text-[13px] font-semibold text-foreground/90">{company}</span>
      <div class="flex shrink-0 items-center gap-1.5">
        {#if entry.match_score !== null}
          <span class="rounded px-1.5 py-0.5 text-[10px] font-semibold {scoreColorClass(entry.match_score)}">
            {entry.match_score}%
          </span>
        {/if}
        {#if entry.profile_color && entry.profile_icon}
          <span class="flex items-center rounded-sm bg-muted/50 px-1 py-0.5 text-[10px] text-muted-foreground">
            {entry.profile_icon}
          </span>
        {/if}
      </div>
    </div>

    <div class="mt-0.5 flex items-center justify-between gap-2">
      {#if role}
        <span class="flex-1 truncate text-[11px] font-medium text-muted-foreground/80">{role}</span>
      {/if}
      <span class="ml-auto shrink-0 text-[11px] font-medium text-muted-foreground">{formatDateShort(entry.created_at)}</span>
    </div>

    {#if entry.match_score !== null}
      <p class="mt-2 text-[9px] font-semibold uppercase tracking-wide text-muted-foreground/70">
        {sourceLabel}
      </p>
    {/if}

    {#if entry.application_id}
      <span
        role="button"
        tabindex="0"
        class="absolute right-3 top-3.5 cursor-pointer text-primary/70 transition-colors hover:text-primary"
        onclick={(event) => {
          event.stopPropagation();
          goto('/tracker');
        }}
        onkeydown={(event) => {
          if (event.key === 'Enter') {
            event.stopPropagation();
            goto('/tracker');
          }
        }}
        title="View in Tracker"
        aria-label="View in Tracker"
      >📌</span>
    {/if}

    <div
      class="mt-3 flex flex-wrap items-center gap-1"
      role="presentation"
      onclick={(event) => event.stopPropagation()}
      onkeydown={(event) => event.stopPropagation()}
    >
      {#each STATUS_PIPELINE as status}
        <button
          class="cursor-pointer rounded-full border px-2 py-0.5 text-[10px] font-medium transition-all {entry.application_status === status.value ? status.activeClass : 'border-border/50 text-muted-foreground opacity-70 hover:border-border hover:bg-accent/80'}"
          onclick={() => onStatusChange(entry.id, status.value)}
        >
          {status.label}
        </button>
      {/each}
    </div>

    {#if entry.match_score !== null}
      <div class="absolute bottom-0 left-0 right-0 h-0.5 bg-muted/50">
        <div
          class="h-0.5 transition-all duration-500 ease-out {getScoreBarColor(entry.match_score)}"
          style={`width: ${entry.match_score}%`}
        ></div>
      </div>
    {/if}
  </div>
</div>
