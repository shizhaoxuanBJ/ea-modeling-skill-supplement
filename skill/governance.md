# Governance Loop: Conflict List → Ruling → Writeback · Cross-Domain Registry

> Implements DP5 "Internalize governance rulings as skill rules" and cross-domain composability (zero C1-C3 conflicts).
> Problems that rules and the judgment library cannot resolve are not decided by the agent; they are **explicitly exposed** to the governance board, and once a ruling is written back, the same kind of problem does not recur.

## 1. Conflict list `conflicts.json`

Every run of `generate_views.py` / `check_model.py` writes it to the output directory:

```json
[{"id": "a1b2c3d4", "code": "REG-C3", "level": "CONFLICT", "view": "B4",
  "subject": "Payment Voucher", "pattern": "NP-B4-05",
  "message": "registry assigns ownership to 'Finance', but this domain lists it as its own object (B5 producer is a role of this domain); ...",
  "to": "governance board"}]
```

| level | Meaning | Blocks? |
|---|---|---|
| `ERROR` | violates a deterministic rule (missing contract item, cross-view inconsistency, hard naming rule) | blocks generation |
| `CONFLICT` | business conflict that rules cannot settle (cross-domain ownership, responsibility gap) | does not block, but goes to the list and to the xlsx "Open Issues" sheet |
| `WARN` | possible misjudgment signal (code+LLM negative patterns) | does not block; the agent must review each item and report how it was handled in the delivery note |

`id` is a hash of code + subject and stays stable across runs, so rulings can refer to it.

## 2. Rulings file `rulings.json` (maintained with the skill, organization-wide)

```json
{"id": "R-002", "date": "2026-11-10", "by": "EA governance board",
 "issue": "Is the invoice registered by the finance domain or the resource domain?",
 "decision": "VAT Invoice belongs to Finance; the resource domain only references it",
 "suppress": [{"code": "REG-C3", "subject": "VAT Invoice"}],
 "writeback": ["NP-B4-05"]}
```

- `suppress`: matching conflicts are no longer reported; the list instead notes "ruled under R-002"; a `domain` field restricts the ruling to one domain.
- `writeback`: the negative pattern or validation rule into which the ruling was turned. **Every ruling must have a writeback**;
  otherwise it is only a one-off correction and cannot be reused (rationale of DP5 in the paper).
- After adding a ruling, rerun the historical data as a regression (`check_model.py` on every archived biz_data) to confirm that ruled conflicts do not recur.

## 3. Cross-domain shared-object registry `registry.json` (organization-wide, one file shared by all domains)

```json
{"objects": [
  {"name": "VAT Invoice", "owner_domain": "Finance", "aliases": ["增值税发票", "Tax Invoice"]},
  {"name": "Supplier Master Record", "owner_domain": "Procurement", "aliases": ["供应商主数据"]}
]}
```

(Aliases may be in any language; the Chinese aliases above show bilingual matching.)

`model_rules.py` compares the B4 objects of the domain against the registry:

| code | Situation | level |
|---|---|---|
| `REG-C3` | object registered to another domain, but this domain lists it as its own object (and its C in B5 is an internal role of this domain) | CONFLICT |
| `REG-ALIAS` | an object name of this domain matches a registry alias → use the standard name | WARN |
| `REG-NEW` | object not registered → listed as "awaiting registration" (register with `registry.py add` after the governance board confirms) | INFO (written to the list, not counted as a conflict) |

When a domain references an object of another domain, it declares this explicitly in biz_data; this is not a conflict:

```json
"external_refs": ["VAT Invoice", "Payment Voucher"]
```

Registration commands (run after the governance board has confirmed ownership):

```bash
python scripts/registry.py add registry.json --domain "Resource Management" --from biz_data.json   # register this domain's own objects
python scripts/registry.py list registry.json
```

## 4. A complete governance cycle

```
generate → conflicts.json / Open Issues sheet
  → departmental architecture group checks the facts (edits biz_data)
  → governance board rules on CONFLICT items (writes rulings.json + adds a negative pattern or validation rule)
  → objects with settled ownership are registered in registry.json
  → rerun; the list is empty or contains only ruled items
```
