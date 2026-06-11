# Class Planner Design

## Goal

Add a teacher-facing class planner to the Pilates wiki. A teacher can browse the existing exercise library, add exercises to one ordered class plan, estimate timing, write teaching notes, reorder the sequence by dragging, and export or print the result.

The feature must keep the current GitHub Pages deployment model. It will run as static HTML, CSS, and JavaScript without accounts, a backend, or a database.

## Deployment Fit

GitHub Pages is suitable for this version because it publishes static files from the repository, and the planner can be implemented entirely in client-side JavaScript. Persistent planner data will be stored in browser `localStorage`, which is scoped to the site origin and persists across browser sessions.

This means the planner is local to the browser. It is not cloud sync. Clearing browser data can remove saved class plans, so the UI must encourage JSON export for important plans.

References:

- GitHub Pages static hosting: https://pages.github.com/
- GitHub Pages static file publishing: https://docs.github.com/articles/creating-project-pages-manually
- MDN `localStorage`: https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage

## Scope

Implement one active class plan stored locally in the browser.

Included:

- A planner mode alongside the existing exercise index.
- Add exercises from the existing exercise list and exercise detail.
- Add exercises to the end of a single ordered class sequence.
- Show the sequence as 1, 2, 3 ... N.
- Reorder the sequence by drag-and-drop.
- Add minutes per exercise.
- Add simple notes per exercise.
- Expand advanced fields per exercise:
  - teaching cues
  - apparatus setup notes
  - alternative exercise notes
- Show total planned minutes.
- Autosave the active class plan to `localStorage`.
- Export the plan as JSON.
- Import a JSON plan.
- Generate a short share link when the encoded plan fits in the URL hash.
- Show a clear fallback to JSON export when a plan is too large for a share link.
- Print-friendly class plan view.
- Desktop and mobile layouts.

Excluded from this version:

- User accounts.
- Student accounts.
- Scheduling appointments or bookings.
- Cloud sync.
- Multi-user editing.
- Notifications.
- Backend storage.
- Multiple saved class plans.
The first version does not divide a class into warmup, main training, integration, or stretching sections. The teacher controls sequencing directly through the ordered list.

## Core User Flow

1. The teacher opens the Pilates wiki.
2. The teacher browses or searches exercises using the existing muscle, tag, source, and search filters.
3. The teacher clicks `加入課表` from an exercise row or detail view.
4. The exercise is added to the active class plan.
5. The teacher opens `排課表`.
6. The teacher edits:
   - class title
   - target duration
   - exercise order
   - minutes
   - note
   - optional advanced fields
7. The planner autosaves after edits.
8. The teacher can print, export JSON, import JSON, or create a share link for short plans.

## Information Architecture

The app will have two primary modes:

- `動作索引`: the current wiki experience, with the existing muscle sidebar, exercise list, detail pane, tags, and image lightbox.
- `排課表`: the class plan editor and preview/export actions.

Desktop layout:

- Keep the current index structure.
- Add a header-level mode switch for `動作索引` and `排課表`.
- In index mode, add `加入課表` actions to exercise rows and the selected exercise detail.
- In planner mode, show the planner editor as the main work surface.

Mobile layout:

- Do not force the desktop three-column layout into mobile.
- Use a compact tab pattern:
  - `找動作`
  - `課表`
  - `預覽`
- `找動作` keeps the existing mobile exercise browsing behavior.
- `課表` focuses on editing exercise order, minutes, notes, and advanced fields.
- `預覽` focuses on print, export, import, and share actions.

This avoids the previous mobile failure mode where selecting an item requires scrolling to the bottom to see the result.

## Data Model

The planner stores one active class plan:

```js
{
  id: "class-...",
  title: "60 分鐘器械流動課",
  durationTarget: 60,
  items: [
    {
      id: "item-...",
      exerciseId: "beginner-roll-down",
      exerciseTitleSnapshot: "後卷",
      minutes: 5,
      note: "",
      cues: "",
      apparatusSetup: "",
      alternatives: ""
    }
  ],
  updatedAt: "2026-06-12T00:00:00.000Z",
  schemaVersion: 1
}
```

Rules:

- `exerciseId` links to the existing `PILATES_DATA.exercises` item.
- `exerciseTitleSnapshot` preserves a readable title if an imported plan references an exercise that no longer exists in the library.
- `minutes` is optional but, when present, must be a non-negative number.
- `durationTarget` is optional but, when present, must be a non-negative number.
- `items` order is the class order. The first item is shown as 1, the second as 2, and so on.
- Legacy imported plans may contain `sections` or `sectionId`; this version ignores those fields and preserves the imported item order.

## Data Flow

`site/data.js` remains the exercise source of truth. The planner stores only plan-specific data and exercise references.

