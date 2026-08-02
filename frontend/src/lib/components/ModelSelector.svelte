<script lang="ts">
  import { Check, Search, X } from '@lucide/svelte';

  import {
    filterCatalogModels,
    type CatalogModelFilters,
    type CatalogModelOption,
    type ModelStatus,
  } from '$lib/llm-catalog';
  import { nextModelIndex, selectedModelForKey } from '$lib/model-selector';

  let {
    models,
    value = $bindable(''),
    unavailableValue = '',
  }: {
    models: CatalogModelOption[];
    value: string;
    unavailableValue?: string;
  } = $props();

  let query = $state('');
  let statuses = $state<ModelStatus[]>([]);
  let freeTier = $state(false);
  let reasoning = $state(false);
  let structuredOutput = $state(false);
  let activeIndex = $state(0);

  const filters = $derived<CatalogModelFilters>({
    statuses: new Set(statuses),
    freeTier,
    reasoning,
    structuredOutput,
  });
  const filteredModels = $derived(filterCatalogModels(models, query, filters));
  const selectedModel = $derived(models.find((model) => model.value === value));
  const unavailableSelected = $derived(Boolean(value && unavailableValue === value && !selectedModel));
  const activeFilterCount = $derived(
    statuses.length + Number(freeTier) + Number(reasoning) + Number(structuredOutput),
  );

  $effect(() => {
    query;
    statuses;
    freeTier;
    reasoning;
    structuredOutput;
    activeIndex = 0;
  });

  function toggleStatus(status: ModelStatus) {
    statuses = statuses.includes(status)
      ? statuses.filter((item) => item !== status)
      : [...statuses, status];
  }

  function clearFilters() {
    query = '';
    statuses = [];
    freeTier = false;
    reasoning = false;
    structuredOutput = false;
  }

  function chooseModel(model: CatalogModelOption) {
    value = model.value;
  }

  function handleSearchKeydown(event: KeyboardEvent) {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      activeIndex = nextModelIndex(activeIndex, filteredModels.length, event.key);
      return;
    }

    const selectedValue = selectedModelForKey(
      event.key,
      activeIndex,
      filteredModels.map((model) => model.value),
    );
    if (!selectedValue) return;

    event.preventDefault();
    const model = filteredModels.find((item) => item.value === selectedValue);
    if (model) chooseModel(model);
  }

  function statusBadgeClass(status: ModelStatus): string {
    if (status === 'preview') {
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-300';
    }
    if (status === 'experimental') {
      return 'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300';
    }
    return 'bg-muted text-muted-foreground';
  }
</script>

