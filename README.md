```
█  █  ██  ███  █  █ ████  ███  ███    █  █ ███ ████
█  █ █  █ █  █ ██ █ █    █    █       █ █   █    █
████ ████ ███  █ ██ ███   ██   ██     ██    █    █
█  █ █  █ █ █  █  █ █       █    █    █ █   █    █
█  █ █  █ █  █ █  █ ████ ███  ███     █  █ ███   █

        a g e n t   =   m o d e l   +   h a r n e s s
```

The prescriptive half of the Agent Harness Maturity Specification.

The spec says what a level means. This says what to build to reach it.

**Status: pre-1.0.** Contracts track a draft spec whose anchors are not stable.

---

## What this is

Agent = model + harness. The harness decomposes into twelve primitives, and the
[spec](https://github.com/Mariano215/agent-harness-maturity) scores a system
against them 0 to 5. Scoring a system tells you where it stands. It does not
tell you what to build.

That is this repository. Twelve contracts, each stating what to build to reach
level 3 and what to build to reach level 4, phrased so a Python project on
OpenAI and a Rust project on a local model can both satisfy them without
changing stack. Plus the adapters you paste into a project's instruction file,
and the playbook for doing it to a codebase that already exists.

Mattei Systems designs, architects, engineers and full-stack develops solutions
using agentic AI. This is the build standard from that work, applied to our own
systems and to the ones we inherit. It is written from the builder's chair: every
requirement is something we have had to implement, and every contract carries a
`cost` field because someone who builds knows which lifts are cheap and which are
a refactor.

## What is in it

| | |
|---|---|
| `contracts.yaml` | The source of truth. Twelve primitives, requirements at level 3 and 4, each with the check that falsifies it. |
| `TRANSFORM.md` | Seven steps to apply this to a project that already exists. Start here. |
| `adapters/` | Instruction fragments to paste in: vendor-neutral, Claude Code, and a one-page brief for a chat with no filesystem. |
| `docs/harness-engineering.md` | Guides and sensors, the control-type axis that makes level 4 testable rather than intuitive. |

## Try it on a project

Nothing to install. Pick a project that actually calls a model, and give it an
hour.

**1. Baseline it.** Read `adapters/plain-prompt/brief.md`, score the twelve
yourself, and write `harness/baseline.txt` with a path or an explicit "looked in
X and Y, found nothing" behind every number. A score without evidence is an
opinion, and this file is what the whole transform is measured against later. If
you already run `gantry scan` or `gxproof score`, use that instead; neither ships
a release binary yet, so do not install a toolchain just to start.

**2. Decide what done means.** Write `harness/target.yaml`: twelve lines, each
one a target level or `na` with the reason. Most rows are 3. The trust layer is 4
if the work is client-facing or regulated. **Without this file the transform has
no terminating condition** and you will keep adding scaffolding forever.

**3. Drop in one adapter.** They are standalone; use one, not several.
`adapters/agents/AGENTS.md` is the default. Fill in every angle-bracket
placeholder with a real path. An unfilled placeholder is a rule you have not
adopted, so delete it or fill it.

**4. Add two sensors.** Take the level-4 `check` text from two contracts
literally and make them run. Start with whichever primitive your baseline scored
lowest that the workload actually exercises.

**5. Break them.** Deliberately violate each check, watch it go red, paste the
output into `harness/proof/01.md`. A check that has never failed has not been
shown to be capable of failing, and this step is what separates a 3 from a 4.

If you only do steps 1, 2 and 5, you have still learned more about the system
than a scan would tell you. Step 3 alone teaches you nothing: it adds a document.

`TRANSFORM.md` is the full seven-step version with the ordering rules, the stop
rule, and what to do when the scan understates your work.

## The `check` field is the point

Every requirement carries its falsifier. This is the spec's own test, *show me
what breaks when someone ignores this rule*, made a required field:

```yaml
  - key: durable_state
    targets:
      "3":
        requirement: >-
          Run state lives in a named location outside the model's context, is
          readable without running the program, and identifies the goal, the
          steps completed, the step in flight, and what remains. [...]
        check: >-
          Kill a run after at least one state-mutating step. Open the state by
          hand and answer, without the source, what it was doing and what is
          left. If you cannot, the state is a log.
```

A requirement whose check cannot be written is vapid by construction, and making
the field required surfaces that while authoring rather than in front of a
client. At level 4 the check must be runnable and must be able to fail.

The portability rule that keeps requirements from turning to mush: a requirement
constrains **a structural property of an artifact, never a technology**. "One
enumerable registry" is satisfiable by a Python dict, a zod object, an MCP
manifest or an OpenAPI document. "Use pydantic" is not portable. "Have good
schemas" is not a property.

## What this deliberately does not do

**It does not score.** Two scorers already exist:
[gantry](https://github.com/Mariano215/gantry) reads a repository statically and
caps at 3, and gxproof scores from a run ledger with the regulatory clause
attached. A third scoring path in this repository would be the failure mode. If
a level-inference rule appears in `contracts.yaml`, it is a defect.

**It does not restate the spec.** Contracts join upstream by `key`. Definitions,
N/A conditions, limits, severities and control types live there and are absent
here on purpose.
Restating them is where drift starts.

**It ships no toolchain.** No CLI, no package, no generator. A repository whose
pitch is "drops into any project, any language" cannot open by asking you to
install something. Adapters are hand-written, not generated: a `CLAUDE.md` and a
pasteable chat brief are two different rhetorics, and deriving both from one YAML
would mean putting both rhetorics into the YAML.

## Versions

Two numbers, and every adapter carries them in a footer:

```
harness-kit contracts 0.2.0 · spec 0.2.0-draft
```

`spec_version` is copied from upstream verbatim and never forked.
`contracts_version` is this repository's own, because contracts iterate faster
than spec prose. Eighteen months from now that footer is how you tell which
vintage is sitting in a client's `AGENTS.md`.

Downstream consumers (gantry, gxproof, the harness-review skill) keep their own
deliberately lossy condensations and cite the version they were last reconciled
against. `ci/consumers-cite-current-version.sh` reports staleness. It is a
report, not a sync tool: the condensations are lossy on purpose and generating
them would destroy the fit.

## License

`LICENSE` is CC BY 4.0 and covers `contracts.yaml`, `TRANSFORM.md` and `docs/`,
matching the upstream spec.

`adapters/LICENSE` is MIT. Adapter fragments are meant to be pasted into other
people's repositories, and nobody's counsel should have to reason about
attribution on a `settings.json` block.
