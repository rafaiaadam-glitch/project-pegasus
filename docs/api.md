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
{
  "source_id": "src_123",
  "status": "registered"
}
