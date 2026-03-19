export interface StreamOptions {
  onChunk?: (text: string) => void;
  onDone?: () => void;
  onError?: (msg: string) => void;
  transformChunk?: (chunk: string) => string;
}

export async function consumeStream(response: Response, options: StreamOptions = {}): Promise<void> {
  const { onChunk, onDone, onError, transformChunk } = options;
  if (!response.body) return;

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6);

        if (payload === '[DONE]') {
          onDone?.();
          return;
        }

        if (payload.startsWith('[ERROR]')) {
          onError?.(payload.slice(8));
          return;
        }

        const text = transformChunk ? transformChunk(payload) : payload;
        onChunk?.(text);
      }
    }
  } finally {
    reader.releaseLock();
  }
}
