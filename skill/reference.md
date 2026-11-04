# Business Architecture B1-B5 · Step-by-Step Modeling Method (industry-agnostic)

For the agent when guiding business staff. Core principle: **capability = what is done; component = a concrete task; object = a form, certificate, slip, letter or ledger that flows; role = who produces and who uses it**.

This file describes only the **method** and is industry-independent. Differences between industries or organizations (layer names, organizational tiers, granularity baseline, vocabulary) go into `profiles/<name>.json`; see §9.
Drawing rules are not in this file: layout, links and acceptance thresholds for B3 are in [b3-flow-spec.md](b3-flow-spec.md).

## 1. Three layers (fixed metamodel, configurable names)

| Layer (key) | Default name (en / zh) | Definition | Criterion |
|---|---|---|---|
| `guide` | Strategic Control / 战略管控 | Leadership, control and supervision of this domain by the parent organization | Verbs such as plan, control, supervise, assess; does not directly create the main value |
| `exec` | Business Execution / 业务执行 | End-to-end stages of this domain's main value chain | Divided by value-chain stage (4-7), each with a clear deliverable |
| `supp` | Integrated Support / 综合支撑 | Support provided to this domain by other functional domains | Shared services such as HR, finance, legal, IT, facilities |

The **structure** of the three layers is fixed for all industries (this is the metamodel); their **names** come from the profile's `layers`. All business domains of one organization must use the same profile, otherwise the views of different domains cannot be composed.

## 2. B1 capabilities (starting point)

Start with the execution layer, because business staff can describe the main value chain most easily:
1. "From receiving a task to delivering the result, which main stages are there?" → execution-layer L1 (value-chain stages, not departments, not resource types)
2. "What must be done well in each stage?" → L2 (Chinese: four-character verb-object; English: starts with a verb; style set by profile.naming)
3. "What does the parent organization control?" → control layer (control themes clustered into L1)
4. "What do other departments do for you?" → support layer

Five questions for judging a capability: What business result does it produce? Does it overlap with others in the same layer? Is it still needed after a reorganization? Does it control, create value, or support others? Who is accountable?
Naming: capability names contain no system or department names; L1 length ≤ profile.naming.l1_max.
Granularity: compare with profile.baseline (L1/L2 counts of the reference domain); suggest merging when more than 150%; the number of L2 under one L1 stays within profile.limits.l2_per_l1.

**Execution-layer examples by industry** (inspiration only, do not copy):

| Industry / domain | Example value-chain stages of the execution layer |
|---|---|
| Construction · project management | Pre-construction planning → Resource allocation → Construction → Completion and handover → Final account settlement → Asset transfer |
| Healthcare · outpatient services | Appointment → Triage and waiting → Consultation → Examination and testing → Billing → Follow-up |
| Manufacturing · order fulfilment | Order review → Planning and scheduling → Procurement → Production → Inspection and warehousing → Shipping |
| Retail banking · personal loans | Marketing → Application → Credit approval → Contract and disbursement → Loan monitoring → Repayment and closure |
| Generic · resource management | Demand planning → Sourcing and contracting → Receipt → On-site use → Settlement and exit |

## 3. B2 components

Every L2 must be decomposed into business components (L3 business tasks). Ask: "Which concrete tasks are done under this capability?"
**Four CBM gates** (a component must pass all): single responsibility / can operate independently / loosely coupled / governable at enterprise level.
- Component names are verb-object phrases and do not repeat the L2 name;
- Shared components are **not marked** (ruling R-001: decided uniformly after all domains are modeled; criteria = repeated in ≥ 2 L1s or business lines + same business object + rules can be standardized);
- Governance rules (regulations, standards, quotas) are attributes of components, not reusable components;
- Components are not cut along system menus or pages.

## 4. B3 value streams

**First decide how many streams, then stages × lanes × nodes for each stream.**

1. **Identify value streams**: cut by "one trigger, one customer, one deliverable". The number stays within profile.limits.streams (default 2-5); more means too fragmented, fewer means not separated.
   Common cuts: main chain (from demand to delivery) + resource or supply flow + funds or settlement flow + supervision or feedback flow.
