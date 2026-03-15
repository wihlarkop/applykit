<script lang="ts">
  import { toastState } from '$lib/toast.svelte';
  import { CircleAlert, CircleCheck, Info, X } from '@lucide/svelte';
  import { fade, fly } from 'svelte/transition';
  import { Button } from './ui/button';

  let { toast } = $props<{ toast: import('$lib/toast.svelte').Toast }>();

  const icons = {
    success: CircleCheck,
    error: CircleAlert,
    info: Info
  };

  const colors = {
    success: 'border-green-500/50 bg-green-50 text-green-800 dark:bg-green-950/20 dark:text-green-400',
    error: 'border-destructive/50 bg-destructive/5 text-destructive dark:bg-destructive/10',
    info: 'border-primary/50 bg-primary/5 text-primary'
  };

  const Icon = $derived(icons[toast.type as keyof typeof icons] || Info);
  const colorClass = $derived(colors[toast.type as keyof typeof colors] || colors.info);
</script>

<div
  in:fly={{ y: 20, duration: 400 }}
  out:fade={{ duration: 200 }}
  class="flex items-center gap-3 p-4 rounded-xl border-2 shadow-lg backdrop-blur-md min-w-75 max-w-md {colorClass}"
>
  <div class="shrink-0">
    <Icon class="w-5 h-5" />
  </div>
  <p class="text-sm font-medium flex-1">{toast.message}</p>
  <Button
    variant="ghost"
    size="icon"
    class="h-6 w-6 rounded-full hover:bg-black/5 dark:hover:bg-white/5"
    onclick={() => toastState.remove(toast.id)}
  >
    <X class="w-4 h-4" />
  </Button>
</div>
