# Architecture

## High-Level Flow

```text
Audio input
  -> browser WebRTC connection
  -> OpenAI Realtime API
  -> English transcription event stream
  -> Korean interpretation stream
  -> live subtitle UI
  -> summary and response assistant
  -> optional saved session note
```

## Components

### Client

The first client is a browser-based prototype in `apps/web`.

Responsibilities:

- Ask for microphone permission.
- Capture microphone audio.
- Stream microphone audio through WebRTC.
- Render partial and final transcript events.
- Render Korean translations as subtitles.
- Provide a small input box for Korean-to-English response drafting.
- Let the user end the session and review notes.

### Realtime Backend

Responsibilities:

- Serve the browser MVP.
- Create short-lived Realtime Translation client secrets while keeping the OpenAI API key server-side.
- Accept final transcript segments.
- Translate stable transcript segments.
- Maintain short session context for better translation.
- Generate live summaries and post-session notes.

The current MVP uses OpenAI Realtime API WebRTC for microphone interpretation and simple HTTP JSON endpoints for summaries and response drafting. A later desktop version should add system audio capture where platform permissions allow it.

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
