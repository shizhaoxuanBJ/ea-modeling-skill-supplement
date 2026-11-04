# Judgment Library · Negative Patterns in Business Content (industry-agnostic core library)

> Implements DP1 "Encode the application judgment of rules": the rules themselves (reference.md) are not enough; what the LLM lacks is
> **"how this rule applies to the case at hand"**. This library collects typical misjudgments found so far; read the matching section before generating each view.
>
> **Executor** follows the division of labour by verifiability (paper §5):
> `code` = intercepted automatically by `scripts/model_rules.py`; `LLM` = self-review during generation; `people` = ruled by the governance board.
> For entries marked `code+LLM`, code catches only surface signals (WARN); the substantive judgment remains with the LLM.
>
> New patterns come from only two sources: (1) rework records and (2) governance rulings (`writeback` in `rulings.json`). Nothing is added without a source.
>
> **Layering**: this file contains only industry-independent misjudgments; industry-specific ones go into industry packs `profiles/<industry>.patterns.md`,
> loaded through the profile's `patterns` field (e.g. `construction.patterns.md`). Read both before generating.
> Examples in the tables come from different industries and only illustrate the pattern; they do not limit its scope.

## B1 Capabilities

| ID | Negative pattern (wrong) | Correct practice (right) | Executor |
|---|---|---|---|
| NP-B1-01 | Promoting a low-level task to L1/L2, e.g. "Purchase Reconciliation" as an L1 | Reconciliation is a component under "Settlement"; an L1 is a value-chain stage | LLM |
| NP-B1-02 | Capability name contains a department or system name, e.g. "Materials Department Management", "ERP Purchasing" | A capability = what is done, independent of who does it or with what | code |
| NP-B1-03 | L2 written as a noun or a process fragment, e.g. "Suppliers", "Purchasing Process" | Chinese: four-character verb-object; English: starts with a verb (Qualify Suppliers) | code |
| NP-B1-04 | Two capabilities in the same layer are actually one, e.g. "Tender Management" next to "Purchase Sourcing" | Merge them, or split by "sourcing / contracting" and state the boundary | code+LLM |
| NP-B1-05 | Work done for this domain by other departments placed in the execution layer, e.g. "Pay Suppliers" | Place it in the integrated support layer (financial management) | LLM |
| NP-B1-06 | Control layer written as execution actions, e.g. "Prepare Requirement Plan" in the control layer | Control-layer verbs are set/supervise/assess/alert; preparing and executing belong to the execution layer | code+LLM |
| NP-B1-07 | Unbalanced granularity: more than 8 or fewer than 2 L2 under one L1; total count more than 50% above the baseline | Split or merge L1; compare with the baseline (reference.md §2) | code |
| NP-B1-08 | Execution-layer L1 cut by resource type, product line or department, e.g. "Materials / Equipment", "Outpatient Dept / Medical Technology Dept" | Cut the execution layer by value-chain stage (e.g. appointment → triage → treatment → examination → billing → follow-up); resource types and product lines appear in L2 and in value streams | LLM |

## B2 Components

| ID | Negative pattern (wrong) | Correct practice (right) | Executor |
|---|---|---|---|
| NP-B2-01 | Component has the same name as its L2 (empty decomposition) | A component is a concrete task under the L2, e.g. L2 "Qualify Suppliers" → "Review Credentials", "Inspect Site" | code |
| NP-B2-02 | Regulations, standards or quotas treated as components, e.g. "Materials Management Rules" | Rules are attributes of a component; write the component as an action, e.g. "Set and Publish Quotas" | code+LLM |
| NP-B2-03 | System pages or create/read/update/delete operations split into components, e.g. "Add Supplier", "Query Inventory" | Merge into one business task, e.g. "Maintain Supplier Information" | code |
| NP-B2-04 | The same component appears under several L2 | Keep it under the accountable L2; do not repeat it elsewhere | code |
| NP-B2-05 | Component written as a position or role, e.g. "Materials Clerk" | Roles go to B5; components are tasks | LLM |

## B3 Value Streams

| ID | Negative pattern (wrong) | Correct practice (right) | Executor |
|---|---|---|---|
| NP-B3-01 | Value streams cut by department, e.g. "Materials Department Process" | Cut by "one trigger, one customer, one deliverable" | LLM |
| NP-B3-02 | More than 5 value streams (too fragmented) or fewer than 2 (not separated) | 2-5; extra ones are usually sub-processes | code |
| NP-B3-03 | Stage names differ from the L1 names of the B1 execution layer | Use the B1 execution-layer L1 names directly | code |
| NP-B3-04 | Node written as a system module, e.g. "Supplier Management Module" | Write an action, e.g. "Verify Supply Eligibility" | code |
| NP-B3-05 | Document node name differs from the B4 object name | A document node is a B4 object; names must match exactly (line breaks allowed) | code |
| NP-B3-06 | More than 30 nodes on a slide, or more than 6 lanes or stages | Split into several slides, one main line per slide | code |
| NP-B3-07 | End point is an internal approval instead of a delivery, e.g. ending at "Settlement Approval" | The end point is what the customer receives, e.g. "Supplier Receives Payment", "Wages Credited" | LLM |
| NP-B3-08 | Real business steps deleted to make the diagram look tidy | Steps may be merged in the drawing (e.g. "Tendering" includes "Bidding"), but the merge must be stated in the caption or legend | people |

## B4 Objects

| ID | Negative pattern (wrong) | Correct practice (right) | Executor |
|---|---|---|---|
| NP-B4-01 | Object written as an action or capability, e.g. "Materials Acceptance" | Use the real document name, e.g. "Materials Acceptance Slip" | code+LLM |
| NP-B4-02 | One document with several names, e.g. "Goods Receipt / Material Receipt Note" | First ask the business whether they are the same thing; if so, use the real name and record the other as an alias in the registry | code+people |
| NP-B4-03 | The same object appears in several groups | Assign it to the L2 that produces it | code |
| NP-B4-04 | A system or platform treated as an object, e.g. "Materials Management System" | Objects are forms, certificates, slips, letters, ledgers and reports; systems belong to the application architecture | code |
| NP-B4-05 | This domain "claims" a document of another domain, e.g. the resource domain producing a "Payment Voucher" | Check the registry: objects registered to another domain may only be listed as references (`external_refs`) | code+people |

## B5 Role Matrix

| ID | Negative pattern (wrong) | Correct practice (right) | Executor |
|---|---|---|---|
| NP-B5-01 | A row has no C or several C | Each row has exactly one C; if no C can be found, it is a responsibility gap for the governance board to confirm | code |
| NP-B5-02 | Approver taken as producer, e.g. the head of department as C of a prescription | C is the person who fills in or initiates (the prescribing doctor); the approver is a U | LLM |
| NP-B5-03 | An external party set as C of an internal ledger | The C of an internal ledger is an internal role; external parties produce the documents they submit (quotations, invoices, payrolls) | LLM |
| NP-B5-04 | A B4 object has no row in B5, and the responsibility gap is not marked | Every B4 object has a row; objects that no one produces go to the conflict list | code |
| NP-B5-05 | Role names are person or system names | Role = organizational tier + position/department | code |

## Provenance

| ID | Negative pattern (wrong) | Correct practice (right) | Executor |
|---|---|---|---|
| NP-SRC-01 | Drafting from industry experience without material, then delivering it as a formal baseline | Set `provenance.mode=draft` and mark every slide DRAFT; issue the final version only after the contract is fulfilled | code |
