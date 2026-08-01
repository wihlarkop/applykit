<script lang="ts">
  import { tick } from 'svelte';
  import { Check, ChevronDown, Search, X } from '@lucide/svelte';

  import {
    filterCatalogModels,
    type CatalogModelFilters,
    type CatalogModelOption,
    type ModelStatus,
  } from '$lib/llm-catalog';

  let {
    models,
    value = $bindable(''),
    unavailableValue = '',
  }: {
    models: CatalogModelOption[];
    value: string;
    unavailableValue?: string;
  } = $props();

  let open = $state(false);
  let query = $state('');
  let statuses = $state<ModelStatus[]>([]);
  let freeTier = $state(false);
  let reasoning = $state(false);
  let structuredOutput = $state(false);
  let activeIndex = $state(0);
  let searchInput: HTMLInputElement | undefined = $state();

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

  async function toggleOpen() {
    open = !open;
    if (open) {
      await tick();
      searchInput?.focus();
    }
  }

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
    open = false;
    query = '';
  }

  function handleSearchKeydown(event: KeyboardEvent) {
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      activeIndex = Math.min(activeIndex + 1, filteredModels.length - 1);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      activeIndex = Math.max(activeIndex - 1, 0);
    } else if (event.key === 'Enter') {
      event.preventDefault();
      const model = filteredModels[activeIndex];
      if (model) chooseModel(model);
    } else if (event.key === 'Escape') {
      event.preventDefault();
      open = false;
    }
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

<div class="relative">
  <button
    type="button"
    class="flex w-full items-center justify-between gap-3 rounded-md border border-border bg-background px-3 py-2 text-left text-sm hover:bg-accent/40"
    aria-haspopup="listbox"
    aria-expanded={open}
    onclick={toggleOpen}
  >
    <span class="min-w-0 flex-1">
      <span class="block truncate font-medium">
        {selectedModel?.label ?? (unavailableSelected ? unavailableValue : 'Select a model')}
      </span>
      {#if selectedModel}
        <span class="block truncate font-mono text-[11px] text-muted-foreground">{selectedModel.value}</span>
      {:else if unavailableSelected}
        <span class="block truncate text-[11px] text-yellow-700 dark:text-yellow-300">Unavailable in this release</span>
      {/if}
    </span>
    <ChevronDown class="h-4 w-4 shrink-0 text-muted-foreground transition-transform {open ? 'rotate-180' : ''}" />
  </button>

  {#if open}
    <div class="absolute z-50 mt-2 w-full overflow-hidden rounded-lg border border-border bg-popover shadow-xl">
      <div class="space-y-3 border-b border-border p-3">
        <div class="relative">
          <Search class="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            bind:this={searchInput}
            bind:value={query}
            onkeydown={handleSearchKeydown}
            placeholder="Search by name or model ID…"
            aria-label="Search models"
            class="w-full rounded-md border border-border bg-background py-2 pl-8 pr-3 text-sm outline-none focus:ring-2 focus:ring-primary/30"
          />
        </div>

        <div class="flex flex-wrap gap-1.5" aria-label="Model filters">
          {#each ['stable', 'preview', 'experimental'] as status}
            <button
              type="button"
              aria-pressed={statuses.includes(status as ModelStatus)}
              onclick={() => toggleStatus(status as ModelStatus)}
              class="rounded-full border px-2 py-1 text-[11px] font-medium capitalize transition-colors {statuses.includes(status as ModelStatus)
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border hover:bg-accent'}"
            >{status}</button>
          {/each}
          <button
            type="button"
            aria-pressed={freeTier}
            onclick={() => (freeTier = !freeTier)}
            class="rounded-full border px-2 py-1 text-[11px] font-medium transition-colors {freeTier ? 'border-primary bg-primary text-primary-foreground' : 'border-border hover:bg-accent'}"
          >Free tier</button>
          <button
            type="button"
            aria-pressed={reasoning}
            onclick={() => (reasoning = !reasoning)}
            class="rounded-full border px-2 py-1 text-[11px] font-medium transition-colors {reasoning ? 'border-primary bg-primary text-primary-foreground' : 'border-border hover:bg-accent'}"
          >Reasoning</button>
          <button
            type="button"
            aria-pressed={structuredOutput}
            onclick={() => (structuredOutput = !structuredOutput)}
            class="rounded-full border px-2 py-1 text-[11px] font-medium transition-colors {structuredOutput ? 'border-primary bg-primary text-primary-foreground' : 'border-border hover:bg-accent'}"
          >Structured output</button>
          {#if query || activeFilterCount > 0}
            <button
              type="button"
              onclick={clearFilters}
              class="inline-flex items-center gap-1 rounded-full px-2 py-1 text-[11px] text-muted-foreground hover:bg-accent hover:text-foreground"
            >
              <X class="h-3 w-3" /> Clear
            </button>
          {/if}
        </div>
      </div>

      <div class="max-h-72 overflow-y-auto p-1" role="listbox" aria-label="Available models">
        {#if filteredModels.length === 0}
          <div class="px-3 py-8 text-center text-sm text-muted-foreground">
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
              class="flex w-full items-start gap-2 rounded-md px-3 py-2 text-left transition-colors {index === activeIndex ? 'bg-accent' : 'hover:bg-accent/70'}"
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
        {filteredModels.length} of {models.length} models
      </div>
    </div>
  {/if}
</div>
