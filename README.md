# Initial-AI-assisted-SVA-generator-prototype
`sva-gen` is a Python prototype that uses LLMs to generate SystemVerilog Assertions from RTL code and validates them with Verilator for AI-assisted hardware verification research.
# sva-gen

LLM-powered SystemVerilog Assertion (SVA) generator for AI-assisted hardware verification.

This prototype reads a SystemVerilog RTL module and asks an LLM to generate structured SystemVerilog Assertions. It is designed as a small portfolio project for the TIMA Laboratory PhD position on next-generation AI-assisted hardware verification methodologies.

## Why this project fits the TIMA PhD position

The advertised PhD position focuses on AI-assisted hardware verification, formal verification, assertion-based verification, Transformer/LLM methods, and digital hardware design. This project directly touches that space by combining:

- Python tooling
- SystemVerilog RTL examples
- SystemVerilog Assertion generation
- LLM prompting and structured output
- Syntax validation using Verilator
- Evaluation of limitations and research next steps

It is not a complete research contribution. It is a focused prototype showing that I have tried to understand the problem practically before applying.

## What the tool does

Given a `.sv` RTL module, `sva-gen` produces:

1. A short natural-language summary of the module
2. SVA properties such as `assert property`, `cover property`, and `assume property`
3. A justification for each generated property
4. Optional syntax checking through Verilator

## What this project does not claim

This is important for honesty:

- The generated assertions are not guaranteed to be complete or semantically correct.
- Verilator checks syntax only; it does not prove the assertions formally.
- The tool does not replace a verification engineer.
- It works best on small, isolated RTL modules.
- It does not yet integrate commercial formal tools such as JasperGold or QuestaSim.

## Project structure

```text
sva-gen/
├── src/sva_gen/
│   ├── cli.py          # Command-line interface
│   ├── llm_client.py   # Claude API wrapper and structured response parsing
│   ├── parser.py       # Lightweight RTL sanity checks
│   ├── prompts.py      # Prompt templates for SVA generation
│   └── validator.py    # Verilator-based syntax validation
├── examples/
│   ├── fifo.sv
│   ├── arbiter.sv
│   └── uart_tx.sv
├── evaluation/
│   └── analysis.md     # Honest observations and limitations
├── pyproject.toml
├── .env.example
└── README.md
```

## Quick start

```bash
git clone https://github.com/<your-username>/sva-gen.git
cd sva-gen
pip install -e .
```

Create a local environment file:

```bash
cp .env.example .env
```

Then add your Anthropic API key to `.env`:

```bash
ANTHROPIC_API_KEY=your_api_key_here
SVA_GEN_MODEL=claude-3-5-sonnet-latest
```

Run the tool:

```bash
sva-gen examples/fifo.sv
```

Generated assertions are written to:

```text
outputs/fifo_assertions.sv
```

## Example output

```systemverilog
property p_push_when_full_no_change;
  @(posedge clk) disable iff (!rst_n)
    (push && full && !pop) |=> ($past(count) == count);
endproperty
assert property (p_push_when_full_no_change);
```

## Architecture

```text
SystemVerilog RTL
      |
      v
Lightweight parser
      |
      v
Structured LLM prompt
      |
      v
SVA JSON response
      |
      v
Verilator syntax check
      |
      v
Generated assertion file
```

## What I learned

The prototype helped me understand several important points:

- LLMs can generate plausible assertions for clean and well-commented RTL.
- Structured prompting is necessary to get machine-readable output.
- Syntax validity is easier to check than semantic correctness.
- Some valid SVA constructs are not fully supported by open-source validators.
- Real research needs formal-tool feedback, coverage analysis, and stronger evaluation datasets.

## Research directions

If extended into PhD research, the next steps would be:

1. Build a dataset of RTL modules with expert-written assertions.
2. Use commercial formal tools such as JasperGold or QuestaSim for deeper feedback.
3. Add iterative refinement where tool failures are sent back to the LLM.
4. Compare general LLMs with smaller models fine-tuned on RTL and SVA corpora.
5. Evaluate semantic quality using mutation testing, coverage, and formal proof results.

## Relation to the PhD application

I built this project because the TIMA PhD position asks for skills in Python, Verilog/SystemVerilog, LLMs, assertion-based verification, and formal verification concepts. This project is my practical attempt to connect those areas in a small but concrete way.

## License

MIT License. See `LICENSE`.

## Author

Aena Azhar
