<script lang="ts">
  import { ZxcvbnFactory } from '@zxcvbn-ts/core';
  import { adjacencyGraphs, dictionary as commonDictionary } from '@zxcvbn-ts/language-common';
  import { dictionary as englishDictionary, translations } from '@zxcvbn-ts/language-en';

  let { password } = $props<{ password: string }>();

  const checker = new ZxcvbnFactory({
    translations,
    graphs: adjacencyGraphs,
    dictionary: {
      ...commonDictionary,
      ...englishDictionary,
    },
  });

  const result = $derived(password ? checker.check(password) : null);
  const score = $derived(result?.score ?? 0);
  const labels = ['Very weak', 'Weak', 'Fair', 'Strong', 'Very strong'];
  const label = $derived(password ? labels[score] : 'Enter at least 12 characters');
</script>

<div class="space-y-2" aria-live="polite">
  <div class="flex gap-1" aria-hidden="true">
    {#each [1, 2, 3, 4] as segment}
      <span class="h-1.5 flex-1 rounded-full {password && score >= segment ? 'bg-primary' : 'bg-muted'}"></span>
    {/each}
  </div>
  <div class="flex items-start justify-between gap-3 text-xs text-muted-foreground">
    <span>{label}</span>
    <span>{password.length}/128</span>
  </div>
  {#if result?.feedback?.warning}
    <p class="text-xs text-muted-foreground">{result.feedback.warning}</p>
  {/if}
</div>
