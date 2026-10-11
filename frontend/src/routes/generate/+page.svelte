<script lang="ts">
  import ResumeWorkspace from '$lib/features/resume/ResumeWorkspace.svelte';

  let { data } = $props();
</script>

<ResumeWorkspace {data} />
