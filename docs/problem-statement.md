# Grabpic — Problem Statement (Vyrothon 2026)

**Time:** 1h 45m | **Domain:** Backend | **Difficulty:** Medium

---

## Concept

Grabpic is a high-performance image processing backend designed for large-scale events.

**Example scenario:** A marathon with 500 runners, photographers taking 50,000 photos. Instead of manual tagging, Grabpic uses facial recognition to automatically group images and provide a secure "Selfie-as-a-Key" retrieval system.

---

## Requirements

### Discovery & Transformation
- System must crawl a storage to ingest and index raw data/images
- Use facial recognition to assign a unique internal `grab_id` to every unique face discovered
- **A single image might contain multiple people — schema must map one image to many grab_ids**
- Persist the mapping and image identifiers in a relational or vector-capable database

### Selfie Authentication
- Users authenticate using an image file (the search token)
- Compare the input face against known `grab_id`s
- Should return a `grab_id` which acts as authorizer

### Data Extraction
- An endpoint for fetching user's images

### Nice to Have
- Docs: Postman or Swagger
- Unit tests
- Schema & Architecture design

---

## Judging Criteria

| Criterion | Weight |
|---|---|
| Working APIs | 25% |
| Face to ID transformation | 20% |
| Selfie Auth | 15% |
| API Structure & Error Handling | 15% |
| Multiple faces to Image Transformation | 10% |
| Problem Judgement & Analysis | 10% |
| Docs & Design | 5% |

---

## Submission
- Repository link (GitHub)
- README with clear steps to build and run the API + curls (if docs not provided)

## Rules
- Any tech stack acceptable. Preferred: Go (chi, fiber, net-http), Python (django, flask, fastapi), Postgres
- Third-party libraries allowed
- Vibecoding, LLMs, and web search allowed

---

## Key Insight from Judging Criteria

The top 3 criteria sum to **60%** of the score:
1. **Working APIs (25%)** — it must actually run
2. **Face to ID transformation (20%)** — deduplication, correct grab_id assignment
3. **Selfie Auth (15%)** — threshold logic, confidence, rejection handling

Multiple faces to image transformation is **10%** and most people will skip it. Don't.

"Problem Judgement & Analysis" is **10%** and is won by:
- Returning confidence score (not just grab_id)
- Rejecting multi-face selfies with clear error messages
- Documenting your threshold reasoning in README