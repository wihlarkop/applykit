<script lang="ts">
  import { toastState } from '$lib/toast.svelte';
  import ToastComponent from './Toast.svelte';
</script>

<div class="fixed bottom-6 right-6 z-100 flex flex-col gap-3 pointer-events-none">
  {#each toastState.toasts as toast (toast.id)}
    <div class="pointer-events-auto">
      <ToastComponent {toast} />
    </div>
  {/each}
</div>
