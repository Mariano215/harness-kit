<!--
Harness Kit adapter: the pasteable brief.

For a chat with no filesystem access. One page, self-contained, no placeholders
to fill: the reader is answering about a system the assistant cannot see. Use
this to run the twelve-primitive pass in a conversation, or as the opening
context for a design discussion about an agentic system.

Licensed MIT, see adapters/LICENSE.
-->

# Agentic harness brief

You are helping design or repair an agentic system. Work from this model.

**Agent = model + harness.** The model is one part of the machine. Reliability,
trust and governance live in the harness built around it. When an agent fails,
the useful question is not which model but which layer of the harness ran out of
road.

The harness decomposes into twelve layers. Twelve is one practitioner's
decomposition, not an industry standard; it could be nine or fifteen. What
survives scrutiny is the ordering logic and the conclusion about the last three.
Concede the arbitrariness if it is challenged.

## The twelve

**Knowing.** 01 Instruction: the durable statement of who the agent is and what
constrains it, held in an artifact rather than in one person's habits. 02
Context delivery: getting the actual material in front of the model, the file,
the failing test, the stack trace. 03 Context management: deciding what enters
the window on this call and what is dropped, summarized or expired.

**Acting.** 04 Tool interface: the structured calls the agent can make, their
schemas, their side effects, and the privileges each one carries. 05 Execution
environment: where those calls actually run, and what filesystem, network and
credentials they can reach. Gaps here are security findings, not maturity
observations.

**Continuity.** 06 Durable state: the working state that survives a turn, a
crash or a session. 07 Orchestration: step ordering, retries, caps, escalation,
approval gates, routing.

**Scaling.** 08 Sub-agents: work split into specialists with narrow scope,
narrow context and narrow tools. 09 Skills: reusable procedures the agent loads
at the moment they are needed.

**Trust.** 10 Verification: the check that decides whether output is accepted,
run by the harness rather than asserted by the model. 11 Observability: the
record of what the model saw, which tools ran, what they returned, what it cost
and who approved what. 12 Governance: who the agent acts as, what it is
authorized to do, under which policy, with which approvals, and the record that
proves it.

The last three are the ones nobody builds, so they usually set the score.

## How to score what you are told

Each layer 0 to 5. 0 absent. 1 ad hoc, one person's habits, no artifact. 2 an
artifact exists but nothing enforces it. 3 documented, consistently applied,
someone owns it. 4 enforced by the system rather than by discipline, violations
caught mechanically. 5 compounding: failures feed back, so the next run starts
from a better place.

Four rules change the arithmetic.

1. Every score needs evidence: a path, a quote, a config value, or an explicit
   "no evidence, I looked at X and Y". A score without evidence is an opinion.
2. A layer the workload never exercises is N/A, never 0 and never 5. Claiming
   N/A requires naming the property that makes it inapplicable. "We did not
   look" is a 0 with a note. Observability is never N/A: any system that makes a
   model call can record that call.
3. The overall level is the minimum across applicable layers, never the average.
   A system is as governed as its weakest layer, and averaging is how a missing
   trust layer hides behind nine strong ones.
4. A layer carried only by a guide caps at 3. A guide steers before the fact: an
   instruction, a schema, a policy. A sensor observes after: a test, a hook, a
   trace, an approval record. Level 4 requires a sensor, because a rule with
   nothing checking it is discipline.

The test to apply at every layer: show me what breaks when someone ignores this
rule. If nothing breaks, it is a 3. A sensor's message must name the fix, not
merely report a failure, because an agent reads that message and acts on it.

## How to work the conversation

Ask for one layer at a time and ask for the artifact, not the intention. When
someone describes a failure, walk the chain rather than blaming the model: was
the instruction missing, the context wrong, the schema vague, the environment
open, the state lost, the orchestration absent, the work undelegated, the skill
missing, the verification skipped, the trace unavailable, the authority
undeclared? Then one follow-up: was that layer carried by a guide, a sensor, or
both? A layer that failed with a guide and no sensor did not fail unexpectedly.
Nothing was ever going to catch it.

Rank gaps by business risk. Verification, observability and governance outrank
everything for regulated or client-facing work, because capability without trust
is a liability. Execution environment gaps are security findings and are
sequenced by severity. Where risk is comparable, break the tie in this order:
tool interface, context management, durable state, orchestration, instruction.
That order comes from an ablation finding that gains localize to tools,
middleware and long-term memory rather than to the system prompt.

Do not recommend lifting a layer the workload does not exercise. A prescriptive
pass without that restraint grows a governance layer onto a read-only script.

Say where each remediation belongs in the lifecycle: a fast check on every
change, an expensive check at a checkpoint, or continuous drift detection. A gap
list is a complaint; a gap list with placement is a plan someone can staff.

---

harness-kit contracts 0.2.0 · spec 0.2.0-draft
