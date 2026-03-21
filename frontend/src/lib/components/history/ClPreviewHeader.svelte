<script lang="ts">
  import { Button } from '$lib/components/ui/button';
  import ScoreRing from '$lib/components/ScoreRing.svelte';
  import { Download, Sparkles } from '@lucide/svelte';
  import { formatDate } from '$lib/utils';
  import { goto } from '$app/navigation';
  import type { GeneratedCoverLetterEntry } from '$lib/types';
  import { STATUS_CONFIG } from '$lib/constants';

  interface Props {
    selectedCl: GeneratedCoverLetterEntry;
    onClose: () => void;
    onDownload: () => void;
    downloading: boolean;
    onCopy: () => void;
    onDelete: () => void;
  }

  let { selectedCl, onClose, onDownload, downloading, onCopy, onDelete }: Props = $props();

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
</script>

<div class="relative shrink-0 border-b border-border/50 bg-linear-to-br from-card to-background/50">
  <button
    onclick={onClose}
    class="hidden md:flex absolute top-3 right-3 w-7 h-7 items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted/80 transition-colors text-sm"
    title="Close preview"
    aria-label="Close preview"
  >✕</button>
  <div class="md:hidden px-3 pt-2">
    <Button variant="ghost" size="sm" onclick={onClose}>← Back</Button>
  </div>
  
  <div class="flex flex-col sm:flex-row sm:items-start gap-4 p-5 sm:p-6 pb-4">
    {#if selectedCl.match_score !== null}
      <div class="shrink-0">
        <ScoreRing score={selectedCl.match_score} size={64} strokeWidth={8} />
      </div>
    {/if}

    <div class="flex-1 min-w-0">
      <div class="text-xl font-black tracking-tighter text-foreground truncate">{displayCompany(selectedCl)}</div>
      {#if displayRole(selectedCl)}
        <div class="text-[13px] font-semibold text-muted-foreground/90 mt-0.5 truncate">{displayRole(selectedCl)}</div>
      {/if}
      <div class="text-[11px] font-medium text-muted-foreground/60 mt-1 uppercase tracking-widest">{formatDate(selectedCl.created_at)}</div>
      
      <div class="mt-3 flex items-center gap-2 flex-wrap">
        {#if selectedCl.application_status}
          {@const sp = STATUS_PIPELINE.find(p => p.value === selectedCl.application_status)}
          {#if sp}
            <span class="text-[10px] px-2 py-0.5 rounded-full font-black uppercase tracking-widest {sp.activeClass}">
              ● {sp.label}
            </span>
          {/if}
        {/if}
        {#if selectedCl.application_id}
          <span
            role="link"
            tabindex="0"
            class="text-[10px] text-primary hover:underline cursor-pointer flex items-center gap-1 font-bold uppercase tracking-wider"
            onclick={() => goto('/tracker')}
            onkeydown={(e) => { if (e.key === 'Enter') goto('/tracker'); }}
          >📌 View in Tracker <span class="text-xs">→</span></span>
        {/if}
      </div>
    </div>

    <!-- Actions -->
    <div class="flex gap-2 shrink-0 sm:mt-0 mt-4 self-start">
      <Button variant="outline" size="sm" class="h-8 text-xs font-bold" onclick={onDownload} disabled={downloading}>
        <Download class="w-3.5 h-3.5 mr-1.5" />
        {downloading ? 'PDF...' : 'PDF'}
      </Button>
      <Button variant="outline" size="sm" class="h-8 text-xs font-bold" onclick={onCopy}>Copy</Button>
      <Button variant="destructive" size="sm" class="h-8 text-xs font-bold" onclick={onDelete}>Delete</Button>
    </div>
  </div>
</div>
