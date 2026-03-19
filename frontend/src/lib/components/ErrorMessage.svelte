<script lang="ts">
  type Variant = 'error' | 'warning' | 'success' | 'info';

  const {
    message,
    variant = 'error',
    class: className = '',
  }: {
    message: string;
    variant?: Variant;
    class?: string;
  } = $props();

  const styles: Record<Variant, string> = {
    error:   'bg-destructive/10 text-destructive border-destructive/20',
    warning: 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/20',
    success: 'bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20',
    info:    'bg-primary/10 text-primary border-primary/20',
  };
</script>

{#if message}
  <div
    class="p-3 rounded-md text-sm font-medium border animate-in fade-in zoom-in-95 duration-200 {styles[variant]} {className}"
    role={variant === 'error' ? 'alert' : 'status'}
  >
    {message}
  </div>
{/if}
