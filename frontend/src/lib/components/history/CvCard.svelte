<script lang="ts">
  import { Badge } from '$lib/components/ui/badge';
  import { formatDate } from '$lib/utils';
  import type { GeneratedCVEntry } from '$lib/types';

  interface Props {
    entry: GeneratedCVEntry;
    selected: boolean;
    onSelect: () => void;
  }

  let { entry, selected, onSelect }: Props = $props();
</script>

<button
  onclick={onSelect}
  class="w-full text-left border rounded-xl p-3.5 transition-all outline-none
    {selected ? 'border-primary/50 bg-primary/5 shadow-md ring-1 ring-primary/20 scale-[1.01]' : 'border-border/60 bg-card hover:border-border hover:shadow-sm hover:bg-accent/50'}
  "
>
  <div class="flex items-center justify-between gap-2">
    <span class="text-[13px] font-semibold text-foreground/90">{formatDate(entry.created_at)}</span>
    <div class="flex items-center gap-1.5 shrink-0">
      {#if entry.profile_label}
        <span
          class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium"
          style="background: {entry.profile_color ?? '#6366f1'}20; color: {entry.profile_color ?? '#6366f1'}"
        >
          {entry.profile_icon ?? '💼'} {entry.profile_label}
        </span>
      {/if}
      {#if entry.enhanced}
        <Badge variant="default" class="text-[10px] px-1.5 h-4 font-medium">AI</Badge>
      {:else}
        <Badge variant="secondary" class="text-[10px] px-1.5 h-4 font-medium">Raw</Badge>
      {/if}
    </div>
  </div>
  
  <div class="mt-1.5 text-[11px] font-medium text-muted-foreground/70">
    Generated from Profile Snapshot
  </div>
</button>
