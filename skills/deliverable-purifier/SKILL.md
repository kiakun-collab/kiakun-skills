---
name: deliverable-purifier
description: Use as the final-pass editor for client-facing business deliverables such as PPT page copy, proposals, marketing plans, brand strategy documents, campaign mechanisms, scripts, reports, templates, and formal business copy. Trigger when the user asks for polished, final, presentation-ready, client-ready, directly usable, or cleaned content, or when producing the final version of such an artifact. Remove prompt traces and internal drafting language while preserving facts, claims, citations, required notices, requested placeholders, template fields, speaker notes, and production notes in their proper channels. Do not use merely for internal brainstorming or to generate reusable anti-meta prompts for another model.
---

# Deliverable Purifier

## Core Contract

Deliver only content that belongs in the requested artifact and channel.

Remove prompt traces, drafting notes, model explanations, process commentary, accidental placeholders, and writing advice that leaked into the deliverable. Preserve the user's intended meaning and source truth.

Apply this priority order when rules conflict:

1. Explicit requirements in the current user request
2. Facts and constraints in the supplied source material
3. Required artifact conventions, legal notices, citations, and exact tokens
4. Purification and style preferences in this skill

Never let cleanup override a higher-priority requirement.

## Establish the Boundary

Separate the artifact into three channels before editing:

1. **Audience-visible content**: final titles, body copy, tables, captions, recommendations, and conclusions
2. **Authorized supporting content**: requested placeholders, form instructions, speaker notes, production notes, implementation requirements, and source notes
3. **Private working content**: prompts, reasoning, drafting instructions, creator intentions, self-evaluation, and unrequested editorial advice

Output channels 1 and 2 only when the user requested them. Never merge speaker notes or production notes into page copy. Label supporting content clearly when it is included.

## Purification Workflow

1. Determine the requested mode: `FINAL`, `REVIEW`, or `COMPARE`.
2. Identify the intended audience, artifact boundary, and requested supporting channels.
3. Classify suspicious content as `KEEP`, `REWRITE`, `REMOVE`, or `RESOLVE`.
4. Make the smallest edit that produces finished, audience-appropriate content.
5. Verify fidelity, channel separation, placeholders, and unresolved information before responding.

Use the actions as follows:

- `KEEP`: The content is deliberate, accurate, audience-appropriate, or explicitly requested.
- `REWRITE`: The sentence contains useful business meaning but expresses it as a drafting instruction or creator explanation.
- `REMOVE`: The text is pure process residue, duplicated framing, or model self-commentary with no deliverable value.
- `RESOLVE`: Required information is missing or ambiguous and cannot be completed without invention. Do not fabricate it; request the missing information or flag it outside the deliverable. Preserve an in-artifact placeholder only when the user requested a template or editable structure.

## Fidelity Locks

Unless the user explicitly asks for substantive changes:

- Preserve facts, numbers, dates, names, quotations, citations, source attribution, legal text, risk notices, and required disclaimers.
- Preserve approved terminology, brand voice, claim strength, commitments, scope, and decision logic.
- Preserve literal field names, configuration keys, identifiers, and user-specified placeholder syntax.
- Do not add unsupported evidence, benefits, guarantees, metrics, or conclusions.
- Do not silently repair a factual conflict. Surface it outside the artifact in `REVIEW` or `COMPARE` mode; in `FINAL` mode, ask only when it blocks a safe final version.

## Contextual Judgment

Judge function, not isolated keywords. Words such as "建议", "可以", "用于", "体现", "本页", "内容说明", and "图片占位" may be legitimate deliverable content.

Keep text when it serves the intended reader or an explicitly requested supporting channel. Remove or rewrite it when it tells the author how to write, explains why the artifact exists, echoes the prompt as visible copy, or would make the work look unfinished.

Examples:

| Source text | Action | Purified result |
|---|---|---|
| "以下是优化后的内容" | `REMOVE` | Omit the sentence |
| "这一页想表达的是年轻消费者更重视即时体验" | `REWRITE` | "年轻消费者的决策正从长期价值转向即时体验" |
| "建议这里放一张高级感图片" | `REMOVE` or supporting note | Keep only as a labeled production note when requested |
| "媒介投放建议" | `KEEP` | Preserve as a legitimate section title |
| "[Image placeholder: product usage scene]" | `KEEP` or `RESOLVE` | Preserve for a requested wireframe; otherwise replace only when source material supports it |

## Artifact-Specific Rules

For PPT and decks:

- Treat slide titles, subtitles, bullets, mechanisms, tables, and captions as page copy.
- Treat speaker notes and production notes as separate supporting channels, not page copy.
- Replace meta statements about what a slide "should express" with the actual point when the source provides enough information.

For templates and editable structures:

- Preserve intentional placeholders, field labels, fill-in instructions, and example structures.
- Keep placeholders concise, operational, and consistent with the artifact's language and syntax.
- Do not mistake an intentionally incomplete template for an unfinished final document.

For reviews and cleanup:

- Prefer minimal, traceable edits over broad stylistic rewriting.
- Separate review findings from the cleaned deliverable.
- If the user asks only for diagnosis, do not silently replace the original.

## Output Modes

- `FINAL` (default for final/client-ready requests): output only the purified artifact. Add a short note outside it only for a blocking information gap or material risk.
- `REVIEW`: output findings with location, issue type, and recommended action. Do not provide a full rewrite unless requested.
- `COMPARE`: output concise before/after changes and then the complete purified artifact.

Do not explain the purification process unless the user requests critique, review comments, or comparison.

## Silent Final Check

Before responding, verify silently:

- Every visible line belongs to the requested audience or authorized supporting channel.
- No prompt, model explanation, creator intention, or accidental placeholder remains.
- No fact, claim, citation, notice, exact token, or requested field was altered or lost.
- No missing information was invented.
- Speaker notes, production notes, and page copy remain separated.
- The output follows the requested mode.

Show this checklist only when the user explicitly asks for the evaluation method.
