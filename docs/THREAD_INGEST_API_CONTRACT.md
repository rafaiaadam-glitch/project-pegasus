# Thread Ingest API Contract

## `POST /thread/ingest`

Request body:

```json
{
  "text": "string (required)",
  "preset": "string (optional, id or name)"
}
```

Response body:

```json
{
  "preset": {
    "id": "string",
    "name": "string",
    "weights": {
      "what": 0.25,
      "how": 0.25,
      "when": 0.15,
      "where": 0.15,
      "who": 0.05,
      "why": 0.15
    }
  },
  "summary": "string",
  "threads": [
    {
      "id": "string",
      "title": "string",
      "depth": 1,
      "facets": ["what", "how"],
      "itemsCount": 3,
      "lastUpdated": "ISO-8601 string"
    }
  ],
  "changeLog": [
    {
      "event": "string",
      "detail": "string"
    }
  ]
}
```

## `GET /presets`

Returns:

```json
{
  "presets": [
    {
      "id": "exam-mode",
      "name": "📝 Exam Mode",
      "description": "Optimized for structured answers..."
    }
  ]
}
```
