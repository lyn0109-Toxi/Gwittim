# Gwittim API

This app hosts the local MVP backend for realtime interpretation, summaries, response suggestions, and static web serving.

Current responsibilities:

- Serve `apps/web` at `http://localhost:3000`.
- Create short-lived Gemini Live API tokens without exposing the API key to the browser.
- Accept transcript text from the browser MVP.
- Translate English into Korean through Gemini `generateContent`.
- Generate live Korean summaries.
- Compose natural English responses from Korean drafts.

Run from the repository root:

```bash
npm start
```
