<script lang="ts">
  let { text }: { text: string } = $props();
</script>

<div class="cover-letter-preview mx-auto max-w-[44rem] whitespace-pre-wrap bg-transparent p-8 font-sans text-[14px] leading-6 text-foreground dark:text-zinc-100 sm:p-9 lg:p-10 print:p-0 print:text-black">
  {text}
</div>
