import { browser } from '$app/environment';

export type Theme = 'light' | 'dark';

function createTheme() {
	let theme = $state<Theme>('light');

	if (browser) {
		// Initialize from localStorage or system preference
		const stored = localStorage.getItem('theme') as Theme | null;
		if (stored) {
			theme = stored;
		} else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
			theme = 'dark';
		}
	}

	return {
		get current() {
			return theme;
		},
		set current(value: Theme) {
			theme = value;
		},
		toggle() {
			theme = theme === 'light' ? 'dark' : 'light';
		}
	};
}

export const themeState = createTheme();
