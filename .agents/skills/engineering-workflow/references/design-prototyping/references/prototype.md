# Prototype

A prototype is **throwaway code that answers a question**. The question decides the shape.

## Pick a branch

Identify which question is being answered:

- **"Does this logic / state model feel right?"** -> Logic prototype. Build a tiny interactive terminal app that pushes the state machine through cases that are hard to reason about on paper.
- **"What should this look like?"** -> UI prototype. Generate several radically different UI variations on a single route, switchable via a URL search param.

The two branches produce very different artifacts. If the question is genuinely ambiguous, default to whichever branch better matches the surrounding code (a backend module -> logic; a page or component -> UI) and state the assumption at the top.

## Rules that apply to both

1. **Throwaway from day one, and clearly marked as such.** Locate the prototype code close to where it will actually be used — but name it so a casual reader can see it's a prototype, not production.
2. **One command to run.** Whatever the project's existing task runner supports — `task <name>`, `uv run <path>`, `pnpm <name>`, etc.
3. **No persistence by default.** State lives in memory. Persistence is the thing the prototype is _checking_, not something it should depend on.
4. **Skip the polish.** No tests, no error handling beyond what makes the prototype _runnable_, no abstractions. The point is to learn something fast and then delete it.
5. **Surface the state.** After every action, print or render the full relevant state so the user can see what changed.
6. **Delete or absorb when done.** When the prototype has answered its question, either delete it or fold the validated decision into the real code.

## Logic Prototype

A tiny interactive terminal app that lets the user drive a state model by hand.

### Logic Process

1. **State the question** — write down what state model and what question you're prototyping.
2. **Pick the language** — use whatever the host project uses (Python for backend, TypeScript for docs site).
3. **Isolate the logic in a portable module** — put the actual logic behind a small, pure interface that could be lifted into the real codebase later. The TUI around it is throwaway; the logic module shouldn't be.
4. **Build the smallest TUI that exposes the state** — on every tick, clear the screen and re-render the whole frame. Show current state + keyboard shortcuts at the bottom.
5. **Make it runnable in one command** — add a script to the project's task runner.
6. **Hand it over** — give the user the run command.
7. **Capture the answer** — when done, the answer is the only thing worth keeping.

## UI Prototype

Generate **several radically different UI variations** on a single route, switchable from a floating bottom bar.

### UI Process

1. **State the question and pick N** — default to 3 variants. Cap at 5.
2. **Generate radically different variants** — variants must be structurally different, not just different colors.
3. **Wire them together** — create a switcher component using `?variant=` URL search param.
4. **Build the floating switcher** — fixed-position bar at the bottom with left/right arrows and variant label.
5. **Hand it over** — surface the URL and variant keys.
6. **Capture the answer and clean up** — delete losing variants, fold winner into real code.

### Sub-shapes

- **Sub-shape A (preferred)** — adjustment to an existing page. Variants rendered on the same route, gated by `?variant=`.
- **Sub-shape B (last resort)** — a new throwaway route. Only use when no existing page can host the variants.

## When done

The _answer_ is the only thing worth keeping from a prototype. Capture it somewhere durable (commit message, ADR, issue, or a `NOTES.md` next to the prototype) along with the question it was answering.

## Anti-Patterns

- Don't add tests to a prototype.
- Don't wire it to the real database.
- Don't generalise — the prototype answers one question.
- Don't blur the logic and the TUI together.
- Don't ship the TUI shell into production.
- Don't leave variant components or switcher lying around after the prototype is done.
