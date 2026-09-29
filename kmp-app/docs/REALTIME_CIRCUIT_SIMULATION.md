# Interactive circuit simulation

## Status

This is an accepted future direction. The simulator, `Simulation Model IR`,
`Simulation Scenario IR`, and runtime API are not implemented yet. A numerical
engine will be selected after a cross-platform prototype, license review, and
comparative tests.

The general interaction standard is defined in
[`PRODUCT_EXPERIENCE.md`](PRODUCT_EXPERIENCE.md).

## Learning goal

A learner should directly manipulate a verified circuit and immediately
observe the physically valid consequence:

- operate switches;
- change permitted component and source parameters;
- place probes on nodes and branches;
- inspect voltages, currents, powers, phasors, and time plots;
- move from an incorrect answer to an experiment that reveals the mistake;
- connect the result to a formula, derivation, and source.

Here, `real-time` means perceptually continuous interaction, not a hard
real-time guarantee. Physical model time, solver update rate, and UI frame rate
are separate quantities.

## Required physical realism

The simulator must support both ideal instructional circuits and behavior that
approximates a real laboratory setup.

No simulator reproduces reality completely. The application therefore does not
offer a vague `real` mode that hides assumptions. Every experiment declares its
fidelity, models, environmental conditions, validity range, and expected
accuracy.

Comparable profiles are planned:

1. `ideal`: ideal sources, conductors, switches, and lumped elements;
2. `practical`: representative tolerances, losses, internal impedances,
   leakage, and instrument loading;
3. `device`: specific component models from a verified source or data sheet,
   with operating limits;
4. `measured`: parameters and uncertainty calibrated against measurements of a
   specific laboratory setup or specimen.

A learner can compare `Ideal` and `Practical` profiles to understand why a
closed-form calculation differs from an instrument reading. This comparison is
part of the lesson, not a hidden solver setting.

As the practical profile grows, it should represent:

- resistor tolerance, temperature coefficient, power dissipation, and thermal
  drift;
- capacitor ESR, ESL, leakage, initial charge, and condition-dependent
  capacitance;
- inductor winding resistance, losses, and saturation;
- source internal resistance, current limit, ripple, and dynamics;
- switch on-resistance, leakage, delay, and mechanical bounce;
- nonlinear and temperature-dependent semiconductor models;
- connection resistance and parasitics when the physical implementation is
  known;
- instrument input impedance, capacitance, bandwidth, burden voltage, offset,
  noise, and accuracy;
- ambient temperature, initial conditions, noise, and parameter variation;
- maximum ratings and operation outside a model's valid range.

The pixel layout of a source diagram does not encode a wire's physical length,
material, or geometry. Wire parasitics must never be inferred from it. They
come from a separately verified physical model or measurement.

For tolerances and noise, the UI shows a range, distribution, or multiple runs
instead of false single-value precision. Monte Carlo and uncertainty
propagation are reproducible from a stored seed and distribution parameters.

## Data model

`Circuit IR` remains canonical topology and does not become a solver-specific
format. Realistic simulation uses two separate planned documents:

- `Simulation Model IR` binds components and connections to ideal, practical,
  device-level, or measured models, including provenance, validity ranges, and
  uncertainty;
- `Simulation Scenario IR` defines a particular learning experiment, controls,
  events, and probes over one selected model.

Both documents refer to the `document_id` and SHA-256 of a human-verified
circuit. A scenario contains:

- analysis type;
- operating state and switching events;
- numeric parameters and units;
- learner-adjustable overrides and their ranges;
- excitations and initial conditions;
- probes and observable quantities;
- time or frequency ranges;
- solver tolerances and resource limits;
- expected physical invariants;
- links to a question, distractor, claims, and `Learning Evidence IR`.

`Simulation Model IR` contains:

- fidelity profile and model version;
- component-to-model bindings;
- nominal values, tolerances, and distributions;
- parasitic or instrument components absent from the teaching diagram;
- thermal and environmental parameters;
- model source, license, producer, and confidence;
- allowed voltage, current, frequency, and temperature ranges;
- data-sheet or measurement-dataset references;
- review events and verification status.

Calculation results are derived data. A reproducible run manifest records the
circuit and scenario hashes, engine, version, and settings. UI frame streams,
plot history, and control positions do not belong in the read-only corpus.

## Circuit admission

