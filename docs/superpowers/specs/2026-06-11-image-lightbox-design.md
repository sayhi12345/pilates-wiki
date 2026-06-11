# Image Lightbox Design

## Goal

Add a simple image preview for the Pilates wiki so users can tap any exercise image, inspect it at a larger size, and move between the other images for the same exercise without losing their place in the exercise detail.

## Scope

Implement an exercise-scoped image lightbox. The caption shows the exercise title, page label, current image number, and total image count, for example: `後卷 · p.24-25 · 圖 2 / 4`.

This change does not include pinch zoom, image download, annotation, cross-exercise navigation, or persistent state.

## User Interaction

- Clicking or tapping an image inside an exercise detail opens a full-viewport overlay.
- The overlay shows the selected image centered on a dark backdrop.
- The image scales down to fit the viewport while preserving aspect ratio.
- If the exercise has more than one image, the overlay includes previous and next controls.
- On touch devices, horizontal swipe changes the image. Vertical movement is ignored.
- On desktop, `ArrowLeft` and `ArrowRight` change the image.
- Navigation does not wrap: the previous control is disabled on the first image, and the next control is disabled on the last image.
- The overlay includes a close button.
- Users can close the overlay by clicking the close button, clicking the backdrop, or pressing `Escape`.
- Switching exercise filters, closing the mobile detail drawer, or changing the selected exercise closes the lightbox if it is open.

## Components

- `state.lightbox`: stores the open image group state or `null`.
- `openLightbox(exercise, index)`: opens the overlay for one image inside the selected exercise image group.
- `closeLightbox()`: clears the overlay state.
- `showLightboxImage(delta)`: moves within the open image group when the destination index is in range.
- Lightbox DOM: one static overlay container in `site/index.html`, populated and toggled by `app.js`.
- Lightbox styles: added to `site/styles.css`, with responsive constraints for desktop and mobile.

## Data Flow

The existing `exercise.images` array remains the source of truth. During detail rendering, each image receives an index that opens the lightbox with this metadata:

- exercise title
- page label
- image sources for the current exercise
- selected image index

When the user clicks an image, the handler stores those values in `state.lightbox` and re-renders or updates the overlay. Changing images updates only the current index. Closing the overlay clears `state.lightbox`.

## Layout

Desktop:

- Backdrop covers the full viewport.
- Image max size is constrained to fit within the viewport, roughly `90vw` by `86vh`.
- Caption stays below the image.
- Previous and next controls sit at the left and right sides of the viewport.

Mobile:

- Backdrop covers the full viewport, including above the mobile detail drawer.
- Image max size is constrained to avoid horizontal scrolling.
- Horizontal swipe works from the image area and overlay content.
- Previous and next controls remain reachable but compact.
- Close button remains reachable in the top-right corner.
- Caption remains short and does not wrap into a large block.

## Accessibility

- The overlay uses `role="dialog"` and `aria-modal="true"`.
- The close button has an accessible label.
- Previous and next controls have accessible labels and disabled states.
- The enlarged image keeps descriptive alt text.
- `Escape` closes the overlay. `ArrowLeft` and `ArrowRight` navigate when available.
- Focus management is minimal: opening the lightbox focuses the close button, and closing returns control to the page. Full focus trapping is out of scope for this small static app.

## Error Handling

- If an image has no source, clicking does nothing.
- If the image fails to load, the browser alt text remains available and the user can close the overlay.
- Re-rendering due to filters, selected exercise changes, or mobile detail close clears the lightbox.

## Testing

Manual and Playwright checks:

- Desktop: clicking an exercise image opens the overlay and displays the large image.
- Desktop: previous and next controls move within the selected exercise's images and become disabled at boundaries.
- Desktop: `ArrowLeft` and `ArrowRight` move within the selected exercise's images.
- Mobile 390px: clicking an exercise image inside the detail drawer opens the overlay above the drawer.
- Mobile 390px: swipe left advances to the next image, and swipe right returns to the previous image.
- Close button closes the overlay.
- Backdrop click closes the overlay.
- `Escape` closes the overlay.
- The page has no horizontal overflow on mobile after opening and closing the overlay.
- Existing exercise filtering and mobile detail drawer behavior still work.
