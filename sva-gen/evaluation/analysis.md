# Evaluation of sva-gen prototype

This document records what happened when I ran the prototype on three SystemVerilog modules. It is the honest part of this project - what the LLM did well, what it missed, what the tooling missed, and what the realistic next steps would be.

## Setup

- Three SystemVerilog modules of varying complexity: a parameterised FIFO, a round-robin arbiter, and a minimal UART transmitter (FSM-based).
- Prompt: the system prompt + structured JSON schema + one-shot counter example in `src/sva_gen/prompts.py`.
- Model: `claude-opus-4-7` via the Anthropic API.
- Validation: Verilator 5.048 `--lint-only -sv`, with width/style warnings suppressed (those are about the RTL examples I wrote, not the LLM's output).
- Single run per module, no retries.

## Headline result

| Module | Properties generated | Verilator syntax check |
|---|---|---|
| `fifo.sv` | 10 | PASS Passed |
| `arbiter.sv` | 8 | PASS Passed |
| `uart_tx.sv` | 8 | FAIL 2 errors on one property |

**25 of 26 properties syntax-checked cleanly. The one that didn't is a valid IEEE 1800 SVA construct that Verilator does not support.** See the UART section below - this is the most interesting finding.

## FIFO observations

The FIFO output is the clearest demonstration of what well-prompted LLMs can do on small modules.

**What worked beyond my prior:** Before running this, I expected the LLM to miss simultaneous push/pop edge cases - those are exactly where real FIFO bugs hide and where verification-engineer judgement is supposed to come in. It didn't miss them. The generated properties `p_push_when_full_ignored`, `p_pop_when_empty_ignored`, and `p_simul_push_pop_holds_count` cover precisely the three cases I'd want a senior engineer to call out:

```systemverilog
property p_simul_push_pop_holds_count;
  @(posedge clk) disable iff (!rst_n)
    (push && pop && !full && !empty) |=> (count == $past(count));
endproperty
```

This updates my prior on LLM capability for assertion synthesis. I had assumed LLMs would fixate on the most "obvious" behavioural properties (reset, single push, single pop) and miss the cases that matter. Claude with this prompt did not.

**What was honestly weak:** The notes section flagged:

> Data integrity (FIFO ordering - that popped data matches earlier pushed data in order) is not checked here; doing so robustly requires an auxiliary scoreboard or symbolic tracking model that is beyond a single straightforward SVA property.

This is exactly the correct caveat. A FIFO's most important property - that data comes out in the order it went in - requires a symbolic scoreboard, not a one-liner property. Claude flagged this rather than pretending to address it.

## Arbiter observations

The arbiter output contained the most idiomatic verification engineering of any module.

`p_one_hot_grant` reaches for `$onehot0(grant)` - the canonical SVA function for "at most one bit set." That's not what a model would produce by default; it's what someone who has read assertion methodology guides reaches for. Worth noting: the prompt did not mention `$onehot0`. Claude inferred it was the right tool from the design.

`p_grant_implies_req` uses bitwise reasoning across a one-cycle latency: `(grant & $past(req)) == grant`. Means: every bit set in `grant` must have been set in `req` last cycle. This is the kind of property that catches the most common arbiter bug - granting a requester that no longer requests.

The pair `p_no_req_no_grant` + `p_grant_when_req` is a deliberate safety/liveness pairing. Safety: "if no input, no output." Liveness: "if input, then eventually output." Real verification suites use this pattern.

**Honest weakness:** `c_all_requesters_granted` is hardcoded to N=4, the default. Claude noted this in its `notes` field. A parameterised version requires generate-loop constructs that are outside the requested SVA subset.

## UART observations - the most interesting finding

The UART transmitter exposed something I didn't predict: **the validator is the bottleneck, not the LLM.**

Of the 8 generated properties, 7 are syntactically clean and semantically plausible. The one that failed:

```systemverilog
property p_full_transmission;
  @(posedge clk) disable iff (!rst_n)
    (state == STOP_BIT) ##1 (state == STOP_BIT)[*0:$] ##1 (state == IDLE);
endproperty
cover property (p_full_transmission);
```

Verilator rejected this with:
```
%Error-UNSUPPORTED: Unsupported: Unbounded ('$') outside of queue or string operations
%Error: Consecutive repetition max count must be constant expression (IEEE 1800-2023 16.9.2)
```

**The property is valid IEEE 1800 SVA.** `[*0:$]` (zero or more consecutive cycles) is routine in commercial tools. JasperGold and QuestaSim accept it. Verilator does not - its SVA subset is incomplete.

Even more interesting, Claude's own notes flagged a related self-imposed limitation:

> Exact baud timing (each bit lasts exactly BAUD_DIV cycles) could be checked with a more elaborate counter-based property but was omitted to keep the property set clean and within the requested SVA subset.

So the model did identify the most interesting temporal property (exact bit duration), explicitly chose to scope down to fit the prompt constraints, and the simpler unbounded version it did emit was rejected by the open-source validator.

This points at a real methodological concern: **published LLM-for-verification benchmarks that use Verilator as the syntax checker will systematically under-report assertion validity.** Constructs the commercial tools accept are silently failed by the open-source approximation. Any such benchmark is biased low.

For a PhD project, this suggests a concrete contribution: **build an evaluation harness that uses commercial formal tools (JasperGold or VC Formal) via their command-line interfaces.** The infrastructure cost is not trivial but the methodological gain is significant.

## What I learned about prompting

Three observations from iterating on `prompts.py`:

1. **One in-context example is worth a page of constraints.** The few-shot counter module in the prompt has more effect on output style than the entire `Constraints on the SVA you produce` block in the system prompt.

2. **Asking for justification per property forces real reasoning.** Earlier versions of the prompt that requested only the SVA code produced shallower properties. Requiring a `justification` field per property visibly improved the depth of what was generated - Claude visibly thinks about *why* a property matters before writing it.

3. **The structured JSON schema almost completely eliminates output format issues.** Before adopting the strict schema, output frequently contained surrounding markdown fences, embedded commentary, or inconsistent field names. With the schema, parse failures dropped from frequent to near-zero across runs.

None of these observations are novel research - they are standard structured-prompting practice. They are noted here because they were necessary to get from "prototype that produces vaguely useful text" to "prototype that produces machine-checkable output."

## What this prototype does not demonstrate

- **Semantic correctness.** Properties are syntactically valid and look plausible to a human reader. I have not formally proven that any of them are sound, and I have not measured mutation kill rate (the standard quality metric for assertion sets). A real evaluation needs both.
- **Generalisation.** Three small modules is too few to generalise from. A meaningful evaluation needs dozens of designs across multiple complexity tiers.
- **Production utility.** This prototype is a developer aid at best - a starting point for a verification engineer to review and prune. It is not autonomous verification and the README is honest about that.

## What the real research direction looks like

If I were to extend this into PhD research, the most defensible four-year programme would be:

1. **Year 1**: Build a corpus of (RTL, gold-standard assertions) pairs from open-source designs with credible verification suites (e.g. OpenTitan, BlackParrot, lowRISC). Establish baseline LLM performance with mutation kill rate, formal completeness, and syntactic validity (against commercial tools, not Verilator).

2. **Year 2**: Develop a feedback architecture where a commercial formal tool reports counter-examples, vacuity, and coverage gaps back to the LLM for iterative refinement. Quantify improvement over single-shot baseline.

3. **Year 3**: Investigate whether a smaller transformer fine-tuned on the HDL+SVA corpus beats a larger general-purpose model at this task, and at what cost/quality trade-off.

4. **Year 4**: Validate on a real industrial verification flow (in collaboration with an EDA vendor or chipmaker) and publish.

The prototype here addresses approximately the first 5% of step 1.

## Honesty about scope

This took roughly 15 hours of focused work, split across building the Python pipeline, engineering the prompts, picking RTL examples, running the experiments, and writing this document. It is a portfolio piece intended to demonstrate that I have engaged with the problem space concretely before applying. It is explicitly not a research contribution.
