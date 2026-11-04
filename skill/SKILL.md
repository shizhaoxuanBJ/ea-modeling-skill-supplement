---
name: ea-business-architecture-views
description: Business architecture modeling for any industry and any business domain. Business staff supply documents per an input contract (or are interviewed); the agent executes a fixed method (capability → component → value stream → object → role matrix), generates B1-B5 PPTX views and an inventory xlsx from one biz_data.json, then runs deterministic validation, judgment-library self-review and a governance loop. Organization and industry differences (layer names, language, baselines, vocabulary, branding) live in profiles; generic Chinese and generic English profiles are built in. Also for reworking B3 value-stream diagrams. Business architecture only; decline data, application and technology views.
argument-hint: Tell me the business domain and industry (or attach duty documents, regulations, form samples), and which views you need
user-invocable: true
---

# Business Architecture Modeling · B1-B5 Views (industry-agnostic)

**The agent executes the modeling method; people supply facts and govern the results.**
Business staff do not learn modeling syntax; they only hand in business documents according to a checklist (or are interviewed). The agent extracts the facts into an intermediate representation, `biz_data.json`, and maps it to five kinds of views.
Rules that can be written down are checked by code; situated judgments are made by the LLM using the judgment library; business conflicts that rules cannot settle go to the governance board, and its rulings are written back as rules.

Outputs: B1 capability framework, B2 business components, B3 end-to-end value streams, B4 business objects, B5 object-role matrix (PPTX), plus a business-architecture inventory xlsx (with an "Open Issues" sheet) and `conflicts.json`.

## 1. Design principles and how they are implemented

The skill is designed for hybrid intelligence: the LLM extracts and generates from unstructured material, metamodel rules and deterministic checks constrain the generation, and people make the judgments that rules do not cover. The five principles:

| Principle | Problem addressed | Implementation in this skill |
|---|---|---|
| **DP1 Encode the application judgment of rules** | The rules are written down, but "how this rule applies to the case at hand" cannot be transferred by training | Judgment library [negative-patterns.md](negative-patterns.md) (core library) + industry packs `profiles/*.patterns.md`; self-review before each generation step |
| **DP2 Bridge documents and views with an IR** | Drawing views directly from documents carries omitted and fabricated facts through all layers | `biz_data.json`: extract facts first, map to views afterwards; business staff check facts in tables, not in diagrams |
| **DP3 Replace modeling expertise with an input contract** | Business staff "modeling" with templates produce task lists or job-centred descriptions | [input-contract.md](input-contract.md): 12-item material checklist + `provenance` declaration; views lacking required material are not issued as final versions |
| **DP4 Close the loop with a deterministic validator** | LLMs do not internalize the rules of a modeling language | Generate → validate → repair loop: `validate` (cross-view consistency) + `model_rules` (content rules) + B3 checks; labour divided by verifiability (see table below) |
| **DP5 Internalize governance rulings as skill rules** | One-off corrections cannot be reused; externally maintained knowledge bases are hard to sustain | [governance.md](governance.md): conflict list → governance ruling → [rulings.json](rulings.json) written back as a rule or negative pattern; cross-domain object registry |

**Division of labour by verifiability** (the core of the design, not merely "having a validator"):

| Rule type | Example | Executor |
|---|---|---|
| Formally checkable syntax and consistency | L1/L2 of B2 identical to B1; unique C per object; links do not cross boxes | Code (ERROR blocks) |
| Modeling choices that need situated judgment | Is this an L2 or a component? How should the execution layer be divided into stages? | LLM, guided by the judgment library (code only raises WARN signals) |
| Business-semantic conflicts | Two domains both claim the same document; no one produces a document | People (CONFLICT goes to the list; the governance board rules) |

## 2. Method core and context configuration (generalization)

The method core is the same for every industry: three layers (control / execution / support), the B1-B5 metamodel, the step-by-step process, the four CBM gates, unique C, cross-view consistency, and the B3 link rules.
All organizational and industry differences go into `profiles/<name>.json`; the method is not changed:

| Profile field | Content |
|---|---|
| `lang` | `zh` / `en`: interface text, naming style, text-fitting metrics |
| `layers` | names of the three layers (identical for all domains of one organization) |
| `baseline`, `limits` | granularity baseline (reference domain), number of value streams, nodes/lanes/stages per slide, number of role columns, B5 rows per slide |
| `naming`, `lexicon` | L2 naming style (`cn4` / `verb_object` / `free`); industry document suffixes and verb lists |
| `contract.views` | required materials per view (can be replaced to fit the organization) |
| `patterns` | judgment libraries to load: core library + industry packs |
| `branding`, `org_tiers_hint` | header series name, fonts; names of organizational tiers (reference for interviews and lanes) |

Built-in profiles: `generic-zh` (generic Chinese, default for Chinese domain names) and `generic-en` (generic English).
Selection order: command-line `--profile` > `biz_data.profile` > `generic-zh` / `generic-en` chosen from the language of the domain name.
Moving to a new industry or organization: create a profile as described in [reference.md](reference.md) §9 (use `extends` and write only the differences).
Example data in `scripts/examples/`: resource management (generic English) and hospital outpatient services (generic Chinese, kept to demonstrate the Chinese profile). An industry pack for construction is provided in `profiles/construction.patterns.md`.

