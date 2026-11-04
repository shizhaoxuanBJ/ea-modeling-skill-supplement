# Intermediate Representation (IR) Templates Used in the Study

In Round 2, four types of elicitation templates were given to staff to fill in by hand. In Round 3 the same templates became the intermediate representation: the parser writes the facts extracted from submitted documents into these tables, business staff check them, and the orchestrator maps them to views (Sect. 4.2 and Sect. 5 of the paper, DP2).

| Template type | Tables |
|---|---|
| Business architecture | Business glossary; business capability list; business component list; value-stream stages and breakpoints |
| Data architecture | Data asset catalogue; data standards and master-data list |
| Application architecture | Application system list; functional module list; migration planning table |
| Technology architecture | Technology component list; infrastructure resource list |

Field-level definitions of these tables are not included in this package.

In the released skill (`../skill`), the IR for business architecture is the file `biz_data.json`; its structure is documented in `../skill/SKILL.md` §5, and complete examples are in `../skill/scripts/examples/`.
