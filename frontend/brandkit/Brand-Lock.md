# HandoffProof official identity

The user selected the supplied HandoffProof artwork. This implementation applies that identity; no replacement logo or new identity was generated.

- `public/assets/handoffproof-logo-original.webp` preserves the exact supplied file.
- `public/assets/handoffproof-logo.png` is a lossless PNG transcode. Pixel equality with the decoded original was verified. The supplied image is opaque RGB; no transparency was removed or invented.
- `public/assets/handoffproof-mark.svg` clips the original pixels to the H/path/pin for navigation and favicon usage. It embeds the full original PNG; it does not redraw the mark.
- Full artwork, including both taglines, appears on a warm light surface in the workspace header. Click it for a full-size, keyboard-accessible view.

Interface colors are implementation choices informed by the supplied artwork, not claimed exact brand samples: navy `#132b42`, blue `#225e91`, warm orange `#c98551`, cool gray `#f3f5f8`, white panels. Danger red and acceptance green convey explicit operational states. Acceptance never represents verified hazard resolution.

The interface uses the system sans-serif stack, with Inter when already installed. No external font request or invented claim about the raster logo's typeface is made. Typography, borders and native SVG interface icons are editable source code.

The Higgsfield brandkit and generate skills were consulted. The CLI was installed, but its account-readiness check failed. No Higgsfield generation/upload occurred, and no project records, credentials, source code or personal data were sent to it. CSS and deterministic asset handling implement the requested fallback.

The local brandkit state stores the supplied-logo lock and is ignored by Git. The official-logo input file is provenance metadata, not an API credential or an employee record.
