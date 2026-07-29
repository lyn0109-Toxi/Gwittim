# Architecture

## High-Level Flow

```text
Audio input
  -> audio chunking
  -> realtime speech recognition
  -> transcript event stream
  -> translation stream
  -> live subtitle UI
  -> summary and response assistant
  -> optional saved session note
```

## Components

### Client

The first client can be a desktop app or a browser-based prototype.

Responsibilities:

- Ask for microphone permission.
- Capture audio.
- Stream audio chunks to the backend.
- Render partial and final transcript events.
- Render Korean translations as subtitles.
- Provide a small input box for Korean-to-English response drafting.
- Let the user end the session and review notes.

### Realtime Backend

Responsibilities:

- Accept WebSocket connections.
- Receive audio chunks.
- Forward audio to speech recognition.
- Normalize partial and final transcript events.
- Translate stable transcript segments.
- Maintain short session context for better translation.
- Generate live summaries and post-session notes.

### Shared Realtime Protocol

Events should be explicit and versioned.

Example event types:

- `session.started`
- `audio.chunk`
- `transcript.partial`
- `transcript.final`
- `translation.partial`
- `translation.final`
- `summary.updated`
- `response.suggested`
- `session.ended`

## Latency Budget

Target for MVP:

- Audio capture to partial English transcript: under 1 second.
- Final English segment to Korean translation: under 2 seconds.
- Summary update: every 30 to 60 seconds.

## Data Policy Direction

- Do not store raw audio by default.
- Store transcripts and summaries only when the user explicitly enables session history.
- Provide a delete session action.
- Keep consent notices visible before starting a session.
