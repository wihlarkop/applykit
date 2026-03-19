<script lang="ts">
  import type { Component } from 'svelte';

  const {
    icon: IconComponent,
    iconClass = 'text-primary',
    iconBg = 'bg-primary/10',
    title,
    description,
    children,
  }: {
    icon?: Component<{ class?: string }>;
    iconClass?: string;
    iconBg?: string;
    title: string;
    description?: string;
    /** Optional action slot (e.g. a Button) */
    children?: import('svelte').Snippet;
  } = $props();
</script>

<!--
  EmptyState — centered content placeholder used inside a Card or standalone.
  Usage:
    <EmptyState icon={FileText} title="No results" description="Try adjusting your filters.">
      <Button href="/new">Create one</Button>
    </EmptyState>
-->
<div class="flex flex-col items-center justify-center py-16 text-center">
  {#if IconComponent}
    <div class="w-16 h-16 {iconBg} {iconClass} rounded-full flex items-center justify-center mb-4">
      <IconComponent class="w-8 h-8" />
    </div>
  {/if}

  <h3 class="text-xl font-bold mb-2">{title}</h3>

  {#if description}
    <p class="text-muted-foreground max-w-sm mx-auto mb-5">{description}</p>
  {/if}

  {#if children}
    {@render children()}
  {/if}
</div>
