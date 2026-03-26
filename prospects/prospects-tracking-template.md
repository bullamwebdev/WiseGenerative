# WiseGenerative — Template Tracking Prospects

**Version:** 1.0 | **Date:** Mars 2026

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Pipeline Stages

| Stage | Définition | Action |
|-------|------------|--------|
| **NEW** | Entreprise identifiée | Ajouter à la liste |
| **QUALIFIED** | 5-30 salariés, 3+ ans, IDF | Qualifier via Pappers |
| **CONTACTED** | Email J1 envoyé | Suivre séquence |
| **REPLIED** | Réponse reçue (intérêt ou objection) | Répondre / Handle objection |
| **AUDIT BOOKED** | Créneau Calendly réservé | Préparer audit |
| **AUDIT DONE** | Audit 30min réalisé | Envoyer récap |
| **PROPOSAL** | Proposition envoyée | Suivre jusqu'à décision |
| **WON** | Client signé | Onboarding |
| **LOST** | Refusé | Reason tracking |
| **UNREACHABLE** | Email invalide, pas de réponse J30 | Archiver |

---

## Template Prospect

```yaml
ID: WG-001
Entreprise: [Nom]
SIRET: [XXXXXXXXXXXXXXX]
Gérant: [Prénom Nom]
Email: [email@entreprise.fr]
Téléphone: [Optionnel]
LinkedIn: [URL profil]

# Qualification
Salariés: [X]
Année création: [YYYY]
NAF: [43XX]
Région: [Île-de-France - 75/92/93/94/etc.]
Spécialité: [Plomberie/Électricité/Rénovation/etc.]

# Statut
Stage: NEW → QUALIFIED → CONTACTED → REPLIED → AUDIT_BOOKED → AUDIT_DONE → PROPOSAL → WON/LOST
Date contact J1: [YYYY-MM-DD]
Date contact J4: [YYYY-MM-DD]
Date contact J8: [YYYY-MM-DD]
Date contact J15: [YYYY-MM-DD]

# Engagement
LinkedIn connecté: [Oui/Non]
Réponse reçue: [Oui/Non]
Objection principale: [Temps/Prix/Compréhension/Autre]

# Audit
Audit booké: [YYYY-MM-DD HH:MM]
Audit réalisé: [Oui/Non]
Pain points identifiés: [List]

# Résultat
Proposition: [€]
Statut final: [WON/LOST/EN_COURS]
Raison perte: [Prix/Timing/Mauvais fit/Autre]
```

---

## Sources de Prospects

| Source | Volume estimé | Qualité | Coût |
|--------|----------------|---------|------|
| Pappers.fr | ~2,500 IDF | Haute (données officielles) | Gratuit quota, payant illimité |
| Societe.com | ~1,800 IDF | Moyenne | Gratuit |
| LinkedIn Sales Navigator | ~500 décideurs | Haute | ~100€/mois |
| FFB (adhérents) | 50,000 | Très haute | Partenariat requis |
| Expert-comptables (referral) | Variable | Très haute | Commission possible |
| Co-croissant/BPCE (banques) | Variable | Haute | Partenariat |

---

## Filtres de Qualification

**Critères obligatoires:**
- [x] 5-30 salariés (trop petit = pas de budget, trop grand = décision complexe)
- [x] Actif depuis 3+ ans (stabilité)
- [x] Île-de-France (focus géographique)
- [x] NAF 41xx ou 43xx (construction BTP)

**Critères bonus:**
- [ ] Pas de responsable admin/IT visible sur LinkedIn (besoin non comblé)
- [ ] Activité récente (site web actif, chantiers en cours)
- [ ] Reviews Google récentes (signe d'activité)

---

## Liste Initiale — Priorité Île-de-France

### Départements cibles

| Département | Code | Volume estimé | Priorité |
|-------------|------|----------------|----------|
| Paris | 75 | ~800 | 1 (taux faillite +25%) |
| Seine-Saint-Denis | 93 | ~400 | 2 (faillites +36%) |
| Hauts-de-Seine | 92 | ~350 | 3 |
| Val-de-Marne | 94 | ~300 | 4 |
| Yvelines | 78 | ~250 | 5 |
| Essonne | 91 | ~200 | 6 |
| Val-d'Oise | 95 | ~150 | 7 |
| Seine-et-Marne | 77 | ~150 | 8 |

### Requêtes Pappers

```
NAF: 41.10A, 41.20A, 41.20B, 43.11A, 43.12A, 43.21A, 43.22A, 43.29A, 43.31A, 43.32A, 43.33A, 43.34A, 43.91A, 43.99A
Région: Île-de-France
Effectif: 5-30
Statut: Actif
Date création: avant 2023
```

---

## Métriques à Suivre

### Weekly

| Métrique | Target | Outil |
|----------|--------|-------|
| Nouveaux prospects | 20/sem | Pappers |
| Emails J1 envoyés | 15/sem | CRM |
| Emails J4 envoyés | 12/sem | CRM |
| Connexions LinkedIn | 10/sem | LinkedIn |
| Réponses | 3/sem | CRM |
| Audits bookés | 1/sem | Calendly |

### Conversion Funnel

| Stage | Target % | Target # (si 20 prospects) |
|-------|----------|---------------------------|
| NEW → QUALIFIED | 80% | 16 |
| QUALIFIED → CONTACTED | 100% | 16 |
| CONTACTED → REPLIED | 20% | 3 |
| REPLIED → AUDIT_BOOKED | 50% | 1.5 |
| AUDIT_BOOKED → AUDIT_DONE | 80% | 1.2 |
| AUDIT_DONE → PROPOSAL | 60% | 0.7 |
| PROPOSAL → WON | 40% | 0.28 |

**Objectif:** 1 client signé / 70-100 prospects contactés

---

## Export Format (CSV)

```csv
ID,Entreprise,SIRET,Gérant,Email,Salariés,Année,NAF,Département,Stage,Date_J1,Date_J4,Date_J8
WG-001,Example SARL,12345678901234,Jean Dupont,contact@example.fr,12,2015,43.22A,75,QUALIFIED,2026-03-06,,,
```

---

**USAGE:** Remplir pour chaque prospect identifié
**MAJ:** Hebdomadaire