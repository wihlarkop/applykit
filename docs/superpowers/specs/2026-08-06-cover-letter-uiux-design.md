# Cover Letter UI/UX Redesign

Date: 2026-08-06
Branch: `release/role-match-v1.3.0`
Scope: `frontend/src/routes/cover-letter/+page.svelte` and focused supporting frontend tests only.

## Goal

Redesign the Cover Letter page into a clearer hybrid workflow that helps users move from job input to fit analysis and generation without competing actions, excessive empty space, or ambiguous input modes.

The redesign must keep the existing ApplyKit visual language, dark mode support, current backend contracts, draft recovery, role-match integration, and generated-cover-letter behavior.

## Design principles

- One dominant action per workflow stage.
- Prefer authoritative imported job metadata over manually inferred context.
- Make URL import the default, while keeping pasted job descriptions easy to access.
- Show relevant controls only when they become useful.
- Use spacing, typography, and grouping for hierarchy rather than decorative gradients or excessive cards.
- Preserve keyboard usability, visible focus states, semantic labels, and readable contrast.
- Keep the experience efficient for repeat users and understandable for first-time users.

## Page structure

### Header

The page header contains:

- Cover Letter title and short task-oriented description.
- A larger three-step progress indicator: Job details, Fit review, Cover letter.
- Completed, active, and upcoming states that remain understandable without relying on color alone.

### Main layout

Desktop uses a balanced two-column layout:

- Left column: workflow controls, approximately 42% of available width.
- Right column: contextual result or preview, approximately 58% of available width.
- Both columns align at the top and avoid the current oversized empty canvas.

Tablet and mobile collapse into one column in workflow order. Actions remain full-width and easy to reach.

## Workflow states

### State 1: Job input

The first card is titled `Add the job`.

- URL import is the default mode.
- Paste text is available through a segmented control.
- The selected mode has a strong visual state and concise supporting copy.
- URL mode uses one input and one primary `Import job` action.
- Paste mode uses a larger textarea and one primary `Extract details` action.
- A pasted standalone HTTP/HTTPS URL continues to be safely handled by the backend URL-routing safeguard.
- Loading state replaces the action label and prevents duplicate submission.
- Errors remain near the input through the existing toast system and do not erase user data.

The right column in this state shows compact guidance explaining what ApplyKit will extract and what happens next. It must not look like an empty placeholder.

### State 2: Imported job and fit analysis

After a successful import or extraction:

- Replace the raw input area with a compact job summary card.
- Show company, role, location, source domain, and an imported/extracted status.
- Provide `Change job` as a secondary action.
- Keep job description available in an expandable section rather than always occupying the form.
- Keep company, role, location, and salary editable in a clearly labeled `Job details` section.
- Present one dominant `Analyze fit` action.

The right column displays either:

- a fit-analysis introduction before analysis,
- a loading state during analysis,
- the Role Evidence Match result after success, or
- a clear recoverable error state.

Generation remains available without analysis, but is visually secondary until a fit result exists.

### State 3: Generate cover letter

After fit analysis, or when the user chooses to skip it:

- Reveal a `Writing preferences` section containing tone and optional emphasis.
- Tone uses compact selectable cards with short descriptions, not plain unlabeled buttons.
- Show the active profile as contextual information rather than a competing card.
- Use one dominant `Generate cover letter` action.
- Clearly label the secondary `Generate without fit review` path when no analysis exists.

The right column becomes the generation and preview area:

- informative loading state while streaming,
- cover-letter preview after completion,
- copy and PDF actions grouped with the preview,
- fit result remains reachable without dominating the final document.

## Visual hierarchy

- Reduce card nesting and border repetition.
- Use a consistent 16–24 px spacing rhythm.
- Use one primary card surface for each major left-column section.
- Use muted section labels and stronger task titles.
- Avoid large decorative icons floating in empty space.
- Keep buttons visually ranked: one primary, supporting secondary actions, and quiet text actions.
- Use the existing theme tokens and components; do not add a new color system.

## State and data behavior

Existing state and behavior must remain intact:

- active profile loading and switching,
- password-mode draft recovery,
- URL and pasted-text scraping,
- editable company, role, location, and salary,
- Role Evidence Match analysis,
- cover-letter streaming generation,
- PDF download and clipboard copy,
- readiness checks,
- legacy fit compatibility through the existing compatibility layer.

The redesign may introduce derived UI state or small presentation helpers, but must not change backend API contracts.

## Error and edge cases

- Empty profile: explain why generation is unavailable and point to profile setup without hiding job import.
- AI connection not ready: retain the readiness notice and disable only AI-dependent actions.
- Import failure: preserve the URL and offer paste-text mode as a recovery route.
- Parse failure: preserve pasted text for editing and retry.
- Fit analysis failure: keep imported job data and allow retry or generation without fit review.
- Generation failure: preserve job details, preferences, and fit result.
- Profile switch: retain the existing warning and clear only generated output that belongs to the previous profile.

## Accessibility

- All form controls have visible labels.
- Segmented controls expose selected state.
- Buttons retain clear focus rings and disabled states.
- Progress steps include text and status, not color-only meaning.
- Expand/collapse controls expose their state and have sufficiently large targets.
- Mobile reading and keyboard order follow the workflow sequence.

## Testing

Focused frontend tests must verify:

- the redesigned workflow retains URL and paste modes,
- imported job summary and change-job behavior exist,
- one primary action is exposed for the active stage,
- writing preferences appear in the generation stage,
- the page retains Role Evidence Match and cover-letter generation integrations,
- existing frontend unit tests, Svelte checks, production build, and container smoke test pass.

Manual verification must cover desktop and narrow viewport behavior, light and dark themes, URL import, pasted job text, fit analysis, generation, copy, PDF download, error recovery, draft restoration, and profile switching.

## Out of scope

- Redesigning Smart Apply, History, Tracker, Profile, or global navigation.
- Changing Role Evidence Match scoring or backend behavior.
- Introducing a new design system, font, animation library, or global theme.
- Adding new job-board integrations.
- Merging PR #57, tagging `v1.3.0`, or publishing a release.
