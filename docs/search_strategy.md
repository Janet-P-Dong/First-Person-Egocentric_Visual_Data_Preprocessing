# TDSEM Search Strategy

This document translates the current reading coverage assessment into Web of Science search clusters. The goal is to fill dissertation-relevant gaps rather than retrieve the largest possible corpus.

## Guiding Rule

Searches should follow the dissertation argument, not the measurement tools. Measures such as IJA, RJA, RIFL, fNIRS, and MVGC are later-stage targeted searches unless a specific gap requires them.

## Current Seed Library Coverage

Source:

- `output_literature_audit/coverage/current_reading_coverage_report.md`

Strongly covered:

- caregiving and parent-child interaction,
- neural calibration and hyperscanning methods,
- measurement and methodology.

Moderately covered:

- relational/developmental systems theory,
- child agency and joint attention,
- heterogeneity/pathways/profiles.

Thin or missing:

- explicit child agency,
- responding to joint attention,
- neural directionality,
- developmental landscapes/profiles,
- explicit developmental calibration/recalibration framing.

## Cluster A - Relational Developmental Systems

Purpose: establish the theoretical landscape: developmental systems, transactional development, dynamic systems, child effects, parent effects, co-regulation, equifinality, and multifinality.

Status: updated Web of Science search run on 2026-06-23; 708 records.

Web of Science result set:

- https://webofscience.clarivate.cn/wos/woscc/summary/93d29d1f-c801-457f-92ac-af1ebe92cbf3-01baf025cc/relevance/1

```text
TS=(
  "developmental systems theory"
  OR "transactional model"
  OR "transactional development"
  OR "dynamic systems theory"
  OR "child effects"
  OR "parent effects"
  OR "co-regulation"
  OR coregulation
  OR equifinality
  OR multifinality
)
AND TS=(
  "parent-child"
  OR "parent child"
  OR mother*
  OR maternal
  OR father*
  OR paternal
  OR caregiv*
)
AND TS=(
  child*
  OR infant*
  OR toddler*
  OR preschool*
)
```

Suggested filters:

- Document types: Article, Review.
- Categories: Psychology Developmental, Psychology, Family Studies, Behavioral Sciences, Pediatrics.
- Language: English if appropriate for dissertation scope.

## Cluster B - Child Agency

Purpose: fill the largest conceptual gap in the seed library. This search should capture children's active contribution to developmental processes, not only joint attention.

Status: updated Web of Science search run on 2026-06-23; 2,213 records.

Web of Science result set:

- https://webofscience.clarivate.cn/wos/woscc/summary/4634fe90-2dc1-441a-83e7-4a4d63a26078-01baf09116/relevance/1

Broad search:

```text
TS=(
  "child agency"
  OR "active child"
  OR "child effects"
  OR "child-driven"
  OR "child-led"
  OR "child initiated"
  OR "child-initiated"
  OR "child participation"
  OR "social participation"
  OR "shared intentionality"
  OR "social engagement"
  OR "child directed interaction"
  OR "child-directed interaction"
)
AND TS=(
  development*
  OR "developmental"
  OR infant*
  OR toddler*
  OR preschool*
  OR child*
  OR "early childhood"
)
AND TS=(
  parent*
  OR caregiv*
  OR mother*
  OR maternal
  OR father*
  OR paternal
  OR dyad*
  OR "parent-child"
  OR "mother-child"
  OR "father-child"
)
```

If too broad, narrow with:

```text
AND TS=(
  "parent-child interaction"
  OR "parent child interaction"
  OR caregiv*
  OR dyad*
)
```

## Cluster B2 - Joint Attention / RJA Gap

Purpose: the seed library has IJA and general joint attention but no clear RJA coverage. This targeted search fills the RJA gap.

RJA status: updated Web of Science search run on 2026-06-23; 124 records.

RJA Web of Science result set:

- https://webofscience.clarivate.cn/wos/woscc/summary/ac602b1a-4ec7-4f6c-9833-2fea9498cdb5-01baf1648a/relevance/1