2. **Stages**: reuse the B1 execution-layer L1; 4-6 stages per stream, or only a section of the execution layer. Split compound stage names (containing "→") into two stages.
3. **Lanes**: ask "Who takes part?" - organizational tiers from top to bottom, the last lane being external parties (customers, suppliers, regulators); 4-6 lanes in total. Tier names follow profile.org_tiers_hint, adjusted to the organization.
4. **Nodes**: ask "What is done in each step (task), and which document results (business object)?" 15-25 nodes per slide; more than profile.limits.b3_nodes_max requires splitting (one main line per slide).
5. **Flow**: ask "Who gets the next step?" - **main chain first, back-links after** (the order of `links` is the priority for claiming ports).
6. **Start and end**: where it starts (trigger event) and what it delivers (what the customer receives).

Vocabulary discipline: nodes say what is done (e.g. "Verify Supply Eligibility"), not system module names; documents use real names (e.g. "Acceptance Slip"); they share the name of the B4 object and are the source of the data architecture.

## 5. B4 objects

1. Ask "Which forms, certificates, slips, letters, ledgers and reports actually flow through each step?" - **object names are real document names** and must follow naming conventions;
2. Objects are assigned to an L1 (aligned with B1) and grouped by L2 within it (group names are the L2 names);
3. Duplicates: an object name appears only once; for similar objects (e.g. "daily report / weekly report") first ask whether they are the same thing;
4. Cross-domain: check the organization-wide registry (governance.md §3); objects registered to another domain may only be listed in `external_refs`;
5. The support layer may omit groups and list objects directly.

## 6. B5 object-role matrix

1. Role columns: grouped by organizational tier, number within profile.limits.roles (default 12-18); external roles have level "External";
2. For every object ask: "Who **produces** this document (C: exactly one, the person who fills it in, not the approver)? Who **uses** it (U: may be several)?"
3. Hard rules: exactly one C per row; C must not also appear in U; if no C can be found, it is a responsibility gap that goes to the conflict list for business confirmation;
4. Paging: one slide per L1 stage; rows beyond profile.limits.b5_rows_per_page continue automatically.

## 7. Cross-view consistency (hard rules)

- L1/L2 of B2 identical to B1 (script enforces ERROR)
- L1 of B4 ⊆ L1 of B1; group names = B1 L2 (composite names give WARN; allowed but should be aligned)
- Objects of B5 ⊆ objects of B4; each l2 must belong to the correct l1 (script enforces)
- B3 stage names aligned with B1 execution-layer L1 (WARN); document names in B3 identical to B4 objects (WARN)
- When any upstream view changes, all downstream views are regenerated in the same round (e.g. if an L2 name changes in B1, update B2/B4/B5/B3)

## 8. Text templates

- B1 introduction (2 lines): one sentence on the three-layer logic + a walk through the execution-layer value-chain stages
- B2 note: four CBM gates + statement that shared components are decided later + pointer to the component inventory
- B3 overview table, five columns: value stream / trigger → deliverable / stages traversed / customer / value delivered;
  footer note states the end-to-end criterion and why the streams were cut this way
- B4 note: columns = business domain (aligned with B1) / grey bars = L2 groups / cells = objects + pointer to the object inventory

## 9. Moving to a new industry or organization (creating a profile)

1. Copy `profiles/generic-zh.json` (or `generic-en.json`), change `id`, write `"extends": "generic-zh"` and only the differences;
2. `layers`: the organization's names for the three layers (uniform across the organization);
3. `baseline`: choose a domain that has been modeled and accepted by the governance board as the reference domain and enter its L1/L2 counts; keep the defaults until such a domain exists;
4. `org_tiers_hint`: names of organizational tiers, used in interviews and lanes (hint only, not validated);
5. `lexicon`: document suffixes or nouns of the industry (e.g. "prescription", "medical order", "policy"), to avoid false "object name looks like an action" warnings;
6. `contract.views`: if a type of material does not exist in the organization, replace the item with a substitute ID;
7. `patterns`: industry negative-pattern pack, written as `profiles/<industry>.patterns.md`, containing only misjudgments specific to the industry;
8. `branding`: header series name, fonts.

A profile changes only context parameters, **never the method**: the three-layer structure, the B1-B5 metamodel, the CBM gates, unique C and cross-view consistency are the same for all industries.