<div class="overflow-hidden rounded-xl border border-border bg-background">
  <div class="border-b border-border bg-muted/35 p-3">
    <div class="flex items-start justify-between gap-3 rounded-lg bg-background px-3 py-2.5 shadow-sm ring-1 ring-border/70">
      <span class="min-w-0 flex-1">
        <span class="block text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Selected model</span>
        <span class="mt-1 block truncate text-sm font-medium">
          {selectedModel?.label ?? (unavailableSelected ? unavailableValue : 'Choose a model below')}
        </span>
        {#if selectedModel}
          <span class="block truncate font-mono text-[11px] text-muted-foreground">{selectedModel.value}</span>
        {:else if unavailableSelected}
          <span class="block text-[11px] text-yellow-700 dark:text-yellow-300">Unavailable in this release</span>
        {/if}
      </span>
      {#if selectedModel}
        <span class="mt-1 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary" aria-hidden="true">
          <Check class="h-4 w-4" />
        </span>
      {/if}
    </div>

    <div class="relative mt-3">
      <Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <input
        bind:value={query}
        onkeydown={handleSearchKeydown}
        placeholder="Search by name or model ID..."
        aria-label="Search models"
        aria-controls="available-models"
        class="min-h-11 w-full rounded-lg border border-border bg-background py-2 pl-9 pr-3 text-sm outline-none transition-shadow focus-visible:ring-2 focus-visible:ring-primary/40"
      />
    </div>

    <div class="mt-3 flex flex-wrap gap-1.5" aria-label="Model filters">
      {#each ['stable', 'preview', 'experimental'] as status}
        <button
          type="button"
          aria-pressed={statuses.includes(status as ModelStatus)}
          onclick={() => toggleStatus(status as ModelStatus)}
          class="min-h-8 rounded-full border px-2.5 py-1 text-[11px] font-medium capitalize transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 {statuses.includes(status as ModelStatus)
            ? 'border-primary bg-primary text-primary-foreground'
            : 'border-border bg-background hover:bg-accent'}"
        >{status}</button>
      {/each}
      <button
        type="button"
        aria-pressed={freeTier}
        onclick={() => (freeTier = !freeTier)}
        class="min-h-8 rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 {freeTier ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-background hover:bg-accent'}"
      >Free tier</button>
      <button
        type="button"
        aria-pressed={reasoning}
        onclick={() => (reasoning = !reasoning)}
        class="min-h-8 rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 {reasoning ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-background hover:bg-accent'}"
      >Reasoning</button>
      <button
        type="button"
        aria-pressed={structuredOutput}
        onclick={() => (structuredOutput = !structuredOutput)}
        class="min-h-8 rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 {structuredOutput ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-background hover:bg-accent'}"
      >Structured output</button>
      {#if query || activeFilterCount > 0}
        <button
          type="button"
          onclick={clearFilters}
          class="inline-flex min-h-8 items-center gap-1 rounded-full px-2.5 py-1 text-[11px] text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
        >
          <X class="h-3 w-3" /> Clear
        </button>
      {/if}
    </div>
  </div>

  <div id="available-models" class="max-h-[min(42vh,26rem)] overflow-y-auto p-1.5" role="listbox" aria-label="Available models">
    {#if filteredModels.length === 0}
      <div class="px-3 py-10 text-center text-sm text-muted-foreground">
        No models match the current search and filters.
      </div>
    {:else}
      {#each filteredModels as model, index}
        <button
          type="button"
          role="option"
          aria-selected={model.value === value}
          onclick={() => chooseModel(model)}
          onmouseenter={() => (activeIndex = index)}
          class="flex min-h-12 w-full items-start gap-2 rounded-lg px-3 py-2.5 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/40 {model.value === value
            ? 'bg-primary/10 ring-1 ring-inset ring-primary/25'
            : index === activeIndex
              ? 'bg-accent'
              : 'hover:bg-accent/70'}"
        >
          <span class="min-w-0 flex-1">
            <span class="flex flex-wrap items-center gap-1.5">
              <span class="text-sm font-medium">{model.label}</span>
              {#if model.status !== 'stable'}
                <span class="rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase {statusBadgeClass(model.status)}">{model.status}</span>
              {/if}
              {#if model.free_tier}
                <span class="rounded bg-green-100 px-1.5 py-0.5 text-[9px] font-semibold uppercase text-green-800 dark:bg-green-950 dark:text-green-300">Free tier</span>
              {/if}
              {#if model.traits.includes('reasoning')}
                <span class="rounded bg-muted px-1.5 py-0.5 text-[9px] uppercase text-muted-foreground">Reasoning</span>
              {/if}
              {#if model.capabilities.includes('structured_output')}
                <span class="rounded bg-muted px-1.5 py-0.5 text-[9px] uppercase text-muted-foreground">Structured</span>
              {/if}
            </span>
            <span class="mt-0.5 block truncate font-mono text-[11px] text-muted-foreground">{model.value}</span>
          </span>
          {#if model.value === value}
            <Check class="mt-0.5 h-4 w-4 shrink-0 text-primary" />
          {/if}
        </button>
      {/each}
    {/if}
  </div>

  <div class="border-t border-border px-3 py-2 text-[11px] text-muted-foreground">
    Showing {filteredModels.length} of {models.length} models
  </div>
</div>
