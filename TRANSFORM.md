# Transform

How to take an existing agentic project and move it toward the twelve
primitives. Seven steps. Every measurement step calls a tool that already
exists; this document adds no scorer of its own.

Read this before dropping any adapter in. Steps 3 and 4 are the ones people
reverse, and reversing them is how a project ends up with a beautiful
instruction file and a maturity of 2.

An agent can run this. So can a person. Where a step says "record", it means
write the file and commit it, because the transform's value is the diff between
step 1 and step 5, and an uncommitted baseline is not a baseline.

---

## 0. Precondition

The target is a git repository with a clean tree, and it is actually agentic:
something in it calls a model, through a provider SDK or an HTTP endpoint.

If nothing calls a model, every primitive is N/A and there is nothing to
transform. Stop and say so. Do not install a harness on a system that has no
agent in it.

Note the stack, the provider, and whether the workload is client-facing or
regulated. Those three facts decide the targets in step 2 and nothing else in
this document depends on them.

---

## 1. Baseline

You need a number before you change anything, with evidence behind every score.
There are two ways to get one and the second needs nothing installed.

**With a scorer.** `gantry scan . > harness/baseline.txt` reads the repository
statically and caps at 3, because a static read cannot see enforcement actually
firing. `gxproof score .` reads a run ledger and can award 4. Note that neither
publishes a release binary today: gantry is `cargo build` from a checkout,
gxproof is `uv tool install gxproof`. If you do not already have one, do not
install a toolchain just to start. Use the second way.

**By hand, which is the fallback and is not a lesser one.** Score the twelve
yourself against `adapters/plain-prompt/brief.md`, which carries the anchors and
the four rules that change the arithmetic. Write
`harness/baseline.txt` in this shape, one line per primitive:

```
primitive 04 Tool interface | 0 | looked in tools/, .mcp.json, the model call
                                  site in app/agent.py: no registry, tools are
                                  dispatched by name through a match statement
```

The format is the discipline: a score, then a path or an explicit "looked in X
and Y, found nothing". A score without evidence is an opinion, and the whole
transform is measured against this file later.

Commit it either way.

Where the two disagree, do not average them. The static read under-reads a
running system and over-reads a dead one. The telemetry number measured
something; the static number inferred something. Record both and say which is
which.

**The baseline is the only honest artifact in this whole procedure.** Everything
after it is work you did, and work you did is easy to overrate. Commit the
baseline before you touch anything.

---

## 2. Scope

Write `harness/target.yaml`. Twelve lines. Each primitive gets either `na` with
the property that makes it inapplicable, quoted from the spec's `na_condition`,
or a target level.

```yaml
# harness/target.yaml
instruction:           3
context_delivery:      3
context_management:    3
tool_interface:        4
execution_environment: 4   # security severity, sequenced first, see step 4
durable_state:         3
orchestration:         3
sub_agents:            na  # no split in the work: one procedure, one caller
skills:                3
verification:          4
observability:         4
governance:            4
```

3 for most. 4 for the trust layer, 10 through 12, whenever the work is
client-facing or regulated. 4 for tool interface and execution environment
whenever the agent can write to anything shared.

**This file is the definition of done.** Without it, "transform" has no
terminating condition and this kit degenerates into a scaffolding generator.
When every row is met or explicitly deferred with a reason, the transform is
over. Not before, and not after.

**The stop rule.** Do not lift a primitive the workload does not exercise. It is
in the spec, and it still needs saying here, because a prescriptive document
without it will grow a governance layer onto a read-only local script. An `na`
row is a finished row.

---

## 3. Insert the guides

Copy one instruction adapter into the target and fill in every angle-bracket
placeholder with a real path or command:

- `adapters/agents/AGENTS.md` for anything vendor-neutral. This is the default.
- `adapters/claude/CLAUDE.md` for a Claude Code project, along with
  `settings.json` and `commands/proof.md` from the same directory. Standalone;
  use one or the other, not both.
- `adapters/plain-prompt/brief.md` when there is no repository to write into and
  the work is happening in a conversation.

A placeholder left unfilled is a rule that has not been adopted. Delete the rule
or fill it in; do not ship the angle brackets.

**Say this out loud before moving on: this step moves nothing above 2.** The
adapters are guides, and a layer carried only by a guide caps at 3, and it does
not even reach 3 until the rules are consistently applied and owned. Writing
rules down is the cheap half. If the transform stops here, the honest report
says the project acquired documentation.

Every rule you keep and cannot yet back carries the unenforced token followed by
the id of the check that would close it, on the rule's own line. Those markers
are the work list for step 4, and `gantry scan` reads them out of `CLAUDE.md`,
`AGENTS.md` and `.cursorrules` for free.

