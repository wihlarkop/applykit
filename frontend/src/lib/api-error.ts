type UnknownRecord = Record<string, unknown>;


function asRecord(value: unknown): UnknownRecord | undefined {
    return typeof value === 'object' && value !== null && !Array.isArray(value)
        ? value as UnknownRecord
        : undefined;
}


function asNonEmptyString(value: unknown): string | undefined {
    return typeof value === 'string' && value.trim() ? value : undefined;
}


export class ApiError extends Error {
    readonly code: string | undefined;
    readonly details: unknown;
    readonly status: number | undefined;

    constructor(
        message: string,
        code?: string,
        details?: unknown,
        status?: number
    ) {
        super(message);
        this.name = 'ApiError';
        this.code = code;
        this.details = details;
        this.status = status;
    }
}


export function parseApiError(
    payload: unknown,
    fallbackMessage: string,
    status?: number
): ApiError {
    const root = asRecord(payload);
    const nested = asRecord(root?.error);

    const message =
        asNonEmptyString(nested?.message)
        ?? asNonEmptyString(root?.message)
        ?? asNonEmptyString(root?.detail)
        ?? fallbackMessage;

    const code =
        asNonEmptyString(nested?.code)
        ?? asNonEmptyString(root?.error_code)
        ?? asNonEmptyString(root?.code);

    const details = nested && 'details' in nested
        ? nested.details
        : root?.details;

    return new ApiError(message, code, details, status);
}
