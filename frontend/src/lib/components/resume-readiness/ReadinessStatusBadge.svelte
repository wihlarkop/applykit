<script lang="ts">
  import { formatReadinessBand } from '$lib/resume-readiness-policy';
  import type {
    ResumeReadinessBand,
    ResumeReadinessStatus,
  } from '$lib/resume-readiness-types';

  interface Props {
    status: ResumeReadinessStatus;
    band?: ResumeReadinessBand | null;
  }

  let { status, band = null }: Props = $props();

  const label = $derived(
    status === 'failed'
      ? 'Analysis failed'
      : status === 'needs_review'
        ? 'Analysis needs review'
        : formatReadinessBand(band),
  );

  const classes = $derived(
    status === 'failed'
      ? 'border-destructive/30 bg-destructive/10 text-destructive'
      : status === 'needs_review'
        ? 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300'
        : band === 'excellent'
          ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
          : band === 'good'
            ? 'border-blue-500/30 bg-blue-500/10 text-blue-700 dark:text-blue-300'
            : 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300',
  );
</script>

<span class="inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold {classes}">
  {label}
</span>
