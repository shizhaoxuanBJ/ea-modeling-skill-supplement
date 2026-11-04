# Evaluation Protocol

Definitions follow Sects. 3 and 6 of the paper. Data files are in `../data`, analysis scripts in `../analysis`.

## 1. View similarity

Sim(G1, G2) = 1 − GED(G1, G2) / (|V1| + |E1| + |V2| + |E2|)

- |Vi| and |Ei| are the numbers of elements and relationships of view Gi; GED is the minimum number of insertions, deletions or substitutions of elements and relationships that transform one view's graph into the other's.
- Matching: two elements match if they have the same metamodel type and their normalized names refer to the same business entity; two relationships match if they have the same type and matching ends.
- Naturalistic evaluation (Rounds 2 and 3): views were transcribed from PPTX into graphs by two research assistants using the same rules. Controlled experiments: graphs were exported from the skill's intermediate output.

| Consistency | Sample |
|---|---|
| Run-to-run | same input, 10 runs per domain → 45 pairs per domain, 225 in total |
| Inter-provider | input prepared independently by 4 employees per domain → 6 pairs per domain, 30 in total |
| Round 2 (same domain) | view sets drawn by IT staff in the same domain → 4, 4, 3, 3 and 2 pairs (19 in total) |

## 2. Cross-domain conflicts

- Reference objects: the 14 group-level shared objects referenced by the five core domains (8 group-wide application systems, 6 master-data entities).
- Conflict types: C1, the same object decomposed to different granularity; C2, an interface described with a different direction or mode of invocation; C3, both domains claiming the same master data.
- Counting: each of the ten domain pairs is checked; every inconsistency of granularity, interface direction or ownership of a shared object between two domains counts as one conflict. In the ablation study, the mean number over 10 runs is reported (rounded).

## 3. Uncaught violation rate

Share of output edges that violate the connection matrix of the tailored metamodel, |E_illegal| / |E|, averaged over the 50 runs (5 domains × 10 runs) of each configuration.

## 4. Same-input baseline and ablation

- Model: DeepSeek-V4 Pro, deployed on-premises, temperature 0.1; inputs: archived project inputs of the five core domains.
- Configurations: E1, a plain prompt containing the Round-2 drawing rules, without the skill; E2-A, without the judgment library; E2-B, without the deterministic validator; E2-C, without the IR; full skill. The parser and the orchestrator form the pipeline backbone and cannot be removed.

## 5. Blind expert rating

- Raters: five external EA experts, 12-16 years of practice, TOGAF-certified, not involved in the project.
- Samples: naturalistic evaluation, 16 Round-2 view sets + 12 Round-3 core views (28 in total); ablation, 12 core views per configuration taken from the median run (finance 3, procurement 2, sales 2, contract 2, treasury 3).
- Blinding: all views were redrawn in a uniform neutral style with source, configuration and generation parameters hidden, and presented in random order.
- Scales: syntactic accuracy and semantic completeness, each on a five-point scale.
- Agreement: ICC(2,5) 0.961 (syntax) / 0.973 (semantics) across all samples; 0.78 / 0.83 within Round 2; 0.02 / 0.35 within Round 3 (ceiling effect, all scores 4 or 5).

## 6. Qualitative coding

Two researchers not involved in developing the skill independently coded the 16 Round-2 view sets (granularity, layering, relationship type and grounding violations; 192 units, 173 in agreement, Cohen's κ = 0.86) and the interview transcripts (286 segments, κ = 0.82). See `../data/coding_agreement.csv`.

## 7. Domain names

The five core domains are finance, procurement, sales, contract (including legal affairs) and treasury. In Round 1 the domains were described as finance, sales, legal and supply chain (including procurement).
