import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

import { MATCH_COLORS, SCORE_LABELS, SCORE_THRESHOLDS } from "./constants";

export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type WithoutChild<T> = T extends { child?: any } ? Omit<T, "child"> : T;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type WithoutChildren<T> = T extends { children?: any } ? Omit<T, "children"> : T;
export type WithoutChildrenOrChild<T> = WithoutChildren<WithoutChild<T>>;
export type WithElementRef<T, U extends HTMLElement = HTMLElement> = T & { ref?: U | null };

export type ScoreLevel = keyof typeof SCORE_LABELS;

export function getScoreLevel(score: number): ScoreLevel {
	if (score >= SCORE_THRESHOLDS.HIGH) return 'HIGH';
	if (score >= SCORE_THRESHOLDS.MEDIUM) return 'MEDIUM';
	return 'LOW';
}

export interface ScoreInfo {
	level: ScoreLevel;
	color: (typeof MATCH_COLORS)[ScoreLevel];
	label: string;
	summary: string;
	fitTitle: string;
	barColor: string;
}

export function getScoreInfo(score: number): ScoreInfo {
	const level = getScoreLevel(score);
	return {
		level,
		color: MATCH_COLORS[level],
		label: SCORE_LABELS[level],
		summary:
			level === 'HIGH'
				? 'Your profile covers most key requirements.'
				: level === 'MEDIUM'
					? 'Your profile partially matches this role.'
					: 'Your profile has gaps for this role.',
		fitTitle:
			level === 'HIGH'
				? 'Good fit for this role'
				: level === 'MEDIUM'
					? 'Partial fit for this role'
					: 'Weak fit for this role',
		barColor: level === 'HIGH' ? 'bg-green-500' : level === 'MEDIUM' ? 'bg-yellow-500' : 'bg-red-500',
	};
}

export function getScoreColor(score: number) {
	return getScoreInfo(score).color;
}

export function getScoreLabel(score: number): string {
	return getScoreInfo(score).label;
}

export function getScoreSummary(score: number): string {
	return getScoreInfo(score).summary;
}

export function getFitTitle(score: number): string {
	return getScoreInfo(score).fitTitle;
}

export function getScoreBarColor(score: number): string {
	return getScoreInfo(score).barColor;
}

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

export function formatDate(iso: string): string {
	return new Date(iso).toLocaleString(undefined, {
		dateStyle: 'medium',
		timeStyle: 'short',
	});
}

export function formatDateShort(iso: string): string {
	return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function formatDateRelative(iso: string): string {
	const date = new Date(iso);
	const now = new Date();
	const diffMs = now.getTime() - date.getTime();
	const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

	if (diffDays === 0) return 'Today';
	if (diffDays === 1) return 'Yesterday';
	if (diffDays < 7) return `${diffDays} days ago`;
	if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
	return formatDateShort(iso);
}
