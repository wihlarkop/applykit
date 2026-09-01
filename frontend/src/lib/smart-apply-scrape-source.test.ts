import { describe, expect, test } from 'bun:test';
import { readFileSync } from 'node:fs';

const page = readFileSync(
  new URL('../routes/smart-apply/+page.svelte', import.meta.url),
  'utf8',
);

describe('smart apply scrape source badge', () => {
  test('surfaces the scrape source next to the job description toggle', () => {
    expect(page).toContain('SCRAPE_SOURCE_INFO');
    expect(page).toContain('jobDescriptionSource');
    expect(page).toContain('<Badge');
    expect(page).toContain('<TooltipContent>{jobDescriptionSource.description}</TooltipContent>');
  });

  test('maps every ScrapeJobResponse source to a label and description', () => {
    for (const source of ['greenhouse_api', 'lever_api', 'ashby_api', 'jina', 'crawl4ai']) {
      expect(page).toContain(`${source}:`);
    }
  });
});
