import adapter from '@sveltejs/adapter-node';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		adapter: adapter({ out: 'build' }),
		alias: {
			'$lib/api': './src/lib/api-compat.ts',
			'$lib/components/FitAnalysisDisplay.svelte': './src/lib/components/RoleMatchFitAnalysisDisplay.svelte',
			'$lib/components/history/FitAnalysisTab.svelte': './src/lib/components/history/RoleMatchFitAnalysisTab.svelte',
			'$lib/components/history/ClCard.svelte': './src/lib/components/history/RoleMatchClCard.svelte',
			'$lib/components/tracker/ApplicationCard.svelte': './src/lib/components/tracker/RoleMatchApplicationCard.svelte'
		}
	},
	vitePlugin: {
		dynamicCompileOptions: ({ filename }) =>
			filename.includes('node_modules') ? undefined : { runes: true }
	}
};

export default config;
