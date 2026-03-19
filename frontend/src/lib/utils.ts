import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type WithoutChild<T> = T extends { child?: any } ? Omit<T, "child"> : T;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type WithoutChildren<T> = T extends { children?: any } ? Omit<T, "children"> : T;
export type WithoutChildrenOrChild<T> = WithoutChildren<WithoutChild<T>>;
export type WithElementRef<T, U extends HTMLElement = HTMLElement> = T & { ref?: U | null };

/**
 * Build a query string from a filters object, omitting null/undefined values.
 * Returns an empty string when there are no params.
 */
export function buildQs(filters: object): string {
	const params = new URLSearchParams();
	for (const [k, v] of Object.entries(filters)) {
		if (v !== undefined && v !== null) params.set(k, String(v));
	}
	const qs = params.toString();
	return qs ? `?${qs}` : '';
}

/**
 * Safely extract a human-readable message from an unknown catch value.
 * Replaces the `catch (e: any)` pattern throughout the codebase.
 */
export function errorMessage(e: unknown, fallback = 'Something went wrong'): string {
	if (e instanceof Error) return e.message;
	if (typeof e === 'string') return e;
	return fallback;
}