## 3. Workflow (step by step; confirm each step before moving on)

```
Progress checklist:
- [ ] Step 0: choose the profile (industry/organization) → read the core judgment library + industry pack
- [ ] Step 1: collect materials per the input contract → write inputs.json and provenance                 [DP3]
- [ ] Step 2: B1 capabilities (execution layer first) → self-review against judgment library §B1 → user confirms  [DP1 DP2]
- [ ] Step 3: B2 components (decompose every L2, four CBM gates) → self-review → confirm
- [ ] Step 4: B3 value streams (stages × lanes × nodes × links) → self-review → confirm
- [ ] Step 5: B4 objects (real document names, check registry ownership) → self-review → confirm
- [ ] Step 6: B5 role matrix (C and U for every object) → self-review → confirm
- [ ] Step 7: assemble biz_data.json → generate-validate-repair loop → B3 checks                          [DP4]
- [ ] Step 8: deliver + hand open issues to the governance board → write rulings back                    [DP5]
```

### Step 0: choose the profile
Ask for the industry and organization. If the organization already has a profile, use it; otherwise start with `generic-zh` or `generic-en`, and after the first domain has been modeled and accepted by the governance board, create the organization's profile per reference.md §9 (using that domain as the baseline reference domain).
All business domains of one organization must use the same profile; otherwise layer names and granularity will not align and the views will not compose.

### Step 1: input contract
1. Give the user the checklist in [input-contract.md](input-contract.md) §1 and ask the business departments to submit materials accordingly. **Do not** ask business staff to fill in capability, component or object tables.
2. Write `inputs.json` with the submitted file names; when an interview replaces an item, record interviewer, interviewee and date.
3. Write `provenance` in biz_data.json: `documents` / `interview` (views lacking required material are not generated); use `draft` only when the user explicitly asks for a draft without material (every slide gets a DRAFT watermark, and the delivery must state that it is a discussion draft, not a baseline). If not declared, `draft` is assumed.

### Steps 2-6: guided modeling
Method: see [reference.md](reference.md); judgment library: negative-patterns.md and the industry pack named in the profile. Before each step, self-review against the matching section of the judgment library (especially entries whose executor is `LLM`), then show the draft to the user as a Markdown table for confirmation. Ask only about business facts, in the business staff's own words:

- **B1**: What are the main stages of the value chain? What must be done well in each stage? What does the parent organization control? What is done for you by other departments? (Divide the execution layer by value-chain stage, not by department, product line or resource type.)
- **B2**: What concrete tasks are done under each L2? (Pass the four CBM gates; do not decompose by system menus.)
- **B3**: Which steps lie between trigger and delivery? Who takes part? Which documents are produced? Who is handed the next step? (The end point is what the customer receives.)
- **B4**: Which forms, certificates, slips, letters and ledgers actually flow through each step? (Use real document names; objects of other domains go into `external_refs`.)
- **B5**: Who fills in each document (C, unique) and who uses it (U)?

### Step 7: generate-validate-repair loop

```bash
python scripts/check_model.py biz_data.json --registry registry.json --outdir outputs        # validate only, writes conflicts.json
python scripts/generate_views.py --data biz_data.json --outdir outputs --registry registry.json   # generate (validates again internally)
python scripts/generate_views.py --data biz_data.json --outdir outputs --views b3             # regenerate one view only
# add --profile <name> to override biz_data.profile
```

| Level | Meaning | Agent action |
|---|---|---|
| ERROR | violates a deterministic rule | no output; go back to the data using the negative-pattern ID given, fix and rerun |
| CONFLICT | business conflict that rules cannot settle | does not block; goes to the "Open Issues" sheet for the governance board |
| WARN | possible misjudgment signal | review each item against the judgment library; fix the data or state in the delivery note why it is kept |
| RULED / INFO | already ruled / object awaiting registration, etc. | list in the delivery note |

**Repairs change the data, never the rules to fit the data.** If a rule itself seems wrong, raise it as a governance issue; it is written back only after the governance board rules.

**B3 diagrams must pass the checks after generation** (offline first, then rendered; never the other way round):

```bash
python scripts/qa/check_links.py biz_data.json                 # (1) offline: box crossings / short last segments / bidirectional ports / isolated tasks must all be 0
python scripts/qa/check_cxn.py   outputs/<B3 file>.pptx         # (2) structure: one connector per link + 100% glued at both ends
python scripts/qa/export_png.py  outputs/<B3 file>.pptx png_out # (3) render PNGs with WPS/PowerPoint (not PDF)
python scripts/qa/check_arrow_px.py biz_data.json png_out       #     measure arrows in pixels; < 4 px counts as invisible
```

If a hard item is not 0, do not tune by eye: change the data (link order, stage of a node) or the `NODE_GAP/CH` constants and rerun.
Environments without WPS/PowerPoint (e.g. Linux) cannot do step (3): draw the planned routes with `b3_flow.link_plan` and inspect them page by page, and tell the user to re-check arrows in PowerPoint/WPS. LibreOffice recomputes glued connectors and substitutes missing fonts (causing overlapping text), so its rendering can be used to check text and layout only, not routing.

