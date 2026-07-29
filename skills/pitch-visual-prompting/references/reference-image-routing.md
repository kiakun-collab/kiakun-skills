# Reference Image Routing

Use this reference whenever the user supplies one or more images. Decide whether the model needs the actual pixels before writing the prompt or choosing generate versus edit/composition tooling.

## Decision

For each image ask:

1. Must the output preserve or replace a specific identity, object, geometry, composition, pose, logo, package, character, or fixed asset?
2. Would the result be considered wrong if the model saw only a textual description of the image?
3. Is the user asking for “this exact thing,” “replace X with this,” “keep this,” “use my model,” “turn this into,” or “based on the uploaded object”?

If any answer is yes, choose `load`.

If the image contributes only style, color, material mood, lighting, brushwork, or camera character, choose `inspect-only` by default. Translate the relevant traits into the prompt and generate a new subject without the pixels.

If the image is a screenshot, slide, document, or moodboard used only to provide copy, strategy, facts, or requirements, choose `extract-only` unless its layout or visual identity must be preserved.

## Must Load

Load the actual image pixels for:

- replacing a person, face, character, product, prop, background, or object with a supplied reference
- keeping the same person or character across scenes
- preserving an exact product silhouette, packaging system, logo, artwork, texture map, or decoration placement
- preserving a target image while changing only one region
- carrying over a specific pose, camera composition, spatial arrangement, or scene structure
- combining multiple supplied subjects or assets into one image
- turning an uploaded 3D model design into a believable physical product, installation, toy, package, or manufactured object
- reconstructing or closely adapting a supplied slide, poster, UI, or visual system when its spatial structure matters

For “replace the person on the left with my character,” load both the target image and the supplied character image. Assign the target as the scene/composition reference and the character as the identity/appearance reference.

For “make a physical object from my uploaded 3D model,” load clear model renders that preserve silhouette and geometry. Prefer front, side, and three-quarter views when available. If the user supplied only a `.glb`, `.obj`, `.fbx`, or similar 3D file, render useful views first with an appropriate 3D tool; image models cannot reliably infer the design from an unrendered file path.

## Usually Do Not Load

Prefer `inspect-only` for:

- “use this color mood on a completely new campaign”
- “make a new subject in this photographic style”
- “use this material and lighting language”
- broad moodboards where no depicted subject should be repeated
- competitor references where subject, composition, trade dress, or protected assets must not leak into the output

Loading style-only images can cause unintended subject, composition, or brand leakage. Load them only when the style is difficult to verbalize and fidelity outweighs contamination risk; explicitly instruct the model to copy only the named style traits.

## Multi-Reference Rules

- Assign one primary role to every loaded image.
- Pass every identity-critical reference needed to complete the transformation.
- Remove redundant or conflicting references.
- State which source controls identity, geometry, scene, pose, composition, material, and fixed assets.
- When two references disagree, declare the priority order.
- Do not replace strong pixel references with prose summaries.

## When Uncertain

Infer from verbs and acceptance criteria. Ask one short question only when the choice would materially change the result:

“Do you want this exact subject/object preserved, or only its visual style applied to a new subject?”

Default to `load` only when the user's wording clearly requires identity, replacement, geometry, or direct preservation.
