import type { ApplicationStatus } from '$lib/types';

export const SCORE_THRESHOLDS = {
	HIGH: 70,
	MEDIUM: 40,
} as const;

export const SCORE_LABELS = {
	HIGH: 'Strong Match',
	MEDIUM: 'Partial Match',
	LOW: 'Weak Match',
} as const;

export const MATCH_COLORS = {
	HIGH: {
		text: 'text-green-600',
		bg: 'bg-green-500/20',
		border: 'border-green-500/40',
		ring: 'ring-green-500',
		hex: '#22c55e',
	},
	MEDIUM: {
		text: 'text-yellow-600',
		bg: 'bg-amber-500/20',
		border: 'border-amber-500/40',
		ring: 'ring-amber-500',
		hex: '#f59e0b',
	},
	LOW: {
		text: 'text-red-600',
		bg: 'bg-red-500/20',
		border: 'border-red-500/40',
		ring: 'ring-red-500',
		hex: '#ef4444',
	},
} as const;

export const STATUS_OPTIONS: { value: ApplicationStatus | null; label: string }[] = [
	{ value: null, label: '—' },
	{ value: 'applied', label: 'Applied' },
	{ value: 'interviewing', label: 'Interviewing' },
	{ value: 'offer', label: 'Offer' },
	{ value: 'rejected', label: 'Rejected' },
];

export const STATUS_CONFIG: Record<ApplicationStatus, { label: string; color: string; activeClass: string }> = {
	applied: {
		label: 'Applied',
		color: 'text-blue-600',
		activeClass: 'bg-blue-500/20 text-blue-600 border border-blue-500/40',
	},
	interviewing: {
		label: 'Interviewing',
		color: 'text-amber-500',
		activeClass: 'bg-amber-500/20 text-amber-600 border border-amber-500/40',
	},
	offer: {
		label: 'Offer',
		color: 'text-green-500',
		activeClass: 'bg-green-500/20 text-green-600 border border-green-500/40',
	},
	rejected: {
		label: 'Rejected',
		color: 'text-red-500',
		activeClass: 'bg-red-500/20 text-red-600 border border-red-500/40',
	},
};

export const DATE_RANGES = [
	{ value: 'all', label: 'All time' },
	{ value: 'week', label: 'This week' },
	{ value: 'month', label: 'This month' },
	{ value: 'quarter', label: 'Last 3 months' },
] as const;

export const MATCH_FILTERS = [
	{ value: 'all', label: 'All matches' },
	{ value: 'high', label: 'High (≥70%)' },
	{ value: 'medium', label: 'Medium (40–69%)' },
	{ value: 'low', label: 'Low (<40%)' },
] as const;

export const SORT_OPTIONS = [
	{ value: 'newest', label: 'Newest first' },
	{ value: 'oldest', label: 'Oldest first' },
	{ value: 'best_match', label: 'Best match' },
	{ value: 'company', label: 'Company A–Z' },
] as const;
