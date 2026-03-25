<script lang="ts">
  import { goto } from '$app/navigation';
  import { activeProfile } from '$lib/activeProfile.svelte';
  import { getProfile } from '$lib/api';
  import { profiles } from '$lib/profiles.svelte';
  import ProfileModal from './ProfileModal.svelte';

  let dropdownOpen = $state(false);
  let modalMode = $state<'edit' | null>(null);

  const ap = $derived(activeProfile.current);
  const allProfiles = $derived(profiles.all);

  function switchProfile(p: { id: number; label: string; color: string; icon: string; name: string }) {
    activeProfile.set(p);
    dropdownOpen = false;
  }

  function openEdit() {
    dropdownOpen = false;
    modalMode = 'edit';
  }

  function closeModal() {
    modalMode = null;
  }

  function handleManageProfiles() {
    dropdownOpen = false;
    goto('/profiles');
  }
</script>

<div class="relative">
  <!-- Trigger button -->
  <button
    onclick={() => (dropdownOpen = !dropdownOpen)}
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
    <div class="fixed inset-0 z-10" role="presentation" onclick={() => (dropdownOpen = false)} onkeydown={(e) => e.key === 'Escape' && (dropdownOpen = false)}></div>

    <div class="absolute top-full mt-1 left-0 z-20 bg-card border rounded-lg shadow-lg py-1 min-w-50">
      {#each allProfiles as p}
        <button
          onclick={() => (p.id === ap?.id ? openEdit() : switchProfile(p))}
          class="w-full flex items-center gap-2.5 px-3 py-2 text-sm hover:bg-accent transition-colors text-left"
        >
          <span class="w-2 h-2 rounded-full shrink-0" style="background:{p.color}"></span>
          <span>{p.icon}</span>
          <span class="truncate flex-1">{p.label}</span>
          {#if !p.has_content}
            <span class="inline-flex items-center gap-1 text-[10px] font-medium text-yellow-600 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/30 px-1.5 py-0.5 rounded shrink-0">
              Empty
            </span>
          {/if}
          {#if p.id === ap?.id}
            <span class="text-xs text-muted-foreground">active</span>
          {/if}
        </button>
      {/each}

      <div class="border-t my-1"></div>
      <button
        onclick={() => { dropdownOpen = false; goto('/profile'); }}
        class="w-full flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
      >
        <span class="text-base">✏️</span> Edit Profile
      </button>
      <button
        onclick={handleManageProfiles}
        class="w-full flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
      >
        <span class="text-base">👥</span> Manage Profiles
      </button>
    </div>
  {/if}
</div>

<!-- Edit modal -->
{#if modalMode === 'edit' && ap}
  {#await getProfile(ap.id) then profileData}
    <ProfileModal mode="edit" profile={profileData} onclose={closeModal} />
  {:catch}
    {closeModal()}
  {/await}
{/if}
