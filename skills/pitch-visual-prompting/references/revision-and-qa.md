# Revision and QA

Use this reference after generation, when refining a prompt, or when the user provides corrective feedback.

## Contents

- Pre-Generation Check
- Result Inspection
- Classify the Failure
- Repair Prompt
- Common Repairs
- Stop Conditions

## Pre-Generation Check

- Is the deliverable mode unambiguous?
- Does the prompt express one primary communication objective?
- Is every important claim represented by visible evidence?
- Does each reference have a specific role?
- Are fixed assets and structural invariants explicit?
- Is exact copy separated from paraphrasable copy?
- Is the image-to-text balance appropriate to the output mode?
- Are aspect ratio, destination crop, and whitespace specified?
- Are realism, scale, budget level, and camera character concrete?
- Does the avoid list target likely failures rather than generic negativity?

## Result Inspection

Check in this order:

1. **Meaning**: Can the intended idea be understood without explanation?
2. **Reference fidelity**: Were strong references actually loaded, style-only references withheld when appropriate, and each loaded reference used for its assigned role?
3. **Structure**: Are focal hierarchy, panel count, crop, scale, and object relationships correct?
4. **Behavior**: Are people doing the correct action at the correct stage?
5. **Brand fit**: Are palette, form, tone, and category conventions appropriate?
6. **Text**: Are required words accurate and unwanted words absent?
7. **Artifacts**: Check hands, faces, repeated people, malformed objects, signage, logos, and watermarks.
8. **Production plausibility**: Does the scene fit the stated budget, venue, materials, and operational reality?

Do not report success based only on dimensions or file creation.

## Classify the Failure

- wrong target or reference contamination
- missing strategic evidence
- incorrect object structure
- wrong behavior or event moment
- weak hierarchy or composition
- wrong realism, scale, or budget character
- excessive decoration or uncontrolled text
- inaccurate required text
- technical artifact or crop failure

Fix the dominant class first.

## Repair Prompt

```text
Edit this exact target image.

Accepted and frozen:
- [region/object/copy/style that is correct]

Highest-priority correction:
- [one observable change]

Permitted supporting adjustments:
- [only adjustments required to make the correction coherent]

Strictly preserve:
- [layout, copy, subject identity, camera, palette, aspect ratio, fixed assets]

Do not introduce:
- [likely regression or previous failure]

Outside the requested correction, keep the output nearly identical to the target.
```

## Common Repairs

### Reference was described but not actually used

- Pass the image to the model.
- Name its unique visual characteristics.
- Assign one role.
- Remove competing references when possible.

### One image cannot explain several actions

- Switch to equal visual actions or a multi-panel composition.
- Give every action a scene, subject, and outcome.

### Generated page is too formulaic

- Re-evaluate the page's actual claim.
- Change the composition family, not only colors or decoration.
- Vary hero size, image count, and evidence type according to the message.

### Scene looks too expensive or too cheap

- Define footprint, materials, staffing, visitor count, venue condition, and lighting.
- Replace vague quality adjectives with believable production details.

### Correct object loses a functional feature

- Split structure, decoration, material, and use-context invariants.
- State which zones must remain open, transparent, readable, uncovered, or mechanically plausible.

### Text changed during a local edit

- Include the exact target image only.
- Freeze all existing copy.
- Limit the change to spacing, weight, alignment, or the named replacement.
- If exact fidelity remains critical, move text outside the image-generation workflow.

## Stop Conditions

Stop repeating the same prompt when:

- the wrong reference is repeatedly selected
- exact long-form copy is the only failing requirement
- the model cannot preserve a fixed asset or object structure
- each correction causes larger regressions

Change the workflow: isolate the asset, simplify the prompt, split generation into components, or use native deck/UI/text tools for deterministic elements.
