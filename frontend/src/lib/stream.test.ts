import { describe, expect, test } from 'bun:test';

import { consumeStream, consumeStructuredStream } from './stream';


function sseResponse(payload: string): Response {
    const body = new ReadableStream<Uint8Array>({
        start(controller) {
            controller.enqueue(new TextEncoder().encode(payload));
            controller.close();
        },
    });
    return new Response(body);
}


describe('SSE error envelopes', () => {
    test('consumeStream extracts the public message from an error envelope', async () => {
        let message: string | undefined;
        const response = sseResponse(
            'event: error\n' +
            'data: {"error":{"code":"LLM_CALL_FAILED","message":"Provider request failed.","details":{}}}\n\n'
        );

        await consumeStream(response, {
            onError(value) {
                message = value;
            },
        });

        expect(message).toBe('Provider request failed.');
    });

    test('consumeStructuredStream routes error events through onError', async () => {
        let message: string | undefined;
        const events: string[] = [];
        const response = sseResponse(
            'event: error\n' +
            'data: {"error":{"code":"INTERNAL_SERVER_ERROR","message":"An unexpected error occurred","details":{}}}\n\n'
        );

        await consumeStructuredStream(response, {
            onEvent(event) {
                events.push(event);
            },
            onError(value) {
                message = value;
            },
        });

        expect(message).toBe('An unexpected error occurred');
        expect(events).toEqual([]);
    });

    test('consumeStructuredStream keeps rate limit envelopes as typed events', async () => {
        let received: unknown;
        const response = sseResponse(
            'event: rate_limit\n' +
            'data: {"error":{"code":"RATE_LIMIT_EXCEEDED","message":"Rate limit exceeded.","details":{"retry_after":3}}}\n\n'
        );

        await consumeStructuredStream(response, {
            onEvent(event, data) {
                if (event === 'rate_limit') received = data;
            },
        });

        expect(received).toEqual({
            error: {
                code: 'RATE_LIMIT_EXCEEDED',
                message: 'Rate limit exceeded.',
                details: { retry_after: 3 },
            },
        });
    });
});
