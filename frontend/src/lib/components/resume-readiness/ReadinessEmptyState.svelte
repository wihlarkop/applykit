<script lang="ts">
  import { FileCheck2 } from '@lucide/svelte';

  interface Props {
    generated: boolean;
  }

  let { generated }: Props = $props();
</script>

<div class="rounded-xl border border-dashed bg-muted/20 p-6 text-center">
  <div class="mx-auto flex h-11 w-11 items-center justify-center rounded-full bg-primary/10 text-primary">
    <FileCheck2 class="h-5 w-5" />
  </div>
  <h3 class="mt-3 font-semibold">
    {generated ? 'Resume has not been analyzed' : 'Generate a saved resume version first'}
  </h3>
  <p class="mx-auto mt-1 max-w-md text-sm leading-relaxed text-muted-foreground">
    {#if generated}
      Resume Readiness checks the exported PDF for machine readability, writing quality, and supported job tailoring.
    {:else}
      The analysis runs against an immutable generated resume record, not the unsaved profile preview.
    {/if}
  </p>
</div>
