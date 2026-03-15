# ApplyKit Future Roadmap (2026-03-15)

This roadmap outlines high-impact frontend improvements and feature expansions for ApplyKit, focusing on a premium, AI-first user experience.

---

## ✨ Premium UX Polish (Immediate Wins)

### 1. Animated Toast System
**Concept**: Replace simple success text with floating, animated notifications (Toasts) for actions like "Save Profile", "CV Copied", or "Error Occurred".
- **Benefit**: Feels like a high-end SaaS product; provides clear, consistent feedback across all pages.

### 2. Skeleton Screen Loading
**Concept**: Instead of spinners, show "shimmering" ghost versions of cards, forms, and CV previews while data is being fetched or AI is generating.
- **Benefit**: Dramatically improves "Perceived Performance"—the app feels faster even if AI takes a few seconds.

### 3. Profile "Scrollspy" Navigation
**Concept**: A sticky sidebar or secondary sub-nav on the Profile page that highlights which section you're in (Personal Info, Skills, Education).
- **Benefit**: Makes it much easier to jump between long form sections on desktop.

### 4. Confetti & Celebration
**Concept**: Add a subtle burst of confetti when someone completes their onboarding or generates their first CV.
- **Benefit**: Creates a "Moment of Delight" that makes the user feel successful.

---

## 🎨 UI/UX Enhancements

### 1. Interactive CV Builder (Real-time Preview)
**Concept**: A split-screen experience where the left side is the editor and the right side is a live-updating PDF/HTML preview.
- **Benefit**: Users can immediately see how their data and styling choices affect the final document.
- **FE Requirements**: Integration with high-fidelity HTML-to-PDF libraries and reactive preview rendering.

### 2. Multi-Profile Support
**Concept**: Allow users to maintain multiple professional identities (e.g., "Software Engineer" vs "Technical Manager").
- **Benefit**: Targeting various industries without overwriting core data.

### 3. Progressive Dark Mode
**Concept**: A sleek, "Deep Night" dark mode toggle with high-contrast variants for accessibility.
- **Benefit**: Essential for a "Pro" development tool feel.

### 4. LinkedIn Persona Optimizer
**Concept**: AI-generated headlines and "About" sections tailored to the user's best achievements for LinkedIn visibility.
- **Benefit**: Ensures a consistent professional brand across platforms.

---

## 🔬 Analysis & Strategy

### 1. AI Skill Gap Analysis
**Concept**: Compare a user's profile against a Job Description and highlight specific keywords, technologies, or concepts they are missing.
- **Benefit**: Helps users identify learning targets or how to better frame existing experience.

### 2. Interactive Resume Scoring
**Concept**: A "Match Score" (0-100) that predicts how well a CV aligns with a specific role, highlighting "Yellow Flag" areas that need more quantification or detail.
- **Benefit**: Provides objective feedback before the user sends out an application.

### 3. Role-Based Versioning & History
**Concept**: Maintain a library of every CV and Cover Letter generated, tagged by company and role type.
- **Benefit**: Never lose a specific tailored version; allows for "one-click revisions" to previous successful applications.

### 4. Salary Negotiation AI
**Concept**: AI-driven market value research and customized negotiation scripts for the "Offer" stage.
- **Benefit**: Empowers users to maximize their compensation once they land the role.

---

## 🚀 Advanced AI Features

### 1. AI Interview Coach (Voice enabled)
**Concept**: A practice area using the **Web Speech API** to let users practice their "Elevator Pitch" and receive verbal feedback.
- **Benefit**: Bridges the gap between written preparation and oral performance.

### 2. Job Application Tracker (Kanban)
**Concept**: A visual board (Applied -> Interviewing -> Offer -> Rejected) to manage the job hunt lifecycle.
- **Benefit**: Centralizes the entire job-seeking workflow in one self-hosted app.

### 3. One-Click Portfolio Generator
**Concept**: Transform your profile data into a minimalist, lightning-fast portfolio website (HTML/CSS export or simple static hosting).
- **Benefit**: Instant professional web presence without manual design work.

### 4. Networking "Cold Outreach" Generator
**Concept**: Specific AI prompts for LinkedIn networking, recruiter outreach, and follow-up emails after an interview.
- **Benefit**: Streamlines the "invisible" part of the job search.

### 5. Smart URL Cover Letter Generator
**Concept**: Instead of pasting text, users simply provide a URL to a job posting (LinkedIn, Indeed, etc.). The system automatically scrapes and crawls the site to extract the job description.
- **Benefit**: Major reduction in manual work; ensures high-fidelity tailoring by scraping the original context.

### 6. Multi-Language CV Translation
**Concept**: One-click translation of the profile data into multiple languages for global job markets.
- **Benefit**: Essential for international candidates.

---

## 🛠️ Required API Specs

### Interview Prep API
- **Endpoint**: `POST /api/ai/interview-prep`
- **Body**: `{ "job_description": "string", "profile_id": "string" }`
- **Goal**: Returns a list of behavioral and technical questions based on the candidate's actual history.

### Application Lifecycle API
- **Endpoint**: `POST /api/applications`
- **Body**: `{ "company": "string", "role": "string", "status": "string", "cv_id": "string" }`
- **Goal**: Links generated documents to specific tracking events.

### Job Scraping API
- **Endpoint**: `POST /api/ai/scrape-job`
- **Body**: `{ "url": "string" }`
- **Goal**: Automatically crawls a job board URL and returns structured JSON with the job description and company metadata.
