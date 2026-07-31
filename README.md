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

## Run From GitHub

GitHub does not host the realtime interpreter as an always-on app by itself, but you can run it from GitHub with Codespaces.

1. Add `GEMINI_API_KEY` as a repository Codespaces secret.
2. Open the repository on GitHub.
3. Click `Code` > `Codespaces` > `Create codespace on main`.
4. Run:

   ```bash
   npm run doctor
   npm start
   ```

5. Open the forwarded port `3000` URL.

See [GitHub Codespaces Run Guide](docs/github-codespaces.md).

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

If Secrets are not configured yet, the deployed Streamlit app also lets you paste a Gemini API key once in the sidebar and apply it for the current browser session.

The Streamlit version has three entry points:

- `텍스트 세션`: rewrite Korean drafts into Nature Reviews Drug Discovery-level scientific English, without keeping a writing history in the app session.
- `번역 세션`: paste paper text or upload a PDF, then review `Abs 요약`, `섹터/섹션별 이슈`, `결과 처리`, `결론`, and follow-up questions in Korean.
- `통역 세션`: open the realtime microphone interpreter through the local Node app or GitHub Codespaces, with text-only subtitles and live Compose cues.

Text-session writing criteria:

- Prefer clarity, active voice, concise sentence structure, and logical flow.
- Make drug discovery and development writing accessible to adjacent scientific disciplines.
- Convert Korean-first structure into idiomatic manuscript English rather than literal translation.
- Avoid jargon-heavy phrasing, unnecessary acronyms, inflated claims, and long noun stacks.
- Use careful scientific hedging and avoid unsupported novelty, mechanistic, regulatory, clinical, or efficacy claims.
- Preserve technical terms, gene/protein nomenclature, dates, numbers, SI units, and drug names.
- Use International Nonproprietary Names for drugs when possible.
- Emphasize scientific meaning, translational relevance, and development implications only when supported by the source text.

Live Compose cues prefer natural phrasal verbs such as `follow up`, `look into`, `walk through`, `bring up`, `point out`, `move forward`, `rule out`, `narrow down`, `set up`, `carry out`, and `circle back` when they fit the conversation.

The local Node version is the realtime microphone interpreter.

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
7. Generate live English response cues while interpretation is running.

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
