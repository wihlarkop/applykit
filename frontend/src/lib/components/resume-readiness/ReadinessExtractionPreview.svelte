<script lang="ts">
  import type { ResumeReadinessExtraction } from '$lib/resume-readiness-types';

  interface Props {
    extraction: ResumeReadinessExtraction;
  }

  let { extraction }: Props = $props();
</script>

<details class="rounded-xl border bg-card/50 p-4">
  <summary class="cursor-pointer font-semibold">Document extraction preview</summary>
  <div class="mt-3 grid gap-3 text-sm sm:grid-cols-3">
    <div>
      <span class="block text-xs text-muted-foreground">Pages</span>
      <span class="font-semibold">{extraction.page_count}</span>
    </div>
    <div>
      <span class="block text-xs text-muted-foreground">Text layer</span>
      <span class="font-semibold">{extraction.has_text_layer ? 'Detected' : 'Unavailable'}</span>
    </div>
    <div>
      <span class="block text-xs text-muted-foreground">Source coverage</span>
      <span class="font-semibold">
        {extraction.source_coverage == null ? 'Not available' : `${Math.round(extraction.source_coverage * 100)}%`}
      </span>
    </div>
  </div>
  {#if extraction.warnings.length > 0}
    <div class="mt-3 rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-xs">
      <p class="font-semibold">Parser warnings</p>
      <ul class="mt-1 list-disc space-y-1 pl-4 text-muted-foreground">
        {#each extraction.warnings as warning}
          <li>{warning}</li>
        {/each}
      </ul>
    </div>
  {/if}
  <pre class="mt-3 max-h-80 overflow-auto whitespace-pre-wrap rounded-lg bg-muted p-3 text-xs leading-relaxed">{extraction.text_preview}</pre>
</details>
