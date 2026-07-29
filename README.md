# Gwittim

Gwittim is a quiet real-time conversation assistant for non-native speakers.

The first product goal is simple: listen to English conversations, translate them into Korean in near real time, and quietly help the user understand, respond, and review what happened afterward.

## Quick Start

Gwittim currently ships as a local browser MVP with a small Node API server and Gemini Live API WebSocket streaming.

1. Copy the example environment file.

   ```bash
   npm run setup
   ```

2. Add your Gemini API key to `.env`.

   You can create or copy a key in [Google AI Studio](https://aistudio.google.com/apikey).

   ```bash
   nano .env
   ```

   ```text
   GEMINI_API_KEY=your-real-gemini-key-here
   GEMINI_LIVE_MODEL=gemini-3.5-live-translate-preview
   GEMINI_TEXT_MODEL=gemini-3.6-flash
   GEMINI_TRANSLATION_TARGET=ko
   ```

   Save in `nano` with `Control + O`, press `Enter`, then exit with `Control + X`.

3. Start the app.

   ```bash
   npm run doctor
   npm start
   ```

4. Open the local app.

   ```text
   http://localhost:3000
   ```

The browser app streams 16 kHz PCM microphone audio to Gemini Live, receives English transcription and Korean interpretation events, and renders Korean interpretation as live subtitles. Chrome is recommended.

For a fuller local checklist, see [Local Run Guide](docs/local-run.md).

## Streamlit Cloud Deploy

This repository also includes a Streamlit-compatible preview for quick public deployment.

Use these settings on Streamlit Cloud:

```text
Repository: lyn0109-Toxi/Gwittim
Branch: main
Main file path: streamlit_app.py
```

Add your Gemini key in Streamlit Cloud secrets:

```toml
GEMINI_API_KEY = "your_api_key_here"
GEMINI_TEXT_MODEL = "gemini-3.6-flash"
GEMINI_TRANSLATION_TARGET = "ko"
```

The Streamlit version is a deployable text-input preview. The local Node version is the realtime microphone interpreter.

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

1. Capture live microphone audio.
2. Stream audio to Gemini Live API over WebSocket.
3. Receive English transcription and Korean interpretation events.
4. Render Korean subtitle-style output.
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
├── streamlit_app.py  # Streamlit Cloud deployment entrypoint
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
