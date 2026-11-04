# Industry Negative-Pattern Pack · Construction (load through the `patterns` field of a construction profile)

> General negative patterns are in `negative-patterns.md`; this pack contains only misjudgments specific to the construction industry. ID prefix `NP-CON-`.
> To use it, create a profile that extends `generic-zh` or `generic-en` and set `"patterns": ["negative-patterns.md", "profiles/construction.patterns.md"]`.

| ID | Negative pattern (wrong) | Correct practice (right) | Executor |
|---|---|---|---|
| NP-CON-01 | Execution-layer L1 cut by "materials / machinery / labour / subcontracting" | Cut the execution layer by project life-cycle stage; resource types appear as L2 or in value streams | LLM |
| NP-CON-02 | Owner-supplied materials and self-purchased materials merged into one object | Owner-supplied materials are a separate object (owner-supplied material receipt), with a different producer and settlement rules | LLM |
| NP-CON-03 | Reusable materials (formwork, scaffolding) treated like consumables | Reusable materials have an issue - amortization - return cycle and a separate ledger | LLM |
| NP-CON-04 | Migrant workers' wages shown only as "labour settlement", omitting payment through the dedicated wage account | Real-name attendance → payroll → payment via dedicated account → supervision, as separate steps | LLM |
| NP-CON-05 | Progress valuation (towards the owner) confused with subcontract settlement (towards subcontractors) | Model the revenue side and the cost side with separate objects and value streams | LLM |
| NP-CON-06 | Special equipment used immediately on arrival | After installation it may be used only after passing the statutory inspection; the inspection step belongs to the "arrival" stage | LLM |
