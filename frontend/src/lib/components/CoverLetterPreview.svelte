<script lang="ts">
  let { text }: { text: string } = $props();
</script>

<div class="cover-letter-preview font-sans text-[13px] leading-relaxed text-foreground dark:text-zinc-100 print:text-black max-w-[800px] mx-auto p-8 whitespace-pre-wrap bg-transparent">
  {text}
</div>
