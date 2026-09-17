# Web Dev Flashcards

A single-file interactive flashcard app (Module 6, L4) built with HTML, CSS, and vanilla JavaScript.

## Files

- `flashcards.html` — the complete app (markup, styles, and script in one file)
- `README.md` — this file

## How to run

Open `flashcards.html` in any modern browser. No install or server needed.

## Features

- Five Q&A cards covering HTTP methods, CSS selectors, the DOM, HTTP status codes, and async/await
- **Show / Hide Answer** toggle, with the answer hidden by default
- **Next →** and **← Previous** buttons that wrap around at either end and re-hide the answer
- **Shuffle** randomizes the card order (Fisher–Yates) and restarts at Card 1
- Progress indicator ("Card X of N"), calculated from the array length
- Keyboard shortcuts: **Space** flips the card, and **← / →** move between cards
- Accessibility: `aria-live` on the progress, question, and answer; `aria-expanded` on the Show button; a visible focus ring for keyboard users
- Error handling: an empty `cards` array shows a "No flashcards available." message and disables the controls instead of crashing

## Key concepts used

`const` vs `let`, `querySelector()`, `addEventListener()`, `textContent`, `style.display`, and modulo (`%`) for wraparound navigation.
