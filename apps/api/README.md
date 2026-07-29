# Gwittim API

This app hosts the local MVP backend for translation, summaries, response suggestions, and static web serving.

Current responsibilities:

- Serve `apps/web` at `http://localhost:3000`.
- Accept transcript text from the browser MVP.
- Translate English into Korean through the OpenAI Responses API.
- Generate live Korean summaries.
- Compose natural English responses from Korean drafts.

Run from the repository root:

```bash
npm start
```
