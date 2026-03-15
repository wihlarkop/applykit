<script lang="ts">
  import { cn } from '$lib/utils';

  interface Section {
    id: string;
    label: string;
    icon?: any;
  }

  let { sections = [] }: { sections: Section[] } = $props();
  let activeId = $state(sections[0]?.id || '');

  function scrollToSection(id: string) {
    const element = document.getElementById(id);
    if (element) {
      const offset = 100; // Account for sticky header
      const bodyRect = document.body.getBoundingClientRect().top;
      const elementRect = element.getBoundingClientRect().top;
      const elementPosition = elementRect - bodyRect;
      const offsetPosition = elementPosition - offset;

      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
      });
    }
  }

  $effect(() => {
    const handleScroll = () => {
      const offset = 160; // Better alignment with sticky header
      let currentActiveId = sections[0]?.id || '';

      for (const section of sections) {
        const element = document.getElementById(section.id);
        if (element) {
          const rect = element.getBoundingClientRect();
          if (rect.top <= offset) {
            currentActiveId = section.id;
          }
        }
      }
      activeId = currentActiveId;
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll(); // Check once on mount

    return () => window.removeEventListener('scroll', handleScroll);
  });
</script>

<nav class="hidden lg:block sticky top-24 self-start w-64 space-y-1">
  <div class="px-3 mb-4">
    <h3 class="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Navigation</h3>
  </div>
  {#each sections as section}
    <button
      onclick={() => scrollToSection(section.id)}
      class={cn(
        "w-full flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200 group text-left",
        activeId === section.id
          ? "bg-primary/10 text-primary border-r-2 border-primary"
          : "text-muted-foreground hover:bg-muted hover:text-foreground"
      )}
    >
      {#if section.icon}
        <section.icon class={cn(
          "w-4 h-4",
          activeId === section.id ? "text-primary" : "text-muted-foreground group-hover:text-foreground"
        )} />
      {/if}
      {section.label}
    </button>
  {/each}
</nav>

<style>
  /* Optional: Smooth transition for the border highlight */
  nav button {
    border-right: 0px solid transparent;
  }
</style>
