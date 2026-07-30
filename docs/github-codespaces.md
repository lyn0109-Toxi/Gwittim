# GitHub Codespaces Run Guide

GitHub itself does not keep Gwittim running as a public app server. The closest GitHub-native way to run the realtime interpreter is GitHub Codespaces.

Codespaces gives you a temporary cloud development machine from the GitHub repository. Gwittim can run there, and GitHub forwards port `3000` to an HTTPS URL that can request microphone permission in the browser.

## One-Time Secret Setup

1. Open the GitHub repository.
2. Go to `Settings`.
3. Open `Secrets and variables`.
4. Open `Codespaces`.
5. Add a repository secret:

```text
Name: GEMINI_API_KEY
Value: your-real-gemini-key
```

## Start From GitHub

1. Open the repository on GitHub.
2. Click `Code`.
3. Select the `Codespaces` tab.
4. Click `Create codespace on main`.
5. Wait for the workspace to open.
6. In the Codespaces terminal, run:

```bash
npm run doctor
npm start
```

7. When GitHub forwards port `3000`, click `Open in Browser`.
8. Click `통역 시작`, allow microphone access, and speak English.

## Important Notes

- Codespaces is temporary. Stop it when you are done.
- The app is available while the Codespace is running.
- For a permanent public app, deploy the Node app to a hosting service such as Render, Railway, Fly.io, or Google Cloud Run.
- GitHub Pages is not enough for this realtime app because Gwittim needs a small server to create short-lived Gemini Live API tokens.
