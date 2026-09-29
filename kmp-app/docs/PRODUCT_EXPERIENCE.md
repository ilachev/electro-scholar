# Interactive learning experience

## Status and audience

This is the accepted product direction for the future ElectroScholar
interface. The current question-bank UI is the first technical slice and does
not yet implement the level of interaction described here.

The primary audience is modern students, including Generation Z learners who
expect direct manipulation, immediate feedback, and polished mobile
interfaces. This does not mean simplifying the subject or imitating a social
network. The product should make difficult electrical engineering observable
and explorable.

## Core loop

```text
predict -> change the circuit -> observe the effect immediately
        -> connect it to a formula -> explain the result
        -> verify against sources -> try another case
```

A learner should not complete a long sequence of forms before solving or
experimenting. The first screen of a learning workflow shows the problem,
circuit, or active experiment, not a marketing page.

## Interaction as explanation

Important objects support direct manipulation:

- tapping a switch changes its state;
- a slider or stepper changes an allowed component parameter;
- a probe can be dragged onto a node or branch;
- the timeline supports scrubbing, pause, and stepping;
- pinch or scroll zooms the circuit and drag pans the viewport;
- selecting a formula term highlights its component, net, or plot;
- selecting a component highlights the corresponding formula quantities;
- a parameter change updates numeric labels, formulas, phasors, and plots from
  the same state revision;
- an incorrect choice exposes a short explanation and a `Test in circuit`
  action;
- a source action opens the exact edition and locator when available;
- an `Ideal` / `Practical` segmented control reveals the effect of tolerances,
  losses, source impedance, conductors, and instruments;
- uncertainty appears as a range or distribution, not false precision.

Animation only communicates state change, direction, phase, dependency, or
causality. Decorative motion must not compete with the task. An animated
current indicator must not be presented as literal electron motion without an
explicit model explanation.

## Linked representations

Circuit, formula, plot, and prose are projections of one verified model:

```text
verified circuit graph
    |-- schematic layout
    |-- parameter controls
    |-- formula bindings
    |-- live values and probes
    |-- plots and phasors
    `-- source-backed explanation
```

The relationship is bidirectional. Circuit changes update the mathematics;
selecting a variable or formula term reveals its physical location. Values are
not copied manually between screens. Every projection consumes the same
revisioned state.

## Feedback

An answer result is more than a color and a correct/incorrect label. For the
selected choice, show:

1. the specific misconception or correct idea;
2. the smallest useful next reasoning step;
3. the linked formula or circuit region;
4. a verified interactive experiment when one exists;
5. an independent derivation and exact source locator;
6. an immediate way to try a nearby case.

Explanation uses progressive disclosure: concise reason first, then
derivation, sources, source comparison, and extended experiment. This preserves
pace without hiding rigor from an interested learner.

## Engagement without manipulation

Motivation should reflect subject mastery:

- a map of learned concepts and dependencies;
- visible skill progress rather than only question completion percentage;
- short topic challenges;
- comparison between initial prediction and experiment;
- review driven by actual misconceptions;
- saved experiments and custom parameter sets.

The product does not use mandatory streaks, artificial waiting, random rewards,
penalties for absence, infinite feeds, or unrelated retention mechanics. Scores
or achievements may exist only as secondary evidence of a genuinely verified
skill.

## Visual and interaction system

- The circuit or problem is the primary workspace, not a small image inside a
  decorative card.
- Compact panels use working-scale typography; hero typography is inappropriate
  inside an editor, quiz, or simulator.
- Panels are not nested inside decorative cards without a functional reason.
- Familiar commands use icons; unfamiliar icons have a tooltip and accessible
  name.
- Toggles represent binary state, segmented controls represent modes,
  sliders/steppers/inputs represent numbers, and tabs represent peer views.
- Circuit elements, toolbars, plots, and control regions use stable dimensions
  so live values do not shift the layout.
- A physical quantity uses the same semantic color across representations, but
  color is never its only identifier.
- The palette separates circuits, formulas, plots, warnings, and background
  instead of varying one dominant hue.
- Light and dark modes preserve semantic colors and fine-line legibility.

## Motion, sound, and haptics

- UI rendering should remain smooth while the solver runs independently of
  frame rate.
- A new state is never animated from a stale calculation result.
- Rapid parameter changes coalesce or cancel obsolete requests.
- `Reduce motion` replaces movement with instant transitions or fades without
  losing information.
- Haptics confirms a meaningful physical action: latching a switch, attaching
  a probe, reaching resonance, or making an invalid connection.
- Sound is optional, can be disabled without losing functionality, and is
  never the only result signal.

## Platform interaction

The same learning workflow must be complete on Android, iOS, macOS, Linux, and
Windows, while controls adapt to the device:

- touch: large hit targets, pinch, drag, long press, and haptics;
- mouse/trackpad: hover, wheel zoom, precise drag, and context actions;
- keyboard: focus order, shortcuts, and stepped parameter adjustment;
- screen reader: names for components, nets, states, values, and changes;
- stylus, share/export, and the system PDF viewer use narrow native ports when
  they provide concrete value.

`commonMain` owns learning state and action semantics. Native source sets
implement system capabilities without creating separate product logic.

## Accessibility and model honesty

- Every action works without relying on color, hover, or a complex gesture.
- Text scales without covering the circuit or neighboring controls.
- Formulas have a textual representation and semantic structure.
- Plots have labeled axes, units, accessible descriptions, and a tabular view.
- Every approximation, ideal component, and model limitation is available in
  the experiment context.
- Unsupported or non-converged states are explicit; the application never
  substitutes a plausible-looking result.
- The product is an educational tool and does not claim industrial accuracy or
  real-equipment safety certification.

## Performance

The main UI thread does not run OCR, LaTeX compilation, or numerical solving.
Long operations are cancellable and expose progress. Interactive experiments
prioritize:

1. never blocking user input;
2. stable UI geometry;
3. tagging every result with its request revision;
4. suppressing obsolete calculation results;
5. keeping physical results independent of graphics frame rate.

Numeric latency budgets are set after prototypes run on every platform, not
only the developer's machine.

## First experience slice

The first target-UX demonstration should be one complete problem, not a set of
unrelated screens:

1. The learner chooses an answer and confidence level.
2. The application explains the selected distractor.
3. `Test in circuit` opens the same verified circuit.
4. The learner operates a switch or changes resistance.
5. Circuit values, formula, and plot update together.
6. The learner compares ideal and practical models with a virtual instrument.
7. The learner opens the independent derivation and compares source treatments
   in their preferred language.
8. A short follow-up question checks whether the relationship was understood.

This workflow sets the bar for later slices. Isolated effects and screens that
do not form a learning loop are not considered complete interactivity.
