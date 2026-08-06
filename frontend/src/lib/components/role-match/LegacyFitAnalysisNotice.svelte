<script lang="ts">
  import { Info } from '@lucide/svelte';

  interface Props {
    score?: number | null;
  }

  let { score = null }: Props = $props();
</script>

<div class="rounded-xl border border-border bg-muted/20 p-4">
  <div class="flex items-start gap-3">
    <Info class="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
    <div>
      <p class="text-sm font-semibold text-foreground">Legacy AI fit score{score !== null ? ` · ${score}/100` : ''}</p>
      <p class="mt-1 text-xs leading-5 text-muted-foreground">
        This older result was generated before evidence-based scoring was introduced. It remains visible for history but is not recalculated or compared directly with the new metric.
      </p>
    </div>
  </div>
</div>