```text
TS=(
  "responding to joint attention"
  OR "response to joint attention"
  OR RJA
  OR "responding joint attention"
  OR "joint attention response"
)
AND TS=(
  development*
  OR "developmental"
  OR infant*
  OR toddler*
  OR preschool*
  OR child*
  OR "early childhood"
)
AND TS=(
  language
  OR "social cognition"
  OR learning
  OR "social competence"
  OR longitudinal
  OR autism
  OR ASD
  OR "autism spectrum"
  OR "autism spectrum disorder"
)
```

Companion IJA search, only if balance is needed:

IJA status: updated Web of Science search run on 2026-06-23; 97 records.

IJA Web of Science result set:

- https://webofscience.clarivate.cn/wos/woscc/summary/a1d7823b-bb3c-4aa3-9634-ae3ce9f63da0-01baf19bcc/relevance/1

```text
TS=(
  "initiating to joint attention"
  OR "initati* to joint attention"
  OR IJA
  OR "initiating joint attention"
  OR "joint attention response"
)
AND TS=(
  development*
  OR "developmental"
  OR infant*
  OR toddler*
  OR preschool*
  OR child*
  OR "early childhood"
)
AND TS=(
  language
  OR "social cognition"
  OR learning
  OR "social competence"
  OR longitudinal
)
```

## Cluster C - Developmental Scaffolding and Observational Support

Purpose: already strongly covered in the seed library. Use this mainly to support RIFL, observational caregiving, and measurement, while interpreting the construct as developmental scaffolding and the functional translation of parental support rather than a generic caregiving effect.

Status: updated Web of Science search run on 2026-06-23; 1,657 records.

Web of Science result set:

- https://webofscience.clarivate.cn/wos/woscc/summary/fe6f0b58-6768-4b09-9ea3-8214c284c864-01baf27d8d/relevance/1

```text
TS=(
  "responsive caregiving"
  OR "parental responsiveness"
  OR "maternal responsiveness"
  OR "caregiver sensitivity"
  OR "parent sensitivity"
  OR "paternal sensitivity"
  OR "caregiver responsiveness"
  OR scaffolding
  OR "parental scaffolding"
  OR "developmental scaffolding"
  OR "effective scaffolding"
  OR "guided participation"
  OR "cognitive stimulation"
  OR "learning support"
  OR "responsive interaction"
)
AND TS=(
  infant*
  OR toddler*
  OR preschool*
  OR child*
)
AND TS=(
  observation*
  OR coding
  OR measure*
  OR assessment
  OR "parent-child interaction"
  OR "parent child interaction"
  OR "mother-child interaction"
  OR "father-child interaction"
)
```

RIFL targeted search:

```text
TS=(
  RIFL
  OR "responsive interactions for learning"
  OR "developmental scaffolding"
  OR "parental scaffolding"
  OR "effective scaffolding"
  OR "learning support"
  OR "caregiving observation"
  OR "parent child coding"
  OR "observational parenting measures"
)
```

## Cluster D - Heterogeneity, Pathways, Profiles

Purpose: important gap for developmental calibration. This should be a priority because it links empirical variability to the dissertation framework.

Status: updated Web of Science search run on 2026-06-24; 2,392 records after choosing Highly Cited Papers.

Web of Science result set:

- https://webofscience.clarivate.cn/wos/woscc/summary/2649ba67-b580-4e39-a25b-71bdd3734d90-01bb0afa23/relevance/1

```text
TS=(
  "developmental heterogeneity"
  OR "developmental variability"
  OR "individual differences"
  OR "person-centered"
  OR "person centered"
  OR "latent profile"
  OR "latent profile analysis"
  OR "latent class"
  OR "latent class analysis"
  OR "developmental profiles"
  OR "developmental trajectories"
  OR "developmental pathways"
  OR equifinality
  OR multifinality
  OR "nonlinear development"
  OR "developmental transitions"
  OR "developmental reorganization"
  OR "state space"
  OR "state space grid"
  OR "developmental landscape"
  OR "growth mixture"
  OR "developmental cascade"
  OR "differential susceptibility"
)
AND TS=(
  infant*
  OR toddler*
  OR preschool*
  OR child*
  OR "early childhood"
  OR "young children"
)
AND TS=(
  parent*
  OR caregiv*
  OR mother*
  OR maternal
  OR father*
  OR paternal
  OR "parent-child"
  OR "parent child"
  OR "mother-child"
  OR "father-child"
  OR "dyadic"
)
```

