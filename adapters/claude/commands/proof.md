---
description: Write the proof document that closes a harness step
---

A step is not done because the feature works. It is done when an adversarial
case has been run and recorded.

Produce `harness/proof/NN.md` for step $ARGUMENTS with these sections, and do
not write any section from reasoning. Run the thing and paste what happened.

## 1. The claim
One sentence. What this step asserts is now true of the system.

## 2. The attack
The case that should fail. Not "here is the feature working", but the hostile
input, the tampered record, the killed process, the removed permission, the
deliberately broken registry entry. Include the exact command or fixture.

## 3. What happened
Verbatim output. The denial, the failing check, the blocked gate, the resumed
run. If the run was recorded, include the event ids.

## 4. What surprised you
Anything that failed for a reason nobody predicted. This section is the
steering loop and it is the most valuable part of the document. If it is empty,
say so explicitly rather than deleting the heading.

## 5. Conformance delta
Which primitives moved, from what to what, and the new overall level, which is
the minimum across applicable primitives and never the average. State N/A where
the workload does not exercise a layer, and name the property that makes it
inapplicable.

## 6. What is still a guide
Anything this step added as documentation with nothing enforcing it. Mark it
with the unenforced token in the instruction file too, followed by the id of the
check that would close it.

---

harness-kit contracts 0.2.0 · spec 0.2.0-draft
