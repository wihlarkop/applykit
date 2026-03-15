<script lang="ts">
  import { activeProfile } from '$lib/activeProfile.svelte';
  import { getProfile } from '$lib/api';
  import { profiles } from '$lib/profiles.svelte';
  import ProfileModal from './ProfileModal.svelte';

  let dropdownOpen = $state(false);
  let modalMode = $state<'create' | 'edit' | null>(null);

  const ap = $derived(activeProfile.current);
  const allProfiles = $derived(profiles.all);

  function switchProfile(p: { id: number; label: string; color: string; icon: string; name: string }) {
    activeProfile.set(p);
    dropdownOpen = false;
  }

  function openCreate() {
    dropdownOpen = false;
    modalMode = 'create';
  }

  function openEdit() {
    dropdownOpen = false;
    modalMode = 'edit';
  }

  function closeModal() {
    modalMode = null;
  }
</script>

<div class="relative">
  <!-- Trigger button -->
  <button
    onclick={() => dropdownOpen = !dropdownOpen}
    class="flex items-center gap-2 border rounded-lg px-3 py-2 text-sm font-medium bg-background shadow-sm hover:bg-accent transition-colors min-w-40 justify-between"
  >
    <span class="flex items-center gap-2">
      {#if ap}
        <span class="w-2.5 h-2.5 rounded-full shrink-0" style="background:{ap.color}"></span>
        <span class="text-base leading-none">{ap.icon}</span>
        <span class="truncate">{ap.label}</span>
      {:else}
        <span class="text-muted-foreground">No profile</span>
      {/if}
    </span>
    <span class="text-muted-foreground text-xs ml-1">▼</span>
  </button>

  <!-- Dropdown -->
  {#if dropdownOpen}
    <!-- Click-outside backdrop -->
    <div class="fixed inset-0 z-10" onclick={() => dropdownOpen = false}></div>

    <div class="absolute top-full mt-1 left-0 z-20 bg-card border rounded-lg shadow-lg py-1 min-w-[200px]">
      {#each allProfiles as p}
        <button
          onclick={() => p.id === ap?.id ? openEdit() : switchProfile(p)}
          class="w-full flex items-center gap-2.5 px-3 py-2 text-sm hover:bg-accent transition-colors text-left"
        >
          <span class="w-2 h-2 rounded-full shrink-0" style="background:{p.color}"></span>
          <span>{p.icon}</span>
          <span class="truncate flex-1">{p.label}</span>
          {#if !p.has_content}
            <span class="w-1.5 h-1.5 rounded-full bg-yellow-400 shrink-0" title="Profile is empty"></span>
          {/if}
          {#if p.id === ap?.id}
            <span class="text-xs text-muted-foreground">active</span>
          {/if}
        </button>
      {/each}

      <div class="border-t my-1"></div>
      <button
        onclick={openCreate}
        class="w-full flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
      >
        <span class="text-base">＋</span> New Profile
      </button>
    </div>
  {/if}
</div>

<!-- Modals -->
{#if modalMode === 'create'}
  <ProfileModal mode="create" onclose={closeModal} />
{:else if modalMode === 'edit' && ap}
  {#await getProfile(ap.id) then profileData}
    <ProfileModal mode="edit" profile={profileData} onclose={closeModal} />
  {:catch}
    {closeModal()}
  {/await}
{/if}
