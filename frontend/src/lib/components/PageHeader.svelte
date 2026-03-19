<script lang="ts">
  import type { Snippet } from 'svelte';

  const {
    title,
    subtitle,
    actions,
    class: className = '',
  }: {
    title: string;
    subtitle?: string;
    /** Slot for header action buttons (Download, Generate, etc.) */
    actions?: Snippet;
    class?: string;
  } = $props();
</script>

<!--
  PageHeader — sticky page header used across route pages.
  Renders inside the sticky bar at the top of each page's content area.

  Usage:
    <PageHeader title="Generate CV" subtitle="Create an ATS-optimized CV.">
      {#snippet actions()}
        <Button onclick={handleGenerate}>Generate</Button>
      {/snippet}
    </PageHeader>
-->
<div
  class="sticky top-0 z-50 bg-background/80 backdrop-blur-md border-b border-border -mx-4 px-4 py-4 mb-8 {className}"
>
  <div class="flex items-start sm:items-center justify-between flex-col sm:flex-row gap-4 max-w-4xl mx-auto">
    <div>
      <h1 class="text-2xl font-bold">{title}</h1>
      {#if subtitle}
        <p class="text-xs text-muted-foreground mt-0.5">{subtitle}</p>
      {/if}
    </div>

    {#if actions}
      <div class="flex items-center gap-3 self-end sm:self-auto">
        {@render actions()}
      </div>
    {/if}
  </div>
</div>