Load flow:

1. Load `PILATES_DATA` from `site/data.js`.
2. Load planner JSON from `localStorage`.
3. If no saved plan exists, create a default plan.
4. If the URL hash contains a shared plan, validate it and ask before replacing local state.
5. Render the selected mode.

Save flow:

1. User edits planner state.
2. Update in-memory planner state.
3. Recompute total planned minutes.
4. Debounce writes to `localStorage`.
5. Show a saved or error state.

Export flow:

1. Serialize the active plan.
2. Download as a `.json` file.

Import flow:

1. User selects a JSON file.
2. Parse JSON.
3. Validate schema.
4. Resolve exercise references against `PILATES_DATA`.
5. Replace the active plan only after validation.

Share link flow:

1. Serialize the active plan.
2. Minify to a compact payload.
3. Encode into the URL hash.
4. If the encoded hash exceeds the configured length threshold, do not generate a link; show a message telling the user to use JSON export.

## Components

### Mode Switch

Adds `動作索引` and `排課表` navigation. It should be visible on desktop and mobile. Mobile can use a bottom tab bar if that keeps the layout clearer.

### Add To Class Controls

Exercise rows and exercise detail get an `加入課表` action. The action appends the exercise to the end of the current class plan.

The existing exercise filters and tag behavior remain unchanged.

### Planner Editor

Shows:

- class title input
- target duration input
- computed total duration
- ordered exercise list
- item controls:
  - minutes input
  - note input
  - drag handle for sorting
  - remove
  - expand advanced fields

Advanced fields are hidden by default to keep the list scannable.

### Preview And Print

Shows a clean lesson-plan view:

- class title
- target duration
- total planned duration
- exercises in order, numbered 1 through N
- minutes
- note
- apparatus setup notes
- teaching cues
- alternative notes
- optional exercise thumbnail

Print CSS hides navigation, search, filters, edit controls, and import/export controls.

### Import, Export, And Share

Actions:

- `匯出 JSON`
- `匯入 JSON`
- `產生分享連結`
- `列印`

Import must not silently overwrite local data when the file is invalid.

## Error Handling

- `localStorage` read fails: start with a default plan and show a non-blocking warning.
- `localStorage` write fails: show an error and recommend JSON export.
- Imported JSON cannot be parsed: show `檔案格式不正確`.
- Imported JSON has missing required fields: show `課表資料缺少必要欄位`.
- Imported plan references unknown exercises: keep the imported item with `exerciseTitleSnapshot` and label it as `動作庫中找不到`.
- Imported legacy plans with unknown sections: ignore section data and preserve item order.
- Share hash cannot be decoded: do not overwrite local data; show a warning.
- Share hash is too long to generate safely: disable share link generation and recommend JSON export.

## Accessibility

- Buttons have visible labels or accessible labels.
- Planner controls use native inputs and selects where possible.
- The bottom mobile tab bar uses button semantics and active state.
- Print view remains readable without color.
- Share/import/export error messages are visible text, not only color.
- Drag handles have visible text affordance. Keyboard reordering is deferred for this version.

## Testing

Manual smoke tests:

- Add an exercise from the list to the planner.
- Add an exercise from the detail pane to the planner.
- Switch to planner mode and see the item.
- Change minutes and confirm total updates.
- Drag an item to reorder the class sequence.
- Remove an item.
- Expand and edit advanced fields.
- Reload the page and confirm the plan persists.
- Export JSON and import it back.
- Import invalid JSON and confirm a clear error.
- Generate a share link for a short plan and restore it.
- Confirm a long plan asks the user to use JSON export.
- Print preview shows only the lesson plan.
- Mobile: use `找動作`, `課表`, and `預覽` without needing to scroll to the bottom to see the selected result.

Automated or scripted checks:

- `node --check site/app.js`
- If a planner script is added, run `node --check site/planner.js`.
- `git diff --check`
- Playwright desktop viewport:
  - planner loads
  - add exercise works
  - total duration updates
  - no console errors
- Playwright mobile viewport:
  - no horizontal overflow
  - tab navigation works
  - planner remains visible after adding an exercise

## Implementation Boundary

Keep the site framework-free. This project currently uses static HTML, CSS, and vanilla JavaScript; the planner should follow that pattern.

To avoid overloading `site/app.js`, implementation may add a focused `site/planner.js` module or equivalent plain script. The boundary should be:

- index/search/detail behavior remains responsible for exercise discovery
- planner behavior is responsible for plan state, persistence, import/export, share, and print state
- both layers use `PILATES_DATA.exercises` as the shared exercise library

## Open Decisions

No open product decisions remain for this version. Multi-plan management, account sync, class sections, and student scheduling are explicitly deferred.
