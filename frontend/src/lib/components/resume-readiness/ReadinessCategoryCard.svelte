<script lang="ts">
  import { formatReadinessBand } from '$lib/resume-readiness-policy';
  import type { ResumeReadinessCategoryResult } from '$lib/resume-readiness-types';

  interface Props {
    title: string;
    description: string;
    result: ResumeReadinessCategoryResult | null;
  }

  let { title, description, result }: Props = $props();
</script>

<div class="rounded-xl border bg-card p-4">
  <div class="flex items-start justify-between gap-3">
    <div>
      <h4 class="font-semibold">{title}</h4>
      <p class="mt-1 text-xs leading-relaxed text-muted-foreground">{description}</p>
    </div>
    {#if result}
      <div class="text-right">
        <div class="text-2xl font-black tabular-nums">{result.score}</div>
        <div class="text-[11px] text-muted-foreground">{formatReadinessBand(result.band)}</div>
      </div>
    {:else}
      <span class="rounded-full border px-2 py-1 text-xs text-muted-foreground">Not assessed</span>
    {/if}
  </div>
  {#if result?.score_cap != null}
    <p class="mt-3 text-xs text-amber-700 dark:text-amber-300">
      Score capped at {result.score_cap} by a critical rule.
    </p>
  {/if}
</div>
