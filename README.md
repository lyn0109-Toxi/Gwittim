# Gwittim

Gwittim is a quiet real-time conversation assistant for non-native speakers.

The first product goal is simple: listen to English conversations, translate them into Korean in near real time, and quietly help the user understand, respond, and review what happened afterward.

## Quick Start

Gwittim currently ships as a local browser MVP with a small Node API server.

1. Copy the example environment file.

   ```bash
   cp .env.example .env
   ```

2. Add your OpenAI API key to `.env`.

   ```text
   OPENAI_API_KEY=your_api_key_here
   ```

3. Start the app.

   ```bash
   npm start
   ```

4. Open the local app.

   ```text
   http://localhost:3000
   ```

The browser app uses the browser's speech recognition support for the first MVP. Chrome is recommended.

## Product Direction

Gwittim is not just a translator. It is a discreet assistant for calls, meetings, interviews, classes, and in-person conversations.

Core experience:

- Listen to English speech from a microphone or meeting audio source.
- Show Korean subtitles with minimal delay.
- Keep the original English transcript available.
- Summarize the conversation while it is happening.
- Suggest natural English responses when the user needs help.
- Create a post-conversation note with key points, action items, and useful expressions.

## Initial MVP

The first version should prove the real-time loop:

1. Capture live audio.
2. Stream audio to speech recognition.
3. Translate recognized English into Korean.
4. Render subtitle-style output.
5. Keep a short rolling transcript.
6. Generate a brief conversation summary.

## Repository Layout

```text
.
├── apps/
│   ├── api/          # Realtime transcription, translation, and session backend
│   ├── web/          # Browser MVP for live subtitles and response drafting
│   └── desktop/      # Future desktop overlay app
├── docs/             # Product, architecture, roadmap, and privacy notes
├── packages/
│   └── realtime/     # Shared realtime protocol and event contracts
└── .github/          # GitHub issue and pull request templates
```

## Guiding Principles

- Speed matters: a translation that arrives too late is not useful in a live conversation.
- Privacy is a core feature: audio should be handled transiently whenever possible.
- The UI should stay calm: Gwittim should feel like a quiet cue, not another meeting participant.
- Consent must be explicit: users are responsible for lawful use in conversations and calls.

## Project Status

Local MVP stage.

See:

- [Product Brief](docs/product-brief.md)
- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Privacy and Consent](docs/privacy-and-consent.md)
