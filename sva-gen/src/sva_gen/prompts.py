"""Prompt templates for SVA generation.

The core engineering of this project lives here. The prompts constrain
Claude to produce structured, syntactically valid SVA in a specific
sub-set of the SystemVerilog Assertions language.
"""

SYSTEM_PROMPT = """You are a senior hardware verification engineer with 15 years of \
experience writing SystemVerilog Assertions (SVA). You read RTL code carefully, identify \
intended behaviour, and write concise, syntactically-valid assertions that capture that \
behaviour.

Your output is consumed by an automated pipeline. You must follow the structured format \
exactly. Do not include any text outside the requested JSON.

Constraints on the SVA you produce:
1. Use only IEEE 1800-2017 SVA syntax.
2. Each property must use the form: property p_name; @(posedge clk) ... endproperty
3. Disable the property under reset using: disable iff (!rst_n) - or whatever the active-low \
   reset signal is named in the module.
4. Use `|->` (overlapping implication) or `|=>` (non-overlapping) appropriately. Be \
   conservative - prefer simpler forms.
5. Do NOT use: `let`, `expect`, `cover sequence`, multi-clock properties, complex \
   sequences with `intersect`, `throughout`, `within`. Stick to a clean, readable subset.
6. Each property must come with: a short name, a one-sentence description of intent, \
   the SVA code itself, and a justification for why this property matters.
7. Aim for 4-8 properties per module. Quality over quantity. Cover: reset behaviour, \
   key state transitions, edge cases involving simultaneous events, and at least one \
   `cover property` to demonstrate liveness/reachability.

If the module is genuinely too complex to reason about, return an empty `properties` \
array and an honest explanation in the `notes` field. Do not fabricate."""

USER_PROMPT_TEMPLATE = """Here is a SystemVerilog module. Generate assertions for it.

```systemverilog
{rtl_code}
```

Return your output as a JSON object with this exact schema:

{{
  "module_name": "<the name of the module>",
  "summary": "<one paragraph in plain English describing what this module does>",
  "clock_signal": "<the name of the clock signal>",
  "reset_signal": "<the name of the reset signal, including active-low convention if any>",
  "properties": [
    {{
      "name": "<short snake_case identifier>",
      "description": "<one sentence describing what this property checks>",
      "kind": "<one of: assert | cover | assume>",
      "sva_code": "<the complete property declaration and the assert/cover/assume statement>",
      "justification": "<why this property is worth checking>"
    }}
  ],
  "notes": "<optional caveats, missing context, or honest limitations>"
}}

Output ONLY the JSON object. No surrounding markdown fences, no commentary."""


# Example included in-context to anchor the format. Keep it simple.
FEW_SHOT_EXAMPLE_RTL = """module example_counter (
    input  logic       clk,
    input  logic       rst_n,
    input  logic       enable,
    output logic [3:0] count
);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count <= 4'b0;
        else if (enable)
            count <= count + 1;
    end
endmodule"""

FEW_SHOT_EXAMPLE_OUTPUT = """{
  "module_name": "example_counter",
  "summary": "A 4-bit synchronous counter with asynchronous active-low reset and a clock enable. On every rising clock edge, if enable is high, count increments; otherwise it holds. Reset forces count to 0.",
  "clock_signal": "clk",
  "reset_signal": "rst_n (active-low, asynchronous)",
  "properties": [
    {
      "name": "p_reset_clears_count",
      "description": "After reset is asserted, count must be 0.",
      "kind": "assert",
      "sva_code": "property p_reset_clears_count;\\n  @(posedge clk) (!rst_n) |-> (count == 4'b0);\\nendproperty\\nassert property (p_reset_clears_count);",
      "justification": "Reset is the most important correctness property; if reset doesn't clear state, downstream logic is unsafe."
    },
    {
      "name": "p_enable_increments",
      "description": "When enable is high (and not in reset), count increments by 1 on the next cycle.",
      "kind": "assert",
      "sva_code": "property p_enable_increments;\\n  @(posedge clk) disable iff (!rst_n)\\n    enable |=> (count == $past(count) + 1);\\nendproperty\\nassert property (p_enable_increments);",
      "justification": "Core functional property: the counter must actually count when enabled."
    },
    {
      "name": "p_disable_holds",
      "description": "When enable is low, count must not change.",
      "kind": "assert",
      "sva_code": "property p_disable_holds;\\n  @(posedge clk) disable iff (!rst_n)\\n    !enable |=> (count == $past(count));\\nendproperty\\nassert property (p_disable_holds);",
      "justification": "Ensures the enable signal actually gates the counter; bugs here often appear as 'count always increments'."
    },
    {
      "name": "p_count_reaches_max",
      "description": "Count is able to reach its maximum value.",
      "kind": "cover",
      "sva_code": "property p_count_reaches_max;\\n  @(posedge clk) disable iff (!rst_n)\\n    (count == 4'hF);\\nendproperty\\ncover property (p_count_reaches_max);",
      "justification": "Coverage check: confirms the design's full range is reachable in testing."
    }
  ],
  "notes": "Counter wraps to 0 after 4'hF; depending on intent this may or may not be desired behaviour. A property could be added to check or assume the wrap."
}"""


def build_messages(rtl_code: str) -> list[dict]:
    """Build the message list for the Claude API, including the few-shot example."""
    return [
        {
            "role": "user",
            "content": USER_PROMPT_TEMPLATE.format(rtl_code=FEW_SHOT_EXAMPLE_RTL),
        },
        {
            "role": "assistant",
            "content": FEW_SHOT_EXAMPLE_OUTPUT,
        },
        {
            "role": "user",
            "content": USER_PROMPT_TEMPLATE.format(rtl_code=rtl_code),
        },
    ]
