<script lang="ts">
  import ThemeToggle from '$lib/components/ThemeToggle.svelte';

  let {
    title,
    description,
    children,
  } = $props<{
    title: string;
    description: string;
    children: import('svelte').Snippet;
  }>();
</script>

<div class="relative flex min-h-screen items-center justify-center bg-muted/40 px-4 py-10">
  <div class="absolute right-4 top-4">
    <ThemeToggle />
  </div>

  <div class="w-full max-w-md">
    <div class="mb-6 text-center">
      <a href="/" class="text-xl font-bold tracking-tight text-foreground">ApplyKit</a>
      <h1 class="mt-5 text-2xl font-bold tracking-tight">{title}</h1>
      <p class="mt-2 text-sm leading-6 text-muted-foreground">{description}</p>
    </div>

    <section class="rounded-2xl border border-border bg-card p-6 shadow-sm sm:p-7">
      {@render children()}
    </section>
  </div>
</div>
