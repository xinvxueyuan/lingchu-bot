# Design an Interface

Based on "Design It Twice" from "A Philosophy of Software Design": your first idea is unlikely to be the best. Generate multiple radically different designs, then compare.

## Workflow

### 1. Gather Requirements

Before designing, understand:

- [ ] What problem does this module solve?
- [ ] Who are the callers? (other modules, external users, tests)
- [ ] What are the key operations?
- [ ] Any constraints? (performance, compatibility, existing patterns)
- [ ] What should be hidden inside vs exposed?

Ask: "What does this module need to do? Who will use it?"

### 2. Generate Designs

Produce 3+ **radically different** approaches. Each must have a different constraint:

- Design 1: "Minimize method count - aim for 1-3 methods max"
- Design 2: "Maximize flexibility - support many use cases"
- Design 3: "Optimize for the most common case"
- Design 4: "Take inspiration from [specific paradigm/library]"

For each design, output:

1. **Interface signature** - types, methods, params
2. **Usage example** - how caller uses it
3. **What this design hides internally**
4. **Trade-offs of this approach**

### 3. Present Designs

Show each design with interface signature, usage examples, and what it hides. Present sequentially so user can absorb each approach before comparison.

### 4. Compare Designs

After showing all designs, compare them on:

- **Interface simplicity**: fewer methods, simpler params
- **General-purpose vs specialized**: flexibility vs focus
- **Implementation efficiency**: does shape allow efficient internals?
- **Depth**: small interface hiding significant complexity (good) vs large interface with thin implementation (bad)
- **Ease of correct use** vs **ease of misuse**

Discuss trade-offs in prose, not tables. Highlight where designs diverge most.

### 5. Synthesize

Often the best design combines insights from multiple options. Ask:

- "Which design best fits your primary use case?"
- "Any elements from other designs worth incorporating?"

## Evaluation Criteria

- **Interface simplicity**: Fewer methods, simpler params = easier to learn and use correctly.
- **General-purpose**: Can handle future use cases without changes. But beware over-generalization.
- **Implementation efficiency**: Does interface shape allow efficient implementation?
- **Depth**: Small interface hiding significant complexity = deep module (good). Large interface with thin implementation = shallow module (avoid).

## Anti-Patterns

- Don't produce similar designs - enforce radical difference
- Don't skip comparison - the value is in contrast
- Don't implement - this is purely about interface shape
- Don't evaluate based on implementation effort
