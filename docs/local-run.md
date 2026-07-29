# Local Run Guide

Gwittim's realtime interpreter runs locally through the Node app.

## Requirements

- Node.js 20 or newer.
- Chrome or another browser with WebSocket, Web Audio, and microphone support.
- Gemini API key with Live API access.
- A quiet microphone input.

## Setup

```bash
npm run setup
```

Open `.env`.

```bash
nano .env
```

Add your Gemini API key after `GEMINI_API_KEY=`. You can create or copy a key in [Google AI Studio](https://aistudio.google.com/apikey).

```text
GEMINI_API_KEY=your-real-gemini-key-here
GEMINI_LIVE_MODEL=gemini-3.5-live-translate-preview
GEMINI_TEXT_MODEL=gemini-3.6-flash
GEMINI_TRANSLATION_TARGET=ko
```

In `nano`, save with `Control + O`, press `Enter`, then exit with `Control + X`.

## Check

```bash
npm run doctor
npm run check
```

## Start

```bash
npm start
```

Open:

```text
http://127.0.0.1:3000
```

Click `통역 시작`, allow microphone access, and speak English.

## Notes

- Raw audio is not stored by the app.
- The Gemini API key stays on the local server and is not committed to Git.
- The browser receives only a short-lived Gemini Live API token.
- Browser microphone access generally requires `localhost`, `127.0.0.1`, or HTTPS.
- The Streamlit app is only a text-input preview. Use the Node app for realtime voice interpretation.
