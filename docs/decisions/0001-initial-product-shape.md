# Decision 0001: Initial Product Shape

## Status

Accepted

## Decision

Gwittim will begin as a realtime English-to-Korean conversation assistant, not as a phone-call recorder.

## Why

Direct phone-call audio capture is restricted on major mobile platforms and introduces legal and product complexity early. A microphone or meeting-audio based assistant lets us validate the core loop first:

- Listen.
- Transcribe.
- Translate.
- Summarize.
- Suggest responses.

## Consequences

- The first MVP can be tested in live conversations and online meetings.
- Desktop or browser prototypes are practical early targets.
- Phone-call support can be revisited after the core realtime experience works.
