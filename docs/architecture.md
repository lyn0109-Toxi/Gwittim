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

The first client is a browser-based prototype in `apps/web`.

Responsibilities:

- Ask for microphone permission.
- Capture speech through browser speech recognition.
- Render partial and final transcript events.
- Render Korean translations as subtitles.
- Provide a small input box for Korean-to-English response drafting.
- Let the user end the session and review notes.

### Realtime Backend

Responsibilities:

- Serve the browser MVP.
- Accept final transcript segments.
- Translate stable transcript segments.
- Maintain short session context for better translation.
- Generate live summaries and post-session notes.

The current MVP uses simple HTTP JSON endpoints. A later desktop version should move toward WebSocket or Realtime API events when system audio and lower latency are introduced.

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