---

## 4. Insert the sensors

This is the step that moves numbers.

**Order.** Execution environment first whenever the baseline shows a committed
credential, or an open shell tool with no sandbox configuration. Those are
security findings and they are sequenced by severity, not by expected gain.
Everything else follows the spec's remediation order:

1. tool interface
2. context management
3. durable state
4. orchestration
5. instruction

Verification, observability and governance are sequenced by the business risk in
`target.yaml`: for regulated or client-facing work they come before the list
above, because capability without trust is a liability.

**What a sensor is here.** One per level-4 `check` in `contracts.yaml`. Take the
check text literally: it is written to be runnable. Give each one this shape,
borrowed from a working implementation:

```json
{
  "id": "no-secret-in-tracked-files",
  "kind": "computational",
  "placement": "pre_integration",
  "blocking": true,
  "check": "<the command, exit non-zero on violation>",
  "fix": "<what to do about it, written for an agent to read and act on>",
  "negative_control": ["<input that must make the check fail>"]
}
```

`kind` is computational (deterministic, cheap, every change) or inferential (LLM
judgment, slow, checkpoints only). `placement` is pre_integration, checkpoint,
or continuous. `blocking` false is a sensor that reports and does not gate, and
it does not reach 4.

The `fix` field is not documentation. An agent reads that message when the check
fails and acts on it, so a message that names the fix is worth more than one
that names the failure.

`negative_control` is required and is used in step 5. A check with no negative
control cannot be proven, and unproven is exactly the 3-to-4 boundary.

**Wiring.** Each sensor is named in two places: the CI configuration, and the
instruction file on the rule it carries, as `enforced by` followed by the check
id in backticks. Anything still unbacked keeps its unenforced token. This is not
decoration; it is what makes the transformed repository legible to the scanner
without any extra work.

---

## 5. Prove

Re-run the scan and diff it:

```
gantry scan . > harness/after.txt
diff harness/baseline.txt harness/after.txt
```

Then the step everyone skips. **For each sensor added, run its negative
control**: break the thing deliberately, watch the check go red, and paste the
output verbatim. Write `harness/proof/NN.md` per the structure in
`adapters/claude/commands/proof.md`: the claim, the attack, what happened, what
surprised you, the conformance delta, and what is still a guide.

A check that has never been observed failing has not been shown to be capable of
failing. That is not pedantry: a check with an inverted condition, a typo in a
path, or a grep that silently matches nothing will sit green forever and look
exactly like a working control.

**The scan delta is the weakest of the three artifacts, and you should expect it
to understate the work.** A static read scores from conventional paths: `tests/`
for verification, `logs/` or `telemetry/` for observability, `.mcp.json` for
tools. A real harness at an unconventional path scores 0 with an honest "looked
in X and Y, found nothing" behind it. The first run of this playbook against a
Python bot moved one primitive on the scan while four blocking sensors, a
chokepoint and a structured run record went unrecognised.

Do not rename things to please the scanner. A number obtained that way is a
compliment rather than a measurement, and the scanner's own probe list is
documented as conventions other repositories use, never as a house layout to
conform to. When the scan misses a real control, that is a probe to file
upstream, and the negative controls are what carry the proof in the meantime.

**Three artifacts prove the transform, never one number:**

1. the scan delta against the committed baseline,
2. one negative-control run per sensor added,
3. every row of `target.yaml` met or explicitly deferred with a reason.

A scan that moved 0 to 3 with (2) empty means files were added, not controls.
Say that in the report if it happens.

---

## 6. Review

Run the inferential pass. The `harness-review` skill is the one built for this,
and any capable model working from `adapters/plain-prompt/brief.md` will do.

The static scan cannot see: a tool schema that exists and is vague, a sub-agent
that exists for show, a verification step that runs and gates nothing, an
instruction file whose rules contradict the code. Those are judgments and they
need a reader.

Where the review and the scan disagree, the review wins on substance and the
scan wins on existence. The scan found a file; the review read it.

---

## What this does not do

It does not score. Two scorers exist and a third would be the failure this kit
was built to avoid. `contracts.yaml` states requirements; `gantry scan` and
`gxproof score` decide levels; the spec decides what a level means.

It does not make the project safe. Primitive 05 gaps are security findings, and
this document sequences them first without pretending that sequencing is
remediation.

It does not finish. Level 5 is compounding, and nothing in here produces it. A
failure that becomes a check, a near miss that becomes a negative control, a
correction that becomes a skill: those happen after the transform, in the
ordinary course of running the system, or they do not happen at all.

---

harness-kit contracts 0.1.0 · spec 0.1.0-draft
