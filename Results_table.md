| Patient | Ground truth | Exomiser top gene | LLM top gene | Outcome type | LLM added value? | Notes |
|---|---|---|---|---|---|---|
| patient_099 | Cardioneuromyopathy with hyaline masses and nemaline rods | GLE1 | TPM2 | Improved | Yes | Moves toward correct disease class; rejects biologically implausible top hit |
| patient_001 | Achard syndrome | SC5D | SC5D | Failure | No | Plausible but incorrect; reinforces Exomiser error |
| patient_002 | Cole-Carpenter syndrome 1 | P4HB | P4HB | Agreement | Yes | Correct diagnosis and gene; strong mechanistic interpretation |
| patient_003 | Brachydactyly type D | HOXD13 | HOXD13 | Partial | Yes | Correct limb phenotype class but not exact subtype |
| patient_004 | Ventricular arrhythmias due to RYR2 deficiency syndrome | RYR2 | RYR2 | Agreement | Yes | Correct arrhythmia syndrome with strong mechanistic reasoning |
| patient_006 | Ramos-Arroyo syndrome | FREM1 | ALX1 / SIX1 | Partial | Yes | Better craniofacial reasoning than Exomiser but misses exact syndrome |
| patient_007 | Congenitally short costocoracoid ligament | EYA1 | TRPV4 / LMNA | Partial | Yes | Identifies musculoskeletal disease pattern better than Exomiser |
| patient_008 | Isolated cryptophthalmos | FREM2 | FREM2 / FRAS1 / GRIP1 | Agreement | Yes | Correct Fraser-spectrum / cryptophthalmos reasoning |
| patient_009 | Darier-White disease | ATP2A2 | ATP2A2 | Agreement | Yes | Correct diagnosis with strong mechanistic skin pathology reasoning |
| patient_010 | Dyskeratosis congenita AD1 | STEAP3 | DKC1 | Improved | Yes | Correct telomeropathy disease class; improves on Exomiser top hit |
| patient_011 | Ear malformation | Unclear/random | None | Sparse phenotype limitation | Yes | Correctly identifies insufficient phenotype information |
| patient_012 | Epidermolysis bullosa simplex, Dowling-Meara | KRT14 | COL17A1 / PLEC | Partial | Yes | Correct EB spectrum but shifts toward junctional EB |
| patient_013 | Multiple exostoses type I | EXT1 | EXT1 | Agreement | Yes | Correct diagnosis and skeletal pathway reasoning |
| patient_014 | Focal facial dermal dysplasia 1, Brauer type | CYP26C1 | CYP26C1 / TWIST2 | Partial | Yes | Correct FFDD disease class but uncertain subtype |
| patient_015 | Multiple system atrophy 1 susceptibility | COQ2 | COQ2 | Agreement | Yes | Correct neurodegenerative/autonomic disease class with differential reasoning |
| patient_016 | Metaphyseal dysplasia with maxillary hypoplasia and brachydactyly | RUNX2 | RUNX2 | Partial | Yes | Strong skeletal reasoning but drifts toward cleidocranial dysplasia |
| patient_017 | Muir-Torre syndrome | MLH1 | MLH1 / MSH2 | Agreement | Yes | Correct Lynch/Muir-Torre interpretation with differential diagnosis |
| patient_018 | Transient myeloproliferative syndrome | GATA1 | ABL1 / BCR | Failure | No | Rejects Exomiser due to sparse phenotype and misses true syndrome |
| patient_019 | Myoclonus, cerebellar ataxia, and deafness | Unclear/random | None | Sparse phenotype limitation | Yes | Correctly states single symptom is insufficient |
| patient_020 | Bilateral nasal alar collapse | Unclear/random | None | Sparse phenotype limitation | Yes | Correctly identifies non-diagnostic broad facial term |
| patient_021 | Hereditary vertical nystagmus | Unclear/random | None | Sparse phenotype limitation | Yes | Correctly identifies insufficient phenotype specificity |
| patient_022 | Congenital nail disorder 5 | WNT10A | WNT10A / TRPV3 | Partial | Yes | Correct ectodermal/keratoderma disease class |
| patient_023 | Orofaciodigital syndrome X | GLI3 | RSPO2 / FMN1 | Failure | No | Strong limb reasoning but incorrect disease family |
| patient_024 | Osteogenesis imperfecta type I | COL1A1 | COL1A1 | Agreement | Yes | Correct collagen disorder interpretation |
| patient_025 | Pelger-Huet anomaly | LBR | LBR / OFD1 | Partial | Yes | Correctly identifies Pelger-Huet but overextends into ciliopathy reasoning |
| patient_026 | Polyposis, skin pigmentation, alopecia, and fingernail changes | BMPR1A | SLC39A4 / BMPR1A | Partial | Yes | Identifies overlapping malabsorption/polyposis syndromes |
| patient_027 | Premature chromatid separation trait | BUB1B | BUB1B | Agreement | Yes | Correct chromosomal instability syndrome reasoning |
| patient_028 | Pulmonary hemosiderosis | COL3A1 | COPA | Partial | Yes | Correct pulmonary haemorrhage class but not exact diagnosis |
| patient_029 | Posterior dislocation of radial heads | SFRP4 | SFRP4 / PTPN11 | Sparse phenotype limitation | Yes | Correctly states insufficient phenotype information |
| patient_030 | Sarcoidosis susceptibility 1 | HLA-DRB1 | HLA-DRB1 | Agreement | Yes | Correct inflammatory/granulomatous disease interpretation |

## Preliminary Observations

- LLM performance improves substantially when phenotype sets are rich and disease-defining.
- The LLM frequently adds interpretability and mechanistic reasoning even when Exomiser already identifies the correct gene.
- Sparse or overly broad HPO terms significantly reduce diagnostic specificity and often produce non-actionable outputs.
- In several cases, the LLM improves on Exomiser by rejecting biologically implausible top-ranked genes and moving toward the correct disease class.
- However, the LLM also demonstrates a tendency to overgeneralise into broader syndromic categories or reinforce plausible but incorrect Exomiser outputs.
- The strongest performance is observed in disorders with highly characteristic phenotype combinations (e.g. RYR2-related arrhythmia syndromes, Darier disease, hereditary multiple exostoses).
- The weakest performance is observed in cases with single HPO terms or highly non-specific phenotypes.
- The LLM frequently demonstrates stronger biological interpretation and differential diagnosis reasoning than raw Exomiser output, even when exact diagnosis is not achieved.

## Outcome Summary

Agreement / Correct: 8
Partial / Disease-class level: 15
Incorrect / Failure: 3
Sparse phenotype limitation: multiple cases

Main trend:
LLM-assisted interpretation appears most useful for improving interpretability and broad disease-class reasoning, while exact disease specificity decreases substantially when phenotype information is sparse or highly non-specific.
Moving towards more agentic prompting