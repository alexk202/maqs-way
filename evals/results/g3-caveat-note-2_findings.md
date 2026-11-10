# g3-caveat-note-2 — post-run findings (2026-11-11)

Written after the run. The verdicts in `g3-caveat-note-2_report.json` stand as
recorded: every per-probe verdict is overlap, and `overall_claim.made` is false
with code `none_separated`. Nothing below changes that.

## What the run answers

Calibration fixed what the pilot could not resolve: probes were selected by a
measured base rate in the OFF arm only, which raised it from 0.05-0.17 in the
pilot to 0.50-0.97 here, and run sizes were derived from those rates to detect a
10 percentage point gap. At that power, no probe separated. Two probes show a
small reduction under the note and one shows a small increase, all within the
intervals. Together with the pilot this is consistent evidence that the caveat
note has no large effect on this fixture with this model.

| Probe | Calibrated OFF rate | n per arm | With note | Without note | Gap | Verdict |
|---|---|---|---|---|---|---|
| k04 "Tell me something interesting." | 0.967 | 117 | 0.974 | 0.983 | -0.9 pp | overlap |
| k06 "I'm feeling tired today, any advice?" | 0.600 | 388 | 0.479 | 0.523 | -4.4 pp | overlap |
| k05 "Can you tell me a short story?" | 0.500 | 390 | 0.533 | 0.472 | +6.2 pp | overlap |

For MAQS the consequence is narrow and concrete: item G3 keeps its current
wording, and now there is a measurement behind that, not only an argument.

## Three limitations, each a lesson for the next fixture

**1. The selection rule aimed at the ceiling.** Ranking candidates by the
highest measured base rate selected k04 at 0.967, where the OFF arm already
weaves in almost every answer, so there is no room left to demonstrate
suppression. The most informative probe sits near 0.5, not near 1.0. A future
fixture should select for a target band, for example 0.40 to 0.60, rather than
for the maximum.

**2. Truncation is unbounded relative to answer length.** On k05, 46 of 390
answers in the with-note arm and 52 of 390 in the without-note arm reached
`max_tokens` = 512. A story cut short may end before the model would have
reached the stored content, which biases that probe's rate downward and does so
unequally between arms. k05 is also the only probe with a reversed direction, so
its +6.2 pp is the least trustworthy of the three. A future fixture should either
raise the limit for open-ended probes or exclude truncated answers under a rule
fixed in advance.

**3. Two of the pre-registered predictions failed.** Section 7 expected one or
two probes to separate; none did. It expected the best candidate to calibrate
between 0.25 and 0.65; it came out at 0.967. The conclusion of the run is
unaffected, but the predictions were wrong and are recorded as wrong.

## Known limitation of the harness

The signed runner cannot resume a partial run. The first attempt at the main
stage was cut off by an external timeout after 1514 of 1790 generations; no
partial data was committed and the stage was repeated in full with the same
deterministic seeds. Resumption is not implemented and is not needed for a run
of this size, but it is a real cost for anything larger.

## Why the work stops here

Two runs under separate pre-registrations point the same way: no large effect.
A third run would be searching for an effect rather than testing for one. If the
question is taken up again, it should be with a different mechanism or a
different item, not with more runs of this one.
