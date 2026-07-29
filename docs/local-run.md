# Local Run Guide

Gwittim's realtime interpreter runs locally through the Node app.

## Requirements

- Node.js 20 or newer.
- Chrome or another browser with WebRTC and microphone support.
- OpenAI API key with access to realtime translation models.
- A quiet microphone input.

## Setup

```bash
npm run setup
```

Open `.env`.

```bash
nano .env
```

Add your OpenAI API key after `OPENAI_API_KEY=`.

```text
OPENAI_API_KEY=sk-your-real-key-here
OPENAI_REALTIME_MODEL=gpt-realtime-translate
OPENAI_TRANSCRIPTION_MODEL=gpt-realtime-whisper
OPENAI_TRANSLATION_TARGET=ko
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
- The OpenAI API key stays on the local server and is not committed to Git.
- Browser microphone access generally requires `localhost`, `127.0.0.1`, or HTTPS.
- The Streamlit app is only a text-input preview. Use the Node app for realtime voice interpretation.
