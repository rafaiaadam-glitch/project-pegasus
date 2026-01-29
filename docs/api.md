# Pegasus API Specification

This document defines the **service interfaces** for Project Pegasus.

The API is designed to:
- Support asynchronous, long-running AI pipelines
- Be idempotent and failure-tolerant
- Expose explainable, traceable outputs
- Remain stable as internal models improve

All endpoints return **JSON** unless otherwise stated.

---

## Conventions

### Base URL
/api/v1

### IDs
- All objects use globally unique IDs (UUID or equivalent)
- IDs are opaque to clients

### Job model
- Long-running operations return a `job_id`
- Jobs are pollable and resumable

---

## Authentication (placeholder)

Authorization: Bearer <API_KEY>

(Auth strategy intentionally deferred.)

---

## Core Resources

- Source
- Session
- Segment
- Concept
- Thread
- StudyAction
- Job

---

## 1. Sources & Ingest

### Create Source (upload file)

`POST /sources`

**Request**
- multipart/form-data
- file + metadata

```json
{
  "metadata": {
    "course": "Sociology 101",
    "author": "Durkheim",
    "tags": ["exam", "theory"]
  }
}
```
Response
```
{
  "source_id": "src_123",
  "status": "registered"
}
```
List Sources
GET /sources

Response
```
[
  {
    "id": "src_123",
    "type": "audio",
    "created_at": "2026-01-29T10:00:00Z"
  }
]
```
2. Sessions
Create Session from Source
POST /sessions
Request
```
{
  "source_id": "src_123",
  "title": "Lecture 3 – Social Constructionism",
  "context": {
    "subject": "Sociology",
    "exam_relevance": 0.8
  }
}
```
Response
```
{
  "session_id": "sess_456"
}
```
Get Session
GET /sessions/{session_id}
Response
```
{
  "id": "sess_456",
  "source_id": "src_123",
  "created_at": "2026-01-29T10:05:00Z",
  "status": "processed"
}
```
3. Pipeline Jobs
Run Full Pipeline (MVP)
POST /sessions/{session_id}/process
Request
```
{
  "steps": ["transcribe", "segment", "extract", "thread", "study"]
}
Response
{
  "job_id": "job_789"
}
Get Job Status
GET /jobs/{job_id}
Response
{
  "job_id": "job_789",
  "status": "running",
  "progress": 0.65,
  "current_step": "extract"
}
Possible statuses:
queued
running
completed
failed
partial
5. Segments
List Segments for Session
GET /sessions/{session_id}/segments
Response
[
  {
    "id": "seg_01",
    "index": 1,
    "text": "...",
    "start_time": 120,
    "end_time": 300
  }
]
6. Concepts
List Concepts for Session
GET /sessions/{session_id}/concepts
Response
[
  {
    "id": "con_001",
    "label": "Social Constructionism",
    "type": "theory",
    "confidence": 0.82,
    "segment_id": "seg_01"
  }
]
7. Threads (Core Differentiator)
List Threads
GET /threads
Response
[
  {
    "id": "thr_001",
    "canonical_label": "Social Constructionism",
    "foundational": true,
    "first_seen_session_id": "sess_123"
  }
]
Get Thread Detail
GET /threads/{thread_id}
Response
{
  "thread": {
    "id": "thr_001",
    "canonical_label": "Social Constructionism",
    "foundational": true
  },
  "events": [
    {
      "type": "first_appearance",
      "session_id": "sess_123"
    },
    {
      "type": "refinement",
      "session_id": "sess_456"
    }
  ],
  "summary": {
    "depth_level": 3,
    "text": "This theory explains how..."
  }
}
What Changed Since Last Session
GET /sessions/{session_id}/changes
Response
{
  "new_threads": ["thr_010"],
  "refined_threads": ["thr_001"],
  "repeated_threads": ["thr_004"],
  "contradictions": ["thr_007"]
}
8. Study Planner
Generate Study Plan
POST /study-plan
Request
{
  "session_id": "sess_456",
  "goal_id": "goal_001"
}
Response
{
  "actions": [
    {
      "action_type": "revise",
      "thread_id": "thr_001",
      "estimated_minutes": 20,
      "priority_score": 0.92,
      "rationale": "Repeated across 3 lectures and likely exam topic"
    }
  ],
  "stop_signal": true
}
9. Outputs
Session Summary
GET /sessions/{session_id}/summary
Skeleton Outline
GET /sessions/{session_id}/outline
Exam Questions
GET /sessions/{session_id}/questions
Flashcards (optional)
GET /threads/{thread_id}/flashcards
10. User Goals
Create Goal
POST /goals
{
  "subject": "Sociology",
  "exam_date": "2026-05-10",
  "preferred_pace": "normal"
}
List Goals
GET /goals
11. Error handling
Standard error format
{
  "error": {
    "code": "PIPELINE_FAILED",
    "message": "Extraction step failed",
    "recoverable": true
  }
}
Guarantees
All POST endpoints are idempotent where possible
Failed steps do not delete previous data
Re-running pipelines creates new derived records
No endpoint relies on LLM internal state
Next steps
Implement minimal API skeleton
Add background job runner
Wire API to pipeline modules
Lock schemas before UI work