### Step 8: delivery and governance
1. Deliver 5 PPTX files + the inventory xlsx + conflicts.json.
2. The delivery note states: the profile used, the provenance mode (if draft, say clearly that it is a discussion draft), the CONFLICT list, and how WARN items were handled.
3. After the governance board rules, close the loop per [governance.md](governance.md) §4: write rulings.json (a writeback is mandatory) → add a negative pattern (core library or industry pack) or a validation rule → register objects whose ownership is now settled with `scripts/registry.py add` → rerun and confirm that ruled conflicts no longer appear.
4. Tell the user that later changes only require editing the relevant section of biz_data.json and rerunning a single view with `--views`.

## 4. B3 link rules (violations require rework)

| # | Rule | Check |
|---|---|---|
| 1 | **One link = one connector**; never split a bend into several straight lines | `check_cxn` reports only `line/bentConnector3/bentConnector4/custGeom` |
| 2 | **Both ends really glued** (`stCxn/endCxn` written), so links follow nodes when moved | glued at both ends 100%, half-glued 0 |
| 3 | **Last segment ≥ 0.06"**, otherwise the arrow has no shaft or even points outwards | `check_links` short last segments = 0; `check_arrow_px` invisible = 0 |
| 4 | **No port carries both an incoming and an outgoing link** | `check_links` bidirectional ports = 0 |
| 5 | **No crossing or hugging of boxes**; detour corridors ≤ 1.45 × Manhattan distance | box crossings = 0 |
| 6 | **Every task node except business objects has a link** | isolated tasks = 0 |
| 7 | **Vertically adjacent tasks are linked along the centre axis** (V-H-V), not around the sides | `c4` preferred |
| 8 | **Final acceptance only on PNGs exported by WPS/PowerPoint** | PDF renderers treat zero-width connectors differently and miss outward arrows |
| 9 | **Strictly orthogonal polylines** (tolerance 0.012"); corridors take the centre of the gap | slightly skewed segments escape collision detection |
| 10 | **Start/end dots and their labels are obstacles too** | otherwise links run over labels |

Layout values, failure causes and fixes, and data conventions are in [b3-flow-spec.md](b3-flow-spec.md); read §5 and §8 before changing B3.
When two long links are squeezed into one narrow channel, first merge steps or move a node to another stage; steps merged for layout must be stated in the legend (NP-B3-08).

## 5. Data file structure (key points)

- `profile`: profile name or json path; `provenance`: `{"mode": "documents|interview|draft", "manifest": "inputs.json"}`; `external_refs`: referenced objects of other domains;
- `layers` (B1) is the root: three layers `guide/exec/supp`, each with `blocks[{l1, l2[]}]`; `label` must match profile.layers;
- `b2.layers.*[{l1, l2s[{l2, comps[{name, shared}]}]}]` - L1/L2 identical to B1;
- `b3.overview.rows[{name, trigger, stages, customer, value}]` (any number) + `b3.pages[]`:
  `{title, subtitle, stages{names,weights}|[names], lanes[], start/end, start_label/end_label,
    nodes[{id, stage, lane, text, kind}], links[[a,b]], legend}` - `kind`: `act` = task / `doc` = business object (text must be the real name of a B4 object; `\n` may be used for line breaks);
  `start/end` are optional; **order of `links` = skeleton order: main chain first, back-links after**;
- `b4.layers.*[{l1, groups[{g, objs[]}]}]` - group names are B1 L2 names;
- `b5.{roles[{key, level, name}], pages[{title, l1s[]}], rows[{l1, l2, object, c, u[]}]}` - external roles have level "External"; rows beyond one slide continue automatically.

## 6. Environment

Generation uses python-pptx + openpyxl + Pillow; PyMuPDF for render checks. Final visual acceptance is done on Windows with WPS or PowerPoint (`qa/export_png.py` uses WPS COM `Slide.Export(path, "PNG", 2400, 1350)`).
On Windows set `PYTHONIOENCODING=utf-8` and use `python -X utf8`; if COM fails occasionally, run `taskkill /f /im wpp.exe` and retry. Without WPS/PowerPoint, use the alternative in Step 7 and tell the user.

## 7. Boundaries (mandatory)

- **Business architecture only (B1-B5).** State clearly that data, application and technology architecture views and gap-analysis lists are not supported.
- **No fabrication**: every capability, component, object and role must be grounded in documents or in statements by business staff. Drafting without material is delivered only as a discussion draft with `provenance.mode=draft`.
- **The method does not change by industry**: industry differences go only into profiles and industry negative-pattern packs; do not change the three-layer structure, the metamodel or the validation logic for an industry.
- **Cross-domain**: shared components and shared objects are not marked across domains for now (ruling R-001); but cross-domain ownership conflicts must be exposed to the governance board through the registry, and the agent does not decide them itself.
- **Governance belongs to people**: the agent does not change rules to fit the data and does not edit rulings.json or registry.json on its own; it only writes back what the governance board has ruled.
