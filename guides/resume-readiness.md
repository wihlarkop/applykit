# Resume Readiness

Resume Readiness evaluates a **saved ApplyKit resume version** after ApplyKit renders it to PDF and extracts the PDF text again.

It answers a different question from Role Evidence Match:

- **Role Evidence Match:** Does the career profile contain evidence that supports the target job?
- **Resume Readiness:** Does this resume version communicate that evidence clearly and remain machine-readable after PDF export?

Neither result is a hiring probability or a guarantee that a particular employer's applicant tracking system will accept or rank the document.

## What is evaluated

Resume Readiness contains three categories.

### ATS Parseability

Checks whether software can extract the resume's essential information reliably, including:

- a selectable text layer;
- contact information;
- experience roles and companies;
- education and skills when present in the source profile;
- sensible source-to-PDF content coverage;
- page and parser warnings;
- bounded document size and page count.

Critical extraction failures can cap the result or produce **Analysis needs review**.

### Resume Quality

Checks deterministic writing and structure signals, including:

- missing identity information;
- summary length;
- reverse-chronological experience ordering;
- date-format consistency;
- bullet length;
- generic or duplicate bullets;
- clear action language;
- outcome clarity;
- empty core sections;
- malformed professional links;
- punctuation consistency.

Some checks are advisory. ApplyKit does not require every bullet to contain a metric when no supported metric exists.

### Job Tailoring

When a target job and compatible Role Evidence Match analysis are available, ApplyKit checks whether the resume:

- includes strongly supported important requirements;
- uses relevant terminology only when supported by profile evidence;
- avoids unsupported job keywords;
- avoids excessive keyword repetition;
- represents supported evidence across relevant requirement categories.

Job Tailoring never authorizes ApplyKit to invent experience or add unsupported claims.

## General and job-specific modes

### General mode

Used when no target job is supplied.

- ATS Parseability: 55%
- Resume Quality: 45%
- Job Tailoring: not assessed

### Job-specific mode

Used when a target job is supplied.

- ATS Parseability: 40%
- Resume Quality: 35%
- Job Tailoring: 25%

Job-specific analysis uses a server-loaded Role Evidence Match analysis when available. A non-authoritative or incompatible role analysis causes the tailoring result to require review rather than silently trusting a client-provided score.

## Result bands

| Score | Band |
|---:|---|
| 90–100 | Excellent |
| 75–89 | Good |
| 60–74 | Needs improvement |
| 0–59 | Not ready |

A hard gate may cap the final score below the raw weighted result.

## Analysis states

### Complete

The analysis produced an authoritative result under the current rule version.

### Analysis needs review

Extraction coverage, job context, or supporting evidence is not reliable enough for an unqualified result.

### Failed

An operational error prevented analysis. A failed analysis has no score; it is not represented as a low-quality resume.

## How to use Resume Readiness

1. Open **Resume**.
2. Select the active career profile.
3. Optionally paste a target job description.
4. Generate a saved resume version.
5. Select **Check Resume Readiness**.
6. Review critical issues first, then important and optional improvements.
7. Update the profile or regenerate the resume.
8. Run the analysis again.

Each new run creates an immutable analysis record and references the analysis it supersedes.

## Extraction preview

ApplyKit shows a bounded extraction preview containing:

- page count;
- text-layer status;
- source-profile coverage;
- parser warnings;
- extracted text preview.

The preview helps identify information that appears visually in the PDF but is missing or out of order in machine extraction.

## Backward-compatible routes

The v1.4 product language introduces canonical routes while retaining existing URLs:

| Existing route | Canonical route |
|---|---|
| `/generate` | `/resume` |
| `/history` | `/documents` |
| `/tracker` | `/applications` |

Existing bookmarks and links continue to work. The Resume routes render the same shared workspace.

## Existing resumes

Generated resumes created before v1.4 remain available. They are shown as **Not analyzed** until Resume Readiness is run explicitly.

No legacy score is converted into a Resume Readiness result.

## Privacy and limits

For ApplyKit Community, analysis occurs inside the self-hosted installation.

The MVP analyzes only resumes generated and stored by ApplyKit. Arbitrary external resume upload is intentionally deferred.

Current processing limits:

- maximum PDF size: 5 MB;
- maximum pages: 10;
- maximum extracted text: 100,000 characters.

Complete resume and job-description contents are not intended for operational logs.

## What ApplyKit does not claim

Resume Readiness does not claim:

- a probability of passing an ATS;
- a probability of receiving an interview;
- a probability of receiving an offer;
- compatibility with every employer configuration;
- permission to add experience absent from the user's career profile.
