# UI

## UI Type
Web dashboard (chat interface) served at `/app`.

## Views / Screens
### Screen: Analyst Chat
**Purpose:** The main interface for officers to ask questions about police data, view answers with supporting details (SQL, charts), and manage recent/pinned reports.

**Key elements:**
- Chat input box at the bottom: single-line text field with placeholder "Ask about FIRs, personnel, or logistics..."
- Send button (paper plane icon) to the right of the input.
- Chat history area above the input, displaying messages in bubbles:
  - User messages: left-aligned, with a subtle background.
  - Agent messages: right-aligned, containing:
    - The answer in plain text.
    - A collapsible section labeled "View SQL" that, when expanded, shows the executed SQL query in a monospace block with a copy button.
    - A collapsible section labeled "View Chart" (if a chart is applicable) that shows a visualization (e.g., bar, line, pie) of the result data.
    - A collapsible section labeled "View Table" (if the result is tabular) that shows the data in a searchable, sortable table with pagination.
    - A pin icon (bookmark) in the top-right of the agent message bubble to save the query and result as a pinned report.
- Sidebar on the left (collapsible via a hamburger menu at top-left):
  - Section "Recent": list of the last 10 questions asked by the officer (most recent at top), each showing a truncated question and timestamp; clicking re-populates the input with that question.
  - Section "Pinned": list of pinned reports (saved by the officer), each showing a truncated question and a pin icon; clicking re-populates the input with that question.
  - Section "Dashboard" (Phase 2+): placeholder for pre-built reports.

## Error States
- **Empty state:** When no messages have been exchanged, the chat area shows a friendly illustration and text: "Ask me anything about FIRs, personnel, or logistics data. For example: 'Show total FIRs registered last week in Lucknow district'."
- **Loading state:** When the agent is processing a question, the input is disabled, and a spinner appears inside the send button with the text "Thinking...".
- **Error state:** If the agent returns an error, the message bubble shows a red warning icon and the error message in plain text, with a suggestion to rephrase the question.
- **Clarification state:** If the agent needs more information, the message bubble shows a yellow info icon and a question asking for the missing details (e.g., "To answer that, I need to know: which district are you interested in?"), followed by suggested options or a text field.

## Tech Stack
HTML5, CSS3, vanilla JavaScript (no build step). Served as static files by the FastAPI backend at `/app`.