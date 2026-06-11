# Image Lightbox Design

## Goal

Add a simple image preview for the Pilates wiki so users can tap any exercise image and inspect it at a larger size without losing their place in the exercise detail.

## Scope

Implement a single-image lightbox with a short caption. The caption shows the exercise title, page label, and image number, for example: `後卷 · p.24-25 · 圖 1`.

This change does not include image carousel navigation, pinch zoom, image download, annotation, or persistent state.

## User Interaction

- Clicking or tapping an image inside an exercise detail opens a full-viewport overlay.
- The overlay shows the selected image centered on a dark backdrop.
- The image scales down to fit the viewport while preserving aspect ratio.
- The overlay includes a close button.
- Users can close the overlay by clicking the close button, clicking the backdrop, or pressing `Escape`.
- Switching exercise filters, closing the mobile detail drawer, or changing the selected exercise closes the lightbox if it is open.

## Components

- `state.lightbox`: stores the open image state or `null`.
- `openLightbox(image)`: opens the overlay for one image.
- `closeLightbox()`: clears the overlay state.
- Lightbox DOM: one static overlay container in `site/index.html`, populated and toggled by `app.js`.
- Lightbox styles: added to `site/styles.css`, with responsive constraints for desktop and mobile.

## Data Flow

The existing `exercise.images` array remains the source of truth. During detail rendering, each image receives enough metadata to open the lightbox:

- image source path
- exercise title
- page label
- image index

When the user clicks an image, the handler stores those values in `state.lightbox` and re-renders or updates the overlay. Closing the overlay clears `state.lightbox`.

## Layout

Desktop:

- Backdrop covers the full viewport.
- Image max size is constrained to fit within the viewport, roughly `90vw` by `86vh`.
- Caption stays below the image.

Mobile:

- Backdrop covers the full viewport, including above the mobile detail drawer.
- Image max size is constrained to avoid horizontal scrolling.
- Close button remains reachable in the top-right corner.
- Caption remains short and does not wrap into a large block.

## Accessibility

- The overlay uses `role="dialog"` and `aria-modal="true"`.
- The close button has an accessible label.
- The enlarged image keeps descriptive alt text.
- `Escape` closes the overlay.
- Focus management is minimal: opening the lightbox focuses the close button, and closing returns control to the page. Full focus trapping is out of scope for this small static app.

## Error Handling

- If an image has no source, clicking does nothing.
- If the image fails to load, the browser alt text remains available and the user can close the overlay.
- Re-rendering due to filters, selected exercise changes, or mobile detail close clears the lightbox.

## Testing

Manual and Playwright checks:

- Desktop: clicking an exercise image opens the overlay and displays the large image.
- Mobile 390px: clicking an exercise image inside the detail drawer opens the overlay above the drawer.
- Close button closes the overlay.
- Backdrop click closes the overlay.
- `Escape` closes the overlay.
- The page has no horizontal overflow on mobile after opening and closing the overlay.
- Existing exercise filtering and mobile detail drawer behavior still work.
