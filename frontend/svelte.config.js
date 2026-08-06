import adapter from '@sveltejs/adapter-node';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		adapter: adapter({ out: 'build' }),
		alias: {
			'$lib/api': './src/lib/api-compat.ts',
			'$lib/components/FitAnalysisDisplay.svelte': './src/lib/components/RoleMatchFitAnalysisDisplay.svelte'
		}
	},
	vitePlugin: {
		dynamicCompileOptions: ({ filename }) =>
			filename.includes('node_modules') ? undefined : { runes: true }
	}
};

export default config;
