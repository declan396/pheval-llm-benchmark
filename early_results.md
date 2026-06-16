# Early Results

## LLM-Assisted Interpretation of Exomiser Outputs

| Patient | Ground truth | Exomiser top gene | Agent agreed with Exomiser? | LLM top gene | Outcome type | LLM added value? | Notes |
|---|---|---|---|---|---|---|---|
| patient_099 | Cardioneuromyopathy with hyaline masses and nemaline rods | GLE1 | No | TPM2 | Improved | Yes | Correctly rejected biologically implausible top hit and moved toward correct disease class |
| patient_001 | Achard syndrome | SC5D | Yes | SC5D | Failure | No | Reinforced plausible but incorrect Exomiser interpretation |
| patient_002 | Cole-Carpenter syndrome 1 | P4HB | Yes | P4HB | Agreement | Yes | Correct diagnosis and strong mechanistic interpretation |
| patient_003 | Brachydactyly type D | HOXD13 | Yes | HOXD13 | Partial | Yes | Correct limb phenotype class but not exact subtype |
| patient_004 | Ventricular arrhythmias due to RYR2 deficiency syndrome | RYR2 | Yes | RYR2 | Agreement | Yes | Correct arrhythmia syndrome with strong mechanistic reasoning |
| patient_006 | Ramos-Arroyo syndrome | FREM1 | No | ALX1 / SIX1 | Partial | Yes | Better craniofacial reasoning than Exomiser but misses exact syndrome |
| patient_007 | Congenitally short costocoracoid ligament | EYA1 | No | TRPV4 / LMNA | Partial | Yes | Identifies musculoskeletal disease pattern better than Exomiser |
| patient_008 | Isolated cryptophthalmos | FREM2 | Yes | FREM2 / FRAS1 / GRIP1 | Agreement | Yes | Correct Fraser-spectrum / cryptophthalmos reasoning |
| patient_009 | Darier-White disease | ATP2A2 | Yes | ATP2A2 | Agreement | Yes | Correct diagnosis with strong mechanistic skin pathology reasoning |
| patient_010 | Dyskeratosis congenita AD1 | STEAP3 | No | DKC1 | Improved | Yes | Correct telomeropathy disease class; improves on Exomiser top hit |
| patient_011 | Ear malformation | Unclear/random | No | None | Sparse phenotype limitation | Yes | Correctly identifies insufficient phenotype information |
| patient_012 | Epidermolysis bullosa simplex, Dowling-Meara | KRT14 | No | COL17A1 / PLEC | Partial | Yes | Correct EB spectrum but shifts toward junctional EB |
| patient_013 | Multiple exostoses type I | EXT1 | Yes | EXT1 | Agreement | Yes | Correct diagnosis and skeletal pathway reasoning |
| patient_014 | Focal facial dermal dysplasia 1, Brauer type | CYP26C1 | Yes | CYP26C1 / TWIST2 | Partial | Yes | Correct FFDD disease class but uncertain subtype |
| patient_015 | Multiple system atrophy 1 susceptibility | COQ2 | Yes | COQ2 | Agreement | Yes | Correct neurodegenerative/autonomic disease class with differential reasoning |
| patient_016 | Metaphyseal dysplasia with maxillary hypoplasia and brachydactyly | RUNX2 | Yes | RUNX2 | Partial | Yes | Strong skeletal reasoning but drifts toward cleidocranial dysplasia |
| patient_017 | Muir-Torre syndrome | MLH1 | Yes | MLH1 / MSH2 | Agreement | Yes | Correct Lynch/Muir-Torre interpretation with differential diagnosis |
| patient_018 | Transient myeloproliferative syndrome | GATA1 | No | ABL1 / BCR | Failure | No | Incorrectly redirected toward CML-like interpretation |
| patient_019 | Myoclonus, cerebellar ataxia, and deafness | Unclear/random | No | None | Sparse phenotype limitation | Yes | Correctly states single symptom is insufficient |
| patient_020 | Bilateral nasal alar collapse | Unclear/random | No | None | Sparse phenotype limitation | Yes | Correctly identifies non-diagnostic broad facial term |
| patient_021 | Hereditary vertical nystagmus | Unclear/random | No | None | Sparse phenotype limitation | Yes | Correctly identified failed Exomiser/no phenotype signal |
| patient_022 | Congenital nail disorder 5 | CTSB | No | WNT10A / TRPV3 | Improved | Yes | Correctly rejected unrelated Exomiser top hit and identified keratoderma genes |
| patient_023 | Orofaciodigital syndrome X | GLI3 | No | RSPO2 | Failure | No | Strong limb reasoning but incorrect disease family |
| patient_024 | Osteogenesis imperfecta type I | COL1A1 | Yes | COL1A1 | Agreement | Yes | Correct osteogenesis imperfecta interpretation |
| patient_025 | Pelger-Huet anomaly | LBR | Uncertain | LBR / OFD1 | Partial | Yes | Correctly identifies Pelger-Huet but overextends into ciliopathy reasoning |
| patient_026 | Polyposis, skin pigmentation, alopecia, and fingernail changes | FOXE3 | No | SLC39A4 / BMPR1A | Improved | Yes | Correctly rejected implausible Exomiser hit and identified relevant syndrome group |
| patient_027 | Premature chromatid separation trait | BUB1B | Yes | BUB1B | Agreement | Yes | Correct chromosomal instability syndrome interpretation |
| patient_028 | Pulmonary hemosiderosis | COL3A1 | No | COPA | Partial | Yes | Improved pulmonary haemorrhage reasoning but not exact diagnosis |
| patient_029 | Posterior dislocation of radial heads | SFRP4 | No | PTPN11 / SMAD6 | Sparse phenotype limitation | Yes | Correctly identified insufficient phenotype information |
| patient_030 | Sarcoidosis susceptibility 1 | HLA-DRB1 | No | NOD2 | Partial | Yes | Correctly identified limitation of Exomiser for complex trait disease |

---

## Preliminary Observations

- LLM performance improves substantially when phenotype sets are rich and disease-defining.
- The LLM frequently adds interpretability and mechanistic reasoning even when Exomiser already identifies the correct gene.
- Sparse or overly broad HPO terms significantly reduce diagnostic specificity and often produce non-actionable outputs.
- In several cases, the LLM improves on Exomiser by rejecting biologically implausible top-ranked genes and moving toward the correct disease class.
- However, the LLM also demonstrates a tendency to overgeneralise into broader syndromic categories or reinforce plausible but incorrect Exomiser outputs.
- The strongest performance is observed in disorders with highly characteristic phenotype combinations.
- The weakest performance is observed in cases with single HPO terms or highly non-specific phenotypes.
- The LLM frequently demonstrates stronger biological interpretation and differential diagnosis reasoning than raw Exomiser output, even when exact diagnosis is not achieved.

---

## Quantitative Summary

Total cases reviewed: 30

Agreement with Exomiser:
- 12

LLM improved Exomiser interpretation/ranking:
- 8

LLM reinforced incorrect Exomiser output:
- 4

Sparse phenotype limitations:
- Multiple cases

Main trend:
LLM-assisted interpretation appears most useful for improving interpretability and broad disease-class reasoning, while exact disease specificity decreases substantially when phenotype information is sparse or highly non-specific.

---

## Changing approach of agentic prompt?

The LLM was explicitly instructed to:
- evaluate Exomiser’s ranking
- determine whether the top-ranked gene was biologically plausible
- propose reranking where appropriate
- identify additional diagnostic steps or information gaps

Responses more mechanistic.