# API

## API Style
REST (JSON) + Server-Sent Events (SSE) for streaming upcoming notes. Served by FastAPI on `:8001`. The built UI is mounted at `/app/`.

All responses use the envelope `{ "data": <payload>, "error": null }` on success, or HTTP error on failure.

---

### `POST /api/exercises/start`

**Purpose:** Start a drill set for a student. Makes **exactly one** Gemini call to produce teaching text, then returns the first exercise (computed).

**Request:**
```json
{
  "student_id": "student-1",
  "clefs": ["treble"],
  "topic_hint": null
}
```

**Response (200):**
```json
{
  "data": {
    "drill_id": "drill_xxx",
    "teaching": {
      "text": "Treble clef notes sit on lines and spaces...",
      "tokens": { "prompt": 120, "completion": 80, "total": 200 },
      "model": "gemini-2.5-flash",
      "used_fallback": false
    },
    "exercise": {
      "id": "note_xxx",
      "midi": 67,
      "correct_name": "G4",
      "clef": "treble",
      "staff_svg": "<svg ...>...</svg>",
      "options": ["E4","F4","G4","A4","B4"]
    }
  },
  "error": null
}
```

**Error cases:**
| Status | Condition |
|--------|-----------|
| 400 | missing `student_id` or invalid `clefs` |
| 500 | unexpected server error |

---

### `POST /api/notes/next`

**Purpose:** Get the next computed exercise, selected adaptively from the student's mastery. Streams via SSE if `stream=true` (default for ongoing); returns JSON otherwise.

**Request:**
```json
{ "drill_id": "drill_xxx", "student_id": "student-1" }
```

**Response (200):** same `exercise` object as above (without `teaching`).
**SSE stream (`GET /api/notes/stream?drill_id=...`):** pushes each next exercise as `data: {json}\n\n`.

---

### `POST /api/notes/{note_id}/check`

**Purpose:** Check the student's answer against the **computed** name.

**Request:**
```json
{ "student_answer": "g4" }
```

**Response (200):**
```json
{
  "data": {
    "correct": true,
    "computed_name": "G4",
    "hint": null,
    "revealed": false
  },
  "error": null
}
```
On a miss: `{ "correct": false, "computed_name": "G4", "hint": "From the bottom line E, count up: F, G — this is G4.", "revealed": false }`.

**Error cases:**
| Status | Condition |
|--------|-----------|
| 404 | unknown `note_id` |
| 400 | missing `student_answer` |

---

### `GET /api/notes/{note_id}/audio`

**Purpose:** Local-synthesised WAV of the note (no API). Returns `audio/wav`.

**Error cases:**
| Status | Condition |
|--------|-----------|
| 404 | unknown `note_id` |

---

### `GET /api/notes/{note_id}/speak?text=...`

**Purpose:** edge-tts MP3 of the given teaching/hint text. Returns `audio/mpeg`.

**Error cases:**
| Status | Condition |
|--------|-----------|
| 503 | edge-tts unreachable (UI shows text) |

---

### `GET /api/mastery?student_id=...`

**Purpose:** Return the student's per-topic mastery for the progress view.

**Response (200):** `{ "data": [ { "topic": "treble:G4", "weight": 0.7, "attempts": 3, "correct": 2 } ] }`

---

## Authentication
None (local single-screen tutor tool). `student_id` is a free-form client-supplied identifier.
