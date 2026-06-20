# Design Grill

Use this skill to interrogate a plan or design until the next implementation move is clear. Ask one question at a time, provide a recommended answer for each question, and resolve dependencies between decisions instead of jumping randomly across topics.

## First Move

1. Restate the plan in one or two sentences.
2. Identify the most consequential unresolved decision.
3. Ask one question about that decision, with a recommended answer and the tradeoff.

If the answer can be discovered from the codebase or docs, inspect them instead of asking.

## Question Loop

For each answer:

1. Reflect the decision back in crisp terms.
2. Note which later questions it unlocks or eliminates.
3. Ask the next highest-leverage question.

Keep going until:

- The design is implementable without hidden decisions.
- The user explicitly pauses the grill.
- A blocker requires external information.

## Documentation-Aware Mode

Use this when the user wants the plan challenged against project language, domain model, or existing decisions.

Look for:

- `AGENTS.md`, `CLAUDE.md`
- `.github/note/AGENTS-zh.md`
- `CONTRIBUTING.md`
- README, architecture docs, specs, or issue descriptions relevant to the plan

Challenge terminology immediately when the user's words conflict with the glossary or ADRs. Ask whether the existing term should stand, be refined, or be replaced.

## Capturing Decisions

Create or update docs only when a real decision crystallizes.

- Add glossary terms to the nearest relevant context file.
- Add an ADR only for durable architecture decisions with meaningful alternatives.
- Keep documentation edits small and tied to decisions already made in the session.

## Tone

Be rigorous but not performative. The goal is shared understanding, not winning an argument. Push when language is fuzzy, when a choice hides a cost, or when the implementation path still depends on an unstated assumption.

## Completion

End with:

- The decisions made.
- Remaining open questions, if any.
- Any docs changed.
- The next implementation step.
