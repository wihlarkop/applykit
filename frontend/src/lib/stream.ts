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
        const raw = line.slice(6);

        // Try JSON parsing
        try {
          const parsed = JSON.parse(raw);
          // Handle JSON string value (from ServerSentEvent with data=string)
          if (typeof parsed === 'string') {
            if (parsed === '[DONE]') {
              onDone?.();
              return;
            }
            if (parsed.startsWith('[ERROR]')) {
              onError?.(parsed.slice(8));
              return;
            }
            const text = transformChunk ? transformChunk(parsed) : parsed;
            onChunk?.(text);
          }
          // Handle JSON object (from ServerSentEvent with data={chunk: ...})
          else if (typeof parsed === 'object' && parsed !== null) {
            if (parsed.done) {
              onDone?.();
              return;
            }
            if (parsed.error) {
              onError?.(parsed.error);
              return;
            }
            if (parsed.chunk !== undefined) {
              const text = transformChunk ? transformChunk(parsed.chunk) : parsed.chunk;
              onChunk?.(text);
            }
          }
        } catch {
          // Fallback for plain text format (legacy)
          if (raw === '[DONE]') {
            onDone?.();
            return;
          }
          if (raw.startsWith('[ERROR]')) {
            onError?.(raw.slice(8));
            return;
          }
          const text = transformChunk ? transformChunk(raw) : raw;
          onChunk?.(text);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export interface StructuredStreamOptions {
  onEvent: (event: string, data: unknown) => void;
  onError?: (msg: string) => void;
}

export async function consumeStructuredStream(
  response: Response,
  options: StructuredStreamOptions
): Promise<void> {
  if (!response.body) return;

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let currentEvent = 'message';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() ?? '';

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          const raw = line.slice(6);
          try {
            const parsed = JSON.parse(raw);
            const data = typeof parsed === 'string' ? JSON.parse(parsed) : parsed;
            options.onEvent(currentEvent, data);
          } catch {
            options.onError?.(raw);
          }
          currentEvent = 'message';
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
