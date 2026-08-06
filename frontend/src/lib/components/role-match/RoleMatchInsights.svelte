<script lang="ts">
  import type { RoleMatchViewModel } from '$lib/role-match-presenter';
  import { ArrowRight, Check, CircleAlert } from '@lucide/svelte';

  interface Props {
    view: RoleMatchViewModel;
  }

  let { view }: Props = $props();
</script>

<div class="grid gap-4 lg:grid-cols-2">
  <section class="rounded-2xl border border-border bg-card p-5 shadow-sm" aria-labelledby="role-strengths-title">
    <h3 id="role-strengths-title" class="flex items-center gap-2 text-sm font-semibold text-foreground">
      <span class="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-300">
        <Check class="h-4 w-4" aria-hidden="true" />
      </span>
      What makes you a good fit
    </h3>

    {#if view.sections.strengths.items.length}
      <ul class="mt-4 space-y-3">
        {#each view.sections.strengths.items as item}
          <li class="rounded-xl bg-muted/25 p-3.5">
            <p class="text-sm font-medium text-foreground">{item.title}</p>
            <p class="mt-1 text-xs leading-5 text-muted-foreground">{item.explanation}</p>
            {#if item.evidence_label}
              <p class="mt-2 text-[11px] font-semibold text-emerald-700 dark:text-emerald-300">
                {item.evidence_label}
              </p>
            {/if}
          </li>
        {/each}
      </ul>
    {:else}
      <p class="mt-4 text-sm leading-6 text-muted-foreground">
        Review the detailed requirements to identify where stronger evidence can be added.
      </p>
    {/if}
  </section>

  <section class="rounded-2xl border border-border bg-card p-5 shadow-sm" aria-labelledby="role-gaps-title">
    <h3 id="role-gaps-title" class="flex items-center gap-2 text-sm font-semibold text-foreground">
      <span class="flex h-7 w-7 items-center justify-center rounded-full bg-amber-500/10 text-amber-700 dark:text-amber-300">
        <CircleAlert class="h-4 w-4" aria-hidden="true" />
      </span>
      What may hold you back
    </h3>

    {#if view.sections.gaps.items.length}
      <ul class="mt-4 space-y-3">
        {#each view.sections.gaps.items as item}
          <li class="rounded-xl bg-muted/25 p-3.5">
            <p class="text-sm font-medium text-foreground">{item.title}</p>
            <p class="mt-1 text-xs leading-5 text-muted-foreground">{item.explanation}</p>
            {#if item.evidence_label}
              <p class="mt-2 text-[11px] font-semibold text-amber-700 dark:text-amber-300">
                {item.evidence_label}
              </p>
            {/if}
          </li>
        {/each}
      </ul>
    {:else}
      <p class="mt-4 text-sm leading-6 text-muted-foreground">
        No major evidence gaps were identified in the current analysis.
      </p>
    {/if}
  </section>
</div>

<section class="rounded-2xl border border-primary/20 bg-primary/5 p-5" aria-labelledby="role-next-step-title">
  <h3 id="role-next-step-title" class="text-sm font-semibold text-primary">Your best next step</h3>
  <p class="mt-2 flex gap-3 text-sm leading-6 text-foreground">
    <ArrowRight class="mt-1 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
    <span>{view.sections.nextStep.text}</span>
  </p>
</section>