If too broad, add:

```text
AND TS=(
  longitudinal
  OR trajectory
  OR profile
  OR "latent class"
  OR "latent profile"
)
```

## Cluster E1 - Neural Directionality

Purpose: seed library has neural calibration and synchrony, but directionality is thin. This search should target effective connectivity, leader-follower dynamics, and directional influence.

Status: updated Web of Science search run on 2026-06-24; 4,880 records.

Web of Science result set:

- https://webofscience.clarivate.cn/wos/woscc/summary/c3848f5d-9065-4786-aaea-23ceb580abca-01bb0e3a3d/relevance/1

```text
TS=(
  "effective connectivity"
  OR "granger causality"
  OR "Granger-causal"
  OR "Granger causal"
  OR "neural directionality"
  OR "directional connectivity"
  OR "directed connectivity"
  OR "leader-follower"
  OR "leader follower"
  OR "parent-child influence"
  OR "brain-to-brain coupling"
  OR "interbrain directionality"
  OR "inter-brain directionality"
)
AND TS=(
  "parent-child"
  OR "parent child"
  OR mother*
  OR maternal
  OR father*
  OR paternal
  OR caregiv*
  OR dyad*
  OR "mother-child"
  OR "father-child"
  OR "caregiver-child"
)
AND TS=(
  fNIRS
  OR "functional near-infrared spectroscopy"
  OR EEG
  OR "electroencephalography"
  OR hyperscanning
  OR "dual EEG"
  OR "social neuroscience"
  OR "interbrain synchrony"
  OR "inter-brain synchrony"
  OR "neural synchrony"
  OR "phase synchrony"
  OR coherence
  OR "neural coherence"
  OR "cross-brain"
  OR "cross brain"
)
```

## Cluster E2 - Longitudinal Recalibration

Purpose: fill the longitudinal/time-scale side of developmental calibration.

Status: updated Web of Science search run on 2026-06-24; more than 80,000 records.

Sampling decision: download the top 1,000 records sorted by relevance.

Web of Science result set:

- https://webofscience.clarivate.cn/wos/woscc/summary/f345c928-bb99-4c8a-a5b2-d660c8ebea25-01bb0faf3f/relevance/1

```text
TS=(
  "developmental cascades"
  OR "developmental stability"
  OR "developmental change"
  OR "developmental continuity"
  OR "developmental transitions"
  OR "developmental reorganization"
  OR "developmental recalibration"
  OR "developmental pathways"
  OR "developmental trajectory"
  OR "developmental trajectories"
)
AND TS=(
  longitudinal
  OR "over time"
  OR trajectory
  OR trajectories
  OR "follow-up"
  OR "growth curve"
  OR "growth modeling"
  OR "latent growth"
  OR "cross-lagged"
  OR "cross lagged"
)
AND TS=(
  parent*
  OR caregiv*
  OR mother*
  OR maternal
  OR father*
  OR paternal
  OR child*
  OR infant*
  OR toddler*
  OR preschool*
  OR "early childhood"
  OR "parent-child"
  OR "parent child"
  OR "mother-child"
  OR "father-child"
  OR dyad*
)
```

## Recommended Search Order

Based on current coverage gaps:

1. Cluster B - Child Agency.
2. Cluster B2 - RJA targeted search.
3. Cluster D - Heterogeneity/pathways/profiles.
4. Cluster E1 - Neural directionality.
5. Cluster A - Relational systems master corpus.
6. Cluster C - Caregiving/RIFL targeted refresh only if needed.

Rationale: the seed library already covers caregiving and neural calibration strongly. The next searches should fill the argument's weak points before expanding already-rich areas.
