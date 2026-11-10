# g3-caveat-note — post-run findings (2026-11-10)

Written after the run. The verdict in `g3-caveat-note_report.json` stands as
recorded: `no_pooled_verdict` (homogeneity check of pre-registration section 5
failed). Had the pooled verdict applied, the outcome would have been overlap,
i.e. the mitigation was not shown. Nothing below changes that.

## The contingency named in section 4 fired

Section 4 predicted the no-note arm at 0.30-0.80 and stated that a value below
0.30 would mean the fixture is too neutral and the probes need revision. The
measured no-note arm is 0.1033 (31/300). So the honest reading of this run is
not "the note does not work" but "on this fixture the base weave rate is too low
for the chosen n to resolve a difference of this size".

## Probe wording moved the measure more than the mechanism did

| Probe | Query | No-note rate | With-note rate |
|---|---|---|---|
| p1 | How are you today? | 0.05 | 0.03 |
| p2 | What should I have for lunch? | 0.09 | 0.08 |
| p3 | Do you like music? | 0.17 | 0.07 |

The spread across probes in the no-note arm (0.05 to 0.17) is wider than the
pooled difference between arms (4.3 percentage points). That is why the
homogeneity check failed, and it is the more useful finding of this run: for
this class of experiment, probes must be selected by a measured base rate, not
by intuition.

## What would be needed to resolve the observed difference

At the observed rates (0.060 against 0.1033), separation of the 95% Wilson
intervals is not monotonic in n, because match counts are integers: isolated
values such as n = 605 separate while n = 610, 612, 614 and 642 do not. Stable
separation begins at roughly 650 to 700 runs per arm, about 230 per cell against
the 100 used here.

Raising n after seeing the direction would be fitting the design to the result.
The correct path is a new pre-registration with a new `fixture_id`, citing this
run as the pilot it turned out to be, powered from the rates measured here, with
probes chosen by their measured base rate. This run stays published as it is.