Learner-facing simulation runs only on a `Circuit IR` with `human_verified`
status. Every participating component needs a supported model, unambiguous pins
and nets, and a numeric value with unit. An unknown component, ambiguous
junction, or unverified topology blocks publication instead of being replaced
by a heuristic.

The review tool may simulate a candidate for diagnosis, but must visibly
distinguish that result from an approved learning experiment.

## Delivery stages

### 1. Interactive DC

- resistors;
- independent voltage and current sources;
- ideal switches;
- DC operating point;
- node voltages, branch currents, and power balance;
- recalculation after a parameter or switch change.

This is the first useful slice for Kirchhoff's laws, equivalent sources, and
resistor networks.

### 2. Sinusoidal steady state

- RLC components and complex quantities;
- amplitude, frequency, and initial phase;
- phasors, impedances, and complex power;
- interactive frequency sweep.

### 3. Transients

- time-domain excitations and switching events;
- initial conditions for energy-storage elements;
- plots, scrubbing, pause, and stepping;
- batched samples for smooth playback without changing the integration step to
  match graphics frame rate.

### 4. Advanced models

Diodes, transistors, controlled sources, transformers, and custom models come
only after the linear core is stable. Distributed electromagnetic fields and
FEM are a separate domain system.

## Engine architecture

```text
verified Circuit IR + Simulation Model IR + Simulation Scenario IR
                              |
                              v
                    async SimulationEngine port
                       /       |       \
                 Android      iOS     desktop
                              |
                              v
                  samples, events, diagnostics
```

Heavy computation runs outside the UI thread. A new request cancels the prior
request or makes its result obsolete. Rapid slider changes are coalesced so
they do not queue stale runs. Every published result carries its input request
revision.

The shared contract contains no ngspice, JNI, Swift, or desktop API types. A
platform backend may use a native library or portable engine if it passes one
conformance suite. Each backend declares capabilities so the UI never offers an
unsupported mode.

ElectroScholar will not implement a full SPICE-compatible solver from scratch.
A proven engine with a compatible license and target-platform support is
preferred. A small transparent solver is acceptable for a constrained
educational subset or as an independent validator after comparison with
analytic solutions and a reference engine.

## Physics and numeric verification

Every mode receives a shared conformance suite:

1. analytically solvable fixtures and boundary cases;
2. Kirchhoff current and voltage residuals;
3. component-model equations;
4. power and energy balance where applicable;
5. unit, finiteness, and conditioning checks;
6. comparison with an independent reference engine;
7. the same fixtures and tolerances on every target platform;
8. practical and measured profile comparison with laboratory datasets;
9. sensitivity and Monte Carlo checks for declared tolerances;
10. reproducible reports containing model, engine, version, and parameters.

NaN, infinity, floating nodes, conflicting ideal sources, singular matrices,
and non-convergence are typed diagnostics. They are never changed to zero or
hidden from learners and reviewers.

## Learning integration

`Learning Evidence IR` may cite a human-verified simulation scenario as
independent evidence. After an incorrect answer, `Test in circuit` opens the
prepared experiment and highlights the quantity that refutes the selected
distractor.

An automatically generated scenario remains a `candidate` until a reviewer
checks topology, models, controls, probes, ranges, and explanation. One
numerical run cannot by itself make a question or answer `verified`.

Claims allow the same experiment to support source comparisons in multiple
languages without duplicating the physical model. Localized prose and notation
are projections of the scenario and its language-neutral quantities.

## Security and longevity

- Simulation works offline.
- Arbitrary SPICE directives and model files extracted from text are not
  executed without a separate trust model and sandbox.
- Runs have time, memory, sample-count, and circuit-size limits.
- User experiments are stored separately from the source corpus.
- Engines are replaceable; IR, units, diagnostics, and fixtures are durable.
- The simulator is an educational tool, not a real-equipment safety verifier.

## First vertical slice

1. Define `Simulation Model IR v1` and `Simulation Scenario IR v1` for a DC
   operating point.
2. Select five to ten human-verified resistive circuits with switches and
   sources.
3. Define the asynchronous engine port, capabilities, and typed errors.
4. Compare engine candidates by license, portability, size, determinism, and
   Android, iOS, and desktop integration.
5. Implement one complete experience: control -> solver -> probes -> overlay.
6. For that experience, compare ideal and practical profiles, including source
   resistance and a realistic virtual instrument.
7. Add analytic, KCL/KVL, and power-balance checks.
8. Connect the experiment to one distractor explanation and source-backed
   claim.
9. Measure latency and stability on every platform before expanding models.
