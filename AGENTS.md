# Project Instructions

## Think Before Coding

- State assumptions before implementing when the request is ambiguous.
- If multiple interpretations are plausible, surface them instead of silently choosing.
- Prefer the simpler approach when it satisfies the request.
- If the requirement is unclear enough to risk the wrong change, ask before editing.

## Simplicity First

- Implement only what was asked.
- Do not add speculative features, one-off abstractions, or configurability that was not requested.
- Avoid defensive code for impossible scenarios.
- If a solution grows large, look for a smaller direct change before proceeding.

## Surgical Changes

- Touch only files and lines required by the request.
- Do not refactor, reformat, or clean adjacent code unless it is necessary for the task.
- Match existing style even when a different style would be preferred.
- Remove only imports, variables, or helpers made unused by the current change.
- Mention unrelated dead code or cleanup opportunities instead of changing them.

## Goal-Driven Execution

- Turn each task into verifiable success criteria.
- For bug fixes, add or update regression coverage first when practical.
- For multi-step work, use a short plan with a verification step for each item.
- Keep looping until the requested behavior is verified or a real blocker is identified.

## Dev Rules

- Install tools with Homebrew first when available.
- Use `uv` for Python commands and dependency work; do not use `pip` directly.
- For APIs, functions, or library usage, check current docs first, using Context7 when applicable.
- Never run `rm -rf /`.

## Content Rules

- In generated exercise flow text, every `準備，吸氣...` cue must be on its own line. The following action or breath cue starts on the next line, for example:
  ```text
  準備，吸氣...
  呼氣，...
  ```
- Preserve source-faithful OCR excerpts unless the task explicitly asks to clean those excerpts.
- Prefer fixing generation rules or source data over editing generated output only.

## Search Guidance

- Prefer `gbrain` for semantic questions when the exact identifier is unknown.
- Use `rg` for exact strings, regexes, file globs, and known identifiers.
- Keep workspace boundaries explicit; this repo is `/Users/shane/Desktop/Anatomy/stotts_pirates`.

## Skill Routing

- When a request clearly matches an installed skill, use that skill before answering.
- If skill routing is ambiguous, clarify instead of forcing a skill.
- Common routing:
  - Product idea or pre-code brainstorm -> `office-hours`
  - Bug, error, 500, or broken behavior -> `investigate`
  - Ship, deploy, push, or create PR -> `ship`
  - Code review or diff check -> `review`
  - QA a live site -> `qa`
  - Visual or design audit -> `design-review`
  - Design system or brand setup -> `design-consultation`
  - Architecture review of a plan -> `plan-eng-review`
  - Docs after shipping -> `document-release`
  - Weekly retro or shipped-work summary -> `retro`
