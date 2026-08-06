<script lang="ts">
  import { groupFindings } from '$lib/resume-readiness-policy';
  import type { ResumeReadinessFinding } from '$lib/resume-readiness-types';
  import ReadinessFindingRow from './ReadinessFindingRow.svelte';

  interface Props {
    findings: ResumeReadinessFinding[];
  }

  let { findings }: Props = $props();
  const grouped = $derived(groupFindings(findings));
</script>

<div class="space-y-5">
  {#if grouped.critical.length > 0}
    <section aria-labelledby="readiness-critical-heading">
      <h4 id="readiness-critical-heading" class="mb-2 font-semibold text-destructive">Critical issues</h4>
      <div class="space-y-2">
        {#each grouped.critical as finding (finding.id ?? finding.rule_id)}
          <ReadinessFindingRow {finding} />
        {/each}
      </div>
    </section>
  {/if}

  {#if grouped.important.length > 0}
    <section aria-labelledby="readiness-important-heading">
      <h4 id="readiness-important-heading" class="mb-2 font-semibold">Important issues</h4>
      <div class="space-y-2">
        {#each grouped.important as finding (finding.id ?? finding.rule_id)}
          <ReadinessFindingRow {finding} />
        {/each}
      </div>
    </section>
  {/if}

  {#if grouped.improvement.length > 0}
    <section aria-labelledby="readiness-improvements-heading">
      <h4 id="readiness-improvements-heading" class="mb-2 font-semibold">Recommended improvements</h4>
      <div class="space-y-2">
        {#each grouped.improvement as finding (finding.id ?? finding.rule_id)}
          <ReadinessFindingRow {finding} />
        {/each}
      </div>
    </section>
  {/if}

  {#if grouped.other.length > 0}
    <section aria-labelledby="readiness-other-heading">
      <h4 id="readiness-other-heading" class="mb-2 font-semibold">Additional checks</h4>
      <div class="space-y-2">
        {#each grouped.other as finding (finding.id ?? finding.rule_id)}
          <ReadinessFindingRow {finding} />
        {/each}
      </div>
    </section>
  {/if}

  {#if grouped.passed.length > 0}
    <details class="rounded-lg border bg-card/40 p-3">
      <summary class="cursor-pointer font-semibold">Passed checks ({grouped.passed.length})</summary>
      <div class="mt-3 space-y-2">
        {#each grouped.passed as finding (finding.id ?? finding.rule_id)}
          <ReadinessFindingRow {finding} />
        {/each}
      </div>
    </details>
  {/if}
</div>
