---
name: pitch-visual-prompting
description: Build, refine, and quality-check reusable image-generation prompts for multi-brand creative pitches and campaign proposals. Use when Codex needs to turn a brief, strategy, slide, reference image, brand system, event concept, product idea, UI flow, social-content concept, or revision request into an executable prompt for full-slide images, pitch-deck visual assets, realistic activation scenes, product or merchandise mockups, app/UI visuals, social-content samples, multi-panel compositions, or controlled image edits.
---

# Pitch Visual Prompting

## Objective

Turn a pitch brief into a model-ready visual prompt that makes the strategic idea visible. Keep the workflow brand-agnostic: derive every color, tone, audience, product, IP constraint, and visual convention from the current brief and references.

Do not hardcode any past client, campaign, palette, platform, or IP into the output.

## Core Workflow

1. Determine the requested deliverable before writing the prompt.
2. Extract the communication goal, audience, required evidence, brand variables, reference roles, immutable content, and prohibited content.
3. Decide whether each supplied image must be loaded into the image model, inspected only, or used only as an information source.
4. Choose one output mode and one primary composition pattern.
5. Map each important claim or action to something visible in the image.
6. Assemble a concise prompt from only the relevant modules.
7. Check reference fidelity, text risk, hierarchy, realism, and unwanted additions.
8. For revisions, freeze correct regions and describe only the required delta.

Read [intake-and-routing.md](references/intake-and-routing.md) when the task type, reference roles, or output mode is unclear.

## Select an Output Mode

- **Full-slide image**: Generate the complete pitch page, including layout, copy, and embedded visual evidence.
- **Deck visual asset**: Generate a photo, render, collage, product shot, or scene for placement in an editable deck. Default to no visible text.
- **Activation or environment scene**: Show how a campaign, retail, event, hospitality, exhibition, or public-space idea exists in reality.
- **Product or prop mockup**: Preserve the product structure, materials, decoration zones, scale, and use context.
- **App, UI, or social sample**: Make the intended user action and resulting state visible in a credible product or content format.
- **Multi-panel composition**: Give every panel an independent purpose, crop-safe composition, and explicit separator structure.
- **Controlled edit**: Preserve the accepted image and change only the named region, attribute, object, copy, or aspect ratio.

Do not mix full-slide generation with asset generation. If the deliverable is an editable deck, generate assets without text and keep copy in native deck objects. If the user explicitly wants a complete slide image, keep the amount of model-rendered copy proportional to the model's reliability.

Read [pitch-visual-patterns.md](references/pitch-visual-patterns.md) only when choosing a composition or visual evidence pattern.

## Assign Reference Roles

Give every reference one explicit role:

- content source
- layout reference
- visual-style reference
- brand-system reference
- object or character structure reference
- scene or camera reference
- fixed asset that must remain unchanged

Do not tell the model to “refer to all images” without assigning roles. State what to copy, what to reinterpret, and what to ignore from each reference.

Route each supplied image as one of:

- **Load**: Pass the pixels to the image model when identity, geometry, composition, a fixed asset, or an explicit replacement must carry into the result.
- **Inspect only**: View the image, translate its style, material, lighting, palette, or camera language into words, and generate without the pixels when the subject should not carry over.
- **Extract only**: Read copy, requirements, or factual content from the image without using it as visual context.

Always load strong references for tasks such as replacing a person with a supplied character, placing an exact product or logo into a scene, preserving a subject or composition, or turning an uploaded 3D model design into a physical object visualization. If the source is a 3D file rather than a renderable image, first obtain useful rendered views and pass those views to the image model.

Do not load an image merely because it was uploaded. Style-only references can contaminate the new subject or composition when passed as pixels.

Read [reference-image-routing.md](references/reference-image-routing.md) whenever any image reference is supplied.

## Build the Prompt

Include only sections that affect the output:

1. use case and asset type
2. primary communication objective
3. reference-image roles
4. brand and audience context
5. scene, subject, action, and moment
6. composition, hierarchy, and crop behavior
7. medium, camera, materials, lighting, and palette
8. visible-text contract
9. constraints and avoid list
10. output ratio or dimensions

Use concrete visual instructions. Replace vague requests such as “premium,” “more impactful,” or “make it creative” with observable choices: scale, camera distance, material quality, density, whitespace, number of people, lighting contrast, image-to-text ratio, and focal hierarchy.

Read [prompt-modules.md](references/prompt-modules.md) when composing the final model prompt.

## Handle Visible Text

Treat visible text as a separate reliability decision:

- For visual assets, set `Text: none` unless text is intrinsic to the requested object.
- For full-slide images, distinguish exact copy from paraphrasable copy.
- Keep exact copy limited to essential titles, labels, codes, prices, or calls to action.
- Preserve exact copy in its original language and punctuation.
- Define an authorized visible-text inventory. Require every unspecified author name, metadata field, decorative slogan, screen label, and environmental sign to remain blank, abstract, or unreadable.
- If exact long-form copy is mandatory, warn that image-only generation cannot guarantee perfect text. Recommend a hybrid deck workflow unless the user explicitly accepts the risk.
- Never claim exact text fidelity without inspecting the generated result.

## Revise Without Regressing

For a revision, state:

- the exact target image
- accepted regions to preserve
- the single highest-priority change
- permitted secondary adjustments
- forbidden changes

Do not redesign the entire image when the user asks for a local correction. If the model uses the wrong reference or changes frozen content, stop and re-anchor the target before another generation.

Read [revision-and-qa.md](references/revision-and-qa.md) for repair prompts and validation checks.

## Output

When the user asks only for a prompt, return:

1. a short interpretation of the visual objective
2. the executable image-generation prompt
3. the reference-role mapping, when references exist
4. a compact risk note only when text, IP fidelity, or missing assets create material risk

When the user asks for the image itself, use the prompt with the image-generation tool they selected or the appropriate available image tool. Inspect the result against the brief before reporting success.
