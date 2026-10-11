<script lang="ts">
  import LegacyDocumentsPage from '../history/+page.svelte';
</script>

<div class="canonical-documents-workspace">
  <div class="mb-6">
    <h1 class="text-2xl font-bold">Documents</h1>
    <p class="mt-1 text-sm text-muted-foreground">
      Review saved resumes, cover letters, and their analysis context.
    </p>
  </div>
  <LegacyDocumentsPage />
</div>

<style>
  .canonical-documents-workspace :global(.space-y-6 > h1:first-child) {
    display: none;
  }
</style>
