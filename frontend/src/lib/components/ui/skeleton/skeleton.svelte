<script lang="ts">
  import { cn } from "$lib/utils";

  let { class: className, ...props } = $props<{ class?: string } & any>();
</script>

<div
  class={cn("animate-pulse rounded-md bg-primary/10", className)}
  {...props}
></div>
