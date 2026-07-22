# Data Model

## Entities

1. **Session**
   - `session_id` (PK, string, UUID)
   - `created_at` (datetime)
   - `last_active_at` (datetime)

2. **FileMetadata**
   - `id` (PK, integer)
   - `session_id` (FK -> Session)
   - `filename` (string)
   - `columns` (JSON)
   - `row_count` (integer)
   - `temp_path` (string)

3. **Message (Chat History)**
   - `id` (PK, integer)
   - `session_id` (FK -> Session)
   - `role` (string: "user", "assistant")
   - `content` (text)
   - `created_at` (datetime)

## Lifecycle
- **Creation**: Sessions are created upon first CSV upload.
- **Retention**: Data is session-bound. A cleanup cron/job removes sessions and temp CSV files older than 24 hours.
