<script lang="ts">
  import { Sparkles } from '@lucide/svelte';
  import { formatDateShort, getScoreBarColor, getScoreColor } from '$lib/utils';
  import type { GeneratedCoverLetterEntry } from '$lib/types';
  import { goto } from '$app/navigation';
  import { STATUS_CONFIG } from '$lib/constants';

  interface Props {
    entry: GeneratedCoverLetterEntry;
    selected: boolean;
    onSelect: () => void;
    selectedForBatch?: boolean; // If batch deletion is active
    onToggleBatchSelect?: () => void;
    onStatusChange: (id: number, status: string | null) => void;
  }

  let { 
    entry, 
    selected, 
    onSelect, 
    selectedForBatch = false, 
    onToggleBatchSelect,
    onStatusChange
  }: Props = $props();

  const STATUS_PIPELINE = Object.entries(STATUS_CONFIG).map(([value, config]) => ({
    value,
    ...config,
  }));

  function displayCompany(entry: GeneratedCoverLetterEntry): string {
    if (entry.company_name) return entry.company_name;
    const firstLine = entry.job_description.split('\n')[0].trim()
      .replace(/^(title|job title|position|role)\s*:\s*/i, '');
    const atMatch = firstLine.match(/\bat\s+([^,(\n]+)/i);
    if (atMatch) return atMatch[1].trim().slice(0, 30);
    const dashMatch = firstLine.match(/\s[-–]\s*([A-Za-z]\S+)/);
    if (dashMatch) return dashMatch[1].slice(0, 30);
    return firstLine.length > 30 ? firstLine.slice(0, 27) + '…' : firstLine;
  }

  function displayRole(entry: GeneratedCoverLetterEntry): string {
    const firstLine = entry.job_description.split('\n')[0].trim()
      .replace(/^(title|job title|position|role)\s*:\s*/i, '');
    if (!firstLine) return '';
    const clean = firstLine.replace(/\s[-–]\s*\S+.*$/, '').trim();
    const text = clean || firstLine;
    return text.length > 50 ? text.slice(0, 47) + '…' : text;
  }

  function scoreColorClass(score: number): string {
    const colors = getScoreColor(score);
    return `${colors.bg} ${colors.text}`;
  }

  const role = $derived(displayRole(entry));
  const company = $derived(displayCompany(entry));
</script>

<div class="flex items-start gap-1.5 relative group">
  {#if onToggleBatchSelect}
    <input
      type="checkbox"
      class="mt-3.5 rounded shrink-0 z-10"
      checked={selectedForBatch}
      onclick={(e) => e.stopPropagation()}
      onchange={onToggleBatchSelect}
    />
  {/if}
  
  <div
    role="button"
    tabindex="0"
    onclick={onSelect}
    onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') onSelect(); }}
    class="relative flex-1 text-left border rounded-xl p-3.5 transition-all outline-none overflow-hidden cursor-pointer
      {selected ? 'border-primary/50 bg-primary/5 shadow-md ring-1 ring-primary/20 scale-[1.01]' : 'border-border/60 bg-card hover:border-border hover:shadow-sm hover:bg-accent/50'}
    "
  >
    <!-- Top Row: Company & Score -->
    <div class="flex items-center justify-between gap-2 mb-1">
      <span class="text-[13px] font-semibold truncate text-foreground/90">{company}</span>
      <div class="flex items-center gap-1.5 shrink-0">
        {#if entry.match_score !== null}
          <span class="text-[10px] px-1.5 py-0.5 rounded font-semibold {scoreColorClass(entry.match_score)}">
            {entry.match_score}%
          </span>
        {/if}
        {#if entry.profile_color && entry.profile_icon}
          <span class="flex items-center text-[10px] text-muted-foreground bg-muted/50 px-1 py-0.5 rounded-sm">
            {entry.profile_icon}
          </span>
        {/if}
      </div>
    </div>

    <!-- Row 2: Role & Date -->
    <div class="flex items-center justify-between mt-0.5 gap-2">
      {#if role}
        <span class="text-[11px] font-medium text-muted-foreground/80 truncate flex-1">{role}</span>
      {/if}
      <span class="text-[11px] font-medium text-muted-foreground shrink-0 ml-auto">{formatDateShort(entry.created_at)}</span>
    </div>

    <!-- Tracking Shortcut -->
    {#if entry.application_id}
      <span
        role="button"
        tabindex="0"
        class="absolute top-3.5 right-3 text-primary/70 hover:text-primary transition-colors cursor-pointer"
        onclick={(e) => { e.stopPropagation(); goto('/tracker'); }}
        onkeydown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); goto('/tracker'); } }}
        title="View in Tracker"
        aria-label="View in Tracker"
      >
        <span class="text-xs">📌</span>
      </span>
    {/if}

    <!-- Status Pills Timeline -->
    <div 
      class="mt-3 flex items-center gap-1 flex-wrap"
      role="presentation"
      onclick={(e) => e.stopPropagation()}
      onkeydown={(e) => e.stopPropagation()}
    >
      {#each STATUS_PIPELINE as s}
        <button
          class="text-[10px] px-2 py-0.5 rounded-full font-medium transition-all cursor-pointer border
            {entry.application_status === s.value ? s.activeClass : 'border-border/50 text-muted-foreground hover:bg-accent/80 hover:border-border opacity-70'}
          "
          onclick={() => onStatusChange(entry.id, s.value)}
        >
          {s.label}
        </button>
      {/each}
    </div>

    <!-- Linear Match Progress Bar (replaces ScoreRing bloat) -->
    {#if entry.match_score !== null}
      <div class="absolute bottom-0 left-0 right-0 h-0.5 bg-muted/50">
        <div class="h-0.5 transition-all duration-500 ease-out {getScoreBarColor(entry.match_score)}" style="width:{entry.match_score}%"></div>
      </div>
    {/if}
  </div>
</div>
