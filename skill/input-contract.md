# Input Contract · Business Architecture B1-B5 (industry-agnostic)

> Implements DP3 "Replace modeling expertise with an input contract": business staff do not learn modeling syntax; they only submit **business documents** according to a checklist.
> The agent does the modeling; people check the facts. The contract determines which views can be generated; a view lacking required material is **not issued as a final version**.

## 1. Checklist (12 items, four groups)

| ID | Material | Level | Supports views | Answers |
|---|---|---|---|---|
| **A1** | Departmental responsibility statements (e.g. mandate documents, responsibility handbook, job descriptions, RACI tables) | required | B1, B5 | What does this domain do, and who is accountable? |
| **A2** | Organization chart and management tiers (with department names at each tier) | required | B3, B5 | Swimlanes, role columns |
| **A3** | Business regulations / management rules / operating procedures / SOPs | required | B1, B2, B3 | Capability boundaries, business tasks, flow rules |
| **A4** | Business blueprint / process descriptions / process charts | recommended | B3 | End-to-end steps and hand-overs |
| **A5** | Authority matrix / approval authority table | recommended | B5 | Who produces, who approves, who uses |
| **B1** | Samples or lists of forms and ledgers (forms, certificates, slips, letters, ledgers) | required | B4, B5 | Real object names |
| **B2** | Report list (external reporting / internal management reports) | recommended | B4 | Objects of the control layer |
| **C1** | Control requirements of the parent organization / assessment rules / external regulatory documents (industry supervision, compliance) | required | B1 (control layer) | Control themes |
| **C2** | Function lists / usage of existing systems | recommended | B2 | Component candidates (reference only; components are not cut along system modules) |
| **D1** | Descriptions of collaboration interfaces with other departments (who does what for this domain) | recommended | B1 (support layer) | Boundary of the support layer |
| **D2** | Ownership statements for documents shared across domains (e.g. invoices, payment vouchers, supplier master data) | recommended | B4, B5 | Cross-domain ownership, compared against the registry |
| **I1** | Interview records (interviewer, interviewee, date, key points) | substitute | any | May **substitute** for any required item, but must be recorded in the manifest |

View → required items (defaults; the profile's `contract.views` may adapt them to the organization, e.g. replace an item that does not exist there with a substitute ID):

| View | Required items (any missing item blocks the view unless `mode=draft`) |
|---|---|
| B1 | A1, A3, C1 |
| B2 | A3 |
| B3 | A2, A3 |
| B4 | B1 |
| B5 | A1, A2, B1 |

## 2. Manifest file `inputs.json`

```json
{
  "domain": "Outpatient Services",
  "items": {
    "A1": {"files": ["outpatient_department_responsibilities.pdf"]},
    "A2": {"files": ["org_chart_2026.pptx"]},
    "A3": {"files": ["outpatient_regulations.docx", "insurance_settlement_procedure.docx"]},
    "B1": {"files": ["outpatient_form_samples.xlsx"]},
    "C1": {"interview": {"who": "Medical Affairs Office, Group HQ", "date": "2026-11-03", "notes": "6 quality-control points"}}
  }
}
```

- `files`: names of the files actually submitted by the business department; `interview`: record used when an interview substitutes for the item (I1).
- An item may have both. An empty array/object counts as missing.

## 3. Provenance declaration in biz_data.json

```json
"provenance": {"mode": "documents", "manifest": "inputs.json"}
```

| mode | Meaning | Validation behaviour |
|---|---|---|
| `documents` | mainly based on submitted documents | missing required item → **ERROR**, the view is not generated |
| `interview` | mainly based on interviews (each item needs an I1 record) | as above; interview records count as fulfilment |
| `draft` | no material; discussion draft based on industry experience | missing items downgraded to WARN; **every slide is marked "DRAFT · not document-grounded"**, and so is the inventory xlsx |

Without `provenance`, `draft` is assumed: better one extra marker than an ungrounded view being taken as a baseline.

## 4. How to ask in interviews (without teaching modeling syntax)

Ask only about business facts, in the business staff's own words:

- "Where does this come from, and where does it go? Who gets the next step?" → B3
- "What document does this step leave behind? What is it called? Who fills it in, who signs it, who uses it?" → B4/B5
- "What does the parent organization check? What are you assessed on?" → B1 control layer
- "What do other departments do for you?" → B1 support layer

**Do not** ask business staff to fill in capability/component/object tables: that is what failed in Round 2 of the study (they produced lists of daily tasks or job-centred descriptions).
