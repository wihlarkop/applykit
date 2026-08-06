# Role Evidence Match

Role Evidence Match measures how strongly the evidence in a career profile supports the requirements in a job description. It is an evidence-based application-tailoring aid. It is **not a hiring probability**, an ATS pass probability, an interview probability, or an automated hiring decision.

ApplyKit uses a hybrid architecture:

1. The configured language model extracts atomic, job-related requirements and proposes links to profile evidence.
2. ApplyKit validates those IDs and classifications.
3. A deterministic rules engine calculates requirement strength, category scores, confidence, eligibility, and whether a score is reliable enough to display.
4. Each result is stored as an immutable, versioned analysis snapshot for audit and comparison.

The language model does not calculate the final score.

## What the result contains

A successful analysis reports these separately:

- **Role Evidence Match** — how strongly the profile supports the job requirements.
- **Confidence** — how complete, reliable, and consistent the available evidence is.
- **Eligibility** — explicit work-related conditions such as work authorization, required location, professional licensing, security clearance, or a language genuinely needed for the work.

A high match score does not override an eligibility issue. Missing eligibility information is reported as unclear rather than treated as failure.

## Requirement categories

Every atomic requirement has one primary scoring category. Compound sentences are split so that duration, capability, and job task are not scored as one opaque item.

| Category | Overall weight |
| --- | ---: |
| Essential qualifications | 30% |
| Relevant competencies | 30% |
| Relevant work and tasks | 25% |
| Preferred qualifications | 10% |
| Contextual alignment | 5% |

Eligibility and trainable requirements are tracked separately and do not become extra percentage categories.

### Importance within a category

| Importance | Weight |
| --- | ---: |
| Critical | 1.00 |
| Important | 0.70 |
| Supporting | 0.40 |

Repeated wording is clustered into one canonical requirement. ApplyKit records `mention_count`, source quotes, and importance conflicts, but repetition does not multiply points.

## Evidence strength

Evidence strength is calculated for each requirement:

```text
base strength = relationship × source × depth × recency
```

### Source multipliers

| Evidence source | Multiplier |
| --- | ---: |
| Work experience | 1.00 |
| Project | 0.80 |
| Certification or education | 0.60 |
| Skills list or profile summary only | 0.35 |

A skills-list entry can support an assessment, but it cannot independently demonstrate strong production capability.

### Depth multipliers

| Evidence depth | Multiplier |
| --- | ---: |
| Production ownership | 1.00 |
| Hands-on contribution | 0.80 |
| Exposure only | 0.45 |

### Semantic relationship

| Relationship | Multiplier |
| --- | ---: |
| Exact or direct | 1.00 |
| Close functional equivalent | 0.75 |
| Adjacent transferable | 0.40 |
| Unrelated | 0.00 |

### Relationship ceilings

Relationship ceilings prevent a related tool from being presented as exact tool experience:

- Exact or direct evidence may reach Strong.
- A functional equivalent may reach Strong for a capability-based requirement.
- A functional equivalent for an explicitly required tool is capped below Strong.
- A functional equivalent for an operational tool requirement is capped at Weak.
- Adjacent evidence is capped at Weak.
- Unrelated evidence receives no credit.

For example, Google Pub/Sub can strongly support an event-driven messaging capability. It does not automatically prove direct Kafka operations experience.

### Independent corroboration

Independent evidence receives diminishing additional credit:

```text
combined strength =
  best evidence
  + 10% × second-best evidence
  + 3% × third-best evidence
```

The result cannot exceed 1.00, and relationship ceilings still apply. Duplicate text receives no bonus. A fourth or later independent item can improve confidence but does not add more score.

## Technology volatility and recency

Old experience remains valid. Recency adjusts strength; it does not erase genuine experience.

### Stable technology or capability

| Time since last use | Multiplier |
| --- | ---: |
| 0–5 years | 1.00 |
| More than 5 years | 0.90 |

### Evolving technology

| Time since last use | Multiplier |
| --- | ---: |
| 0–3 years | 1.00 |
| More than 3 through 6 years | 0.85 |
| More than 6 years | 0.70 |

### Fast-moving technology

| Time since last use | Multiplier |
| --- | ---: |
| 0–2 years | 1.00 |
| More than 2 through 4 years | 0.75 |
| More than 4 years | 0.50 |

Current related foundation experience may support confidence in older framework-specific experience, but it does not rewrite that experience as current.

## Experience duration

Duration is calculated in months from relevant work intervals. Overlapping roles are merged so the same calendar period is not counted twice. Skills-list entries do not prove duration, and unverifiable dates remain Unknown.

| Candidate duration compared with the requirement | Assessment |
| --- | --- |
| 100% or more | Strong |
| 85–99% | Moderate |
| 60–84% | Weak |
| Below 60% | No supporting evidence for the duration threshold |
| Cannot be verified | Unknown |

A small shortfall does not make a candidate automatically ineligible.

## Unknown information

Unknown means there is not enough information to assess a requirement. It is different from explicit failure and different from no supporting evidence.

Each category uses **shrink toward neutral**:

```text
known match = weighted average of assessable requirements
known coverage = assessable requirement weight ÷ total requirement weight
unknown coverage = 1 − known coverage

category score =
  known match × known coverage
  + 0.50 × unknown coverage
```

This prevents incomplete profiles from receiving extreme scores while avoiding the false claim that missing information is a confirmed failure.

## Essential-requirement limits

The engine calculates the normal score first, then applies the strictest applicable internal limit.

### Unsupported essential requirements

