<script lang="ts">
  import LegacyApplicationsPage from '../tracker/+page.svelte';
</script>

<div class="canonical-applications-workspace">
  <div class="mb-6">
    <h1 class="text-2xl font-bold">Applications</h1>
    <p class="mt-1 text-sm text-muted-foreground">
      Track active applications, status changes, and follow-up work.
    </p>
  </div>
  <LegacyApplicationsPage />
</div>

<style>
  .canonical-applications-workspace :global(.space-y-4 > div:first-child) {
    display: none;
  }
</style>
