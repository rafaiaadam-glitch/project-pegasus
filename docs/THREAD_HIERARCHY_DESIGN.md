# Hierarchical Thread Design for Dice Protocol

## Decision: Internal-first hierarchy, progressive UI exposure

For PLC, hierarchy should start as **mostly internal** and surface to users through synthesis/revision outputs before becoming a full navigable tree.

### Why this is the right v1.5 strategy

- It preserves v1 clarity (students are not forced into a complex tree immediately).
- It still gives real intelligence gains (better merge/split decisions and stronger continuity).
- It supports gradual product learning: expose tree controls after confidence and usability are proven.

---

## Psychological grounding

A thread is a reinforced semantic cluster across time. In Dice terms, reinforcement happens when multiple faces support the same conceptual core.

- **Growth**: repeated What/How/Who/Why evidence increases confidence.
- **Weakening**: incoming segments no longer match core facets; entropy rises.
- **Branching**: partial continuity + meaningful divergence creates a child thread.
- **Merging**: previously separate clusters reconnect under shared meaning.

This mirrors memory consolidation and hierarchical concept learning.

---

## Data model

```ts
interface Thread {
  id: string
  title: string
  parentId: string | null
  depth: number
  facets: ThreadFacets
  strength: number
  children: string[]
}
```

### Constraints

- `parentId = null` for root threads.
- `depth = 0` for roots; increment for descendants.
- `MAX_DEPTH = 4` to prevent over-fragmentation.
- `MAX_CHILDREN_PER_NODE` guardrail to keep trees readable.

---

## Lifecycle rules

### 1) Extend existing thread

Extend if segment similarity is high and divergence is low.

```text
if similarity(parent, segment) >= 0.6 && divergence < branch_threshold
  -> extend parent
```

### 2) Spawn child thread

Create child when content remains connected but introduces a distinct mechanism/domain.

```text
if similarity(parent, segment) >= 0.6 && divergence >= branch_threshold
  -> create child(parent)
```

### 3) Start new root thread

```text
if max similarity(all active roots, segment) < new_root_threshold
  -> create root
```

### 4) Merge or reattach

- Merge siblings when overlap is consistently high across key faces.
- Reattach a weak root under a stronger root when semantic containment is clear.

---

## Dice-aware hierarchy behavior

Hierarchy should align with abstraction depth:

- **Depth 0 (roots)**: strong `What` + `Why`
- **Depth 1**: `How` + `Where`
- **Depth 2**: `When` + `Who`
- **Depth 3+**: concrete cases/examples

Guardrail: if a node is dominated by only one face for too long, lower strength to avoid single-face drift.

---

## Product rollout plan

### Phase A — Internal hierarchy (recommended first)

- Store parent-child relationships and depth.
- Use hierarchy to improve continuity, summaries, and revision packs.
- Keep primary UI mostly flat, but show “related sub-thread” hints.

### Phase B — Guided visibility

- Add synthesis views that reveal tree snippets.
- Show merge events and branch rationale.
- Allow selective expansion (not full tree navigation yet).

### Phase C — Full thread tree UI

- Dedicated concept tree view.
- Node-level evidence and Dice profile.
- User controls for collapse/merge suggestions.

---

## Success criteria

- Higher cross-lecture continuity scores.
- Lower micro-thread fragmentation.
- Better revision recall quality (fewer disconnected notes).
- Measurable increase in synthesis density across lectures.

---

## Final recommendation

Implement hierarchy now in the engine/data model, but expose it gradually in UX.

In short: **internal first, visible tree second**.