| Count | Internal maximum | Highest displayed value |
| --- | ---: | ---: |
| 0 | No limit | No limit |
| 1 | 74 | 70 |
| 2 | 59 | 55 |
| 3 or more | 44 | 40 |

### Unknown essential requirements

| Count | Internal maximum | Highest displayed value |
| --- | ---: | ---: |
| 0 | No limit | No limit |
| 1 | 89 | 85 |
| 2 | 79 | 75 |
| 3 or more | 69 | 65 |

The strictest limit wins when unsupported and unknown requirements coexist. The UI displays the overall score in increments of five and never rounds above the internal limit.

## Match levels and display bands

Per-requirement evidence strength maps to:

| Strength | Requirement assessment |
| --- | --- |
| 0.75–1.00 | Strong match |
| 0.45–0.749 | Moderate match |
| 0.10–0.449 | Weak match |
| 0.00–0.099 | No supporting evidence |
| Insufficient information | Unknown |
| Explicit opposing evidence | Conflicting information |

The overall displayed score is rounded to the nearest five:

| Displayed score | Result band |
| --- | --- |
| 85–100 | Exceptional evidence match |
| 70–84 | Strong evidence match |
| 55–69 | Moderate evidence match |
| 40–54 | Limited evidence match |
| 0–39 | Weak evidence match |

## Confidence

Confidence is calculated separately from the match score:

```text
confidence =
  45% known requirement coverage
  + 35% evidence reliability
  + 20% evidence consistency
```

| Confidence result | Label |
| --- | --- |
| 0.80 or higher | High confidence |
| 0.55–0.79 | Medium confidence |
| Below 0.55 | Low confidence |

Evidence reliability is based primarily on the strongest source supporting each assessed requirement. Consistency decreases when requirement classifications conflict, validated links are rejected, or unresolved review items remain.

## No reliable evidence, no authoritative score

ApplyKit follows this safety rule:

> **No reliable evidence, no authoritative score.**

The primary score is shown only when all of these conditions hold:

- at least three non-excluded atomic requirements were identified;
- known weighted requirement coverage is at least 60%;
- deterministic confidence is at least 55%;
- unresolved conflict rate is no more than 20%;
- deterministic scoring completed successfully.

Otherwise, ApplyKit shows **Analysis needs review**. Provider failure, invalid structured output, or insufficient evidence never produces a default or guessed score.

## Eligibility

Eligibility statuses are:

- Eligible
- Likely eligible
- Eligibility unclear
- Likely ineligible
- Ineligible

`Ineligible` requires both an explicit mandatory job condition and explicit contradictory profile evidence. Missing information generally produces `Eligibility unclear`.

Years of experience are not treated as an eligibility gate unless they are part of an explicit legal, licensing, or regulatory condition.

## Fairness guardrails

The following must not affect score, confidence, recommendations, or eligibility proxies:

- name or photo;
- age or date of birth;
- gender;
- race or ethnicity;
- religion;
- marital or family status;
- health condition or disability;
- detailed residential address;
- nationality used as a proxy;
- inferred personality from writing style.

ApplyKit removes identity and contact fields from the analysis profile projection. Explicit job-related conditions such as work authorization, required language for the actual work, licensing, clearance, and location can be assessed separately.

Potentially non-job-related requirements use **exclude, warn, and continue**. They do not enter the score, the remaining job description is still analyzed, and ApplyKit does not automatically make a legal accusation about the employer.

## Review, overrides, and audit history

Users may review requirements and correct:

- requirement importance;
- an incorrectly linked piece of evidence;
- whether they do not have the experience;
- whether real evidence exists but is not included in the current profile;
- whether a requirement should be excluded from this analysis.

A correction never mutates the old result. ApplyKit creates a new immutable child snapshot, recalculates the deterministic result, and stores the extracted value, effective value, reason, source, and timestamp.

When a profile or job description is analyzed again, prior overrides use safe carry-forward states:

- **Carried forward** — the canonical requirement and material category remain compatible.
- **Needs review** — the requirement is similar but changed materially. The override does not affect scoring until confirmed.
- **Not applicable** — the old requirement no longer has a safe target.

Restoring an override also creates a new snapshot. Earlier analysis versions remain available for audit and comparison.

## Versioned analysis snapshots

Each successful, review-needed, or failed analysis stores its analysis date, profile snapshot hash, job-description hash, rules version, prompt version, provider metadata, normalized requirements, evidence links, exclusions, scoring inputs, confidence, eligibility, and failure state where applicable.

The rules engine version for this release is `role-match-v1`. The structured extraction prompt version is `role-match-extraction-v1`.

## Golden evaluation suite

The v1.3.0 merge gate includes deterministic synthetic and anonymized scenarios for:

- strong production evidence;
- keyword stuffing and duplicate text;
- equivalent and adjacent technologies;
- tool-specific relationship ceilings;
- old but genuine experience;
- duration shortfalls and overlapping roles;
- incomplete profiles;
- unclear eligibility;
- protected-field invariance;
- non-job-related requirement exclusion;
- equivalent normalized outputs from different model wording.

The fixtures do not call a live model. The same normalized input and rules version must always produce the same deterministic result.

## Legacy AI fit score

Analyses created before v1.3.0 may contain a free-form model-generated `match_score`. ApplyKit preserves those records and labels them **Legacy AI fit score**. They are not recalculated, silently converted, or treated as directly comparable with Role Evidence Match.

## Limitations

Role Evidence Match depends on the truthfulness and completeness of the profile and job description. Requirement extraction can still need human review, semantic equivalence is context-dependent, and the initial constants require continued evaluation as more representative test cases become available.

The result is application guidance. It is not a hiring probability and should not be used as an automated selection decision.
