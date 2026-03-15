<script lang="ts">
  import { Settings } from '@lucide/svelte';
  import SettingsModal from '$lib/components/SettingsModal.svelte';

  // Open the modal automatically when the page loads
  let modalOpen = $state(true);
</script>

<div class="max-w-2xl space-y-4">
  <div>
    <h1 class="text-2xl font-bold flex items-center gap-2">
      <Settings class="w-6 h-6 text-primary" />
      Settings
    </h1>
    <p class="text-sm text-muted-foreground mt-1">Configure your AI provider and API key.</p>
  </div>

  <p class="text-sm text-muted-foreground">
    Use the settings panel — or click the ⚙ gear icon in the top navigation bar.
  </p>
</div>

<SettingsModal bind:open={modalOpen} />
