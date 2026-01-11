---
schema_type: common
title: "Document Type Taxonomy - Hierarchical Domain Classification"
tags:
  - reference
  - taxonomy
status: published
owner: docs-team
purpose: Reference documentation for document type taxonomy - hierarchical classification of document domains for Phase 7/9 training.
---

**Version**: 1.0 (Faceted Hierarchical)
**Date**: 2025-12-17
**Status**: 🚧 **In Progress** - Initial taxonomy definition

## Purpose

This document defines a **hierarchical document type taxonomy** for classifying documents by domain, structure, and purpose. The taxonomy enables:

1. **Stratified sampling**: Ensure training data covers all document types
2. **Domain-specific evaluation**: Measure model performance per document category
3. **Coverage gap analysis**: Identify under-represented document types
4. **Production alignment**: Weight training data to match production distribution

## Taxonomy Structure

The document type taxonomy uses a **4-level hierarchy**:

```
Level 1: Domain (9 categories)
└── Level 2: Sub-domain (~40 categories)
    └── Level 3: Document Class (~100 categories)
        └── Level 4: Specific Type (~200+ types)
```

---

## Level 1: Primary Domains

| Domain Code | Domain Name | Description | Production % (Est.) |
|-------------|-------------|-------------|---------------------|
| `TAX` | Tax & Compliance | Tax forms, filings, regulatory documents | 15% |
| `LEG` | Legal | Contracts, court documents, legal filings | 12% |
| `FIN` | Financial | Invoices, statements, receipts, banking | 25% |
| `TEC` | Technical | Manuals, specifications, engineering docs | 8% |
| `SCI` | Scientific | Research papers, lab reports, publications | 5% |
| `ADM` | Administrative | Business correspondence, memos, HR docs | 18% |
| `MED` | Medical/Healthcare | Patient records, prescriptions, lab results | 7% |
| `EDU` | Educational | Textbooks, exams, transcripts, certificates | 6% |
| `PER` | Personal | IDs, certificates, personal correspondence | 4% |

---

## Level 2-4: Detailed Hierarchy

### TAX - Tax & Compliance

```
TAX
├── TAX.IND - Individual Tax Returns
│   ├── TAX.IND.1040 - Form 1040 Series
│   │   ├── 1040 - Standard Individual Return
│   │   ├── 1040-SR - Senior Return
│   │   ├── 1040-NR - Non-Resident Return
│   │   └── 1040-X - Amended Return
│   ├── TAX.IND.SCH - Schedules
│   │   ├── Schedule A - Itemized Deductions
│   │   ├── Schedule B - Interest/Dividends
│   │   ├── Schedule C - Business Income
│   │   ├── Schedule D - Capital Gains
│   │   └── Schedule E - Rental Income
│   └── TAX.IND.STATE - State Returns
│       ├── CA_540 - California
│       ├── NY_IT201 - New York
│       └── [other states]
├── TAX.BUS - Business Tax Returns
│   ├── TAX.BUS.CORP - Corporate
│   │   ├── 1120 - C Corporation
│   │   ├── 1120-S - S Corporation
│   │   └── 1065 - Partnership
│   └── TAX.BUS.PAYROLL - Payroll Tax
│       ├── 941 - Quarterly Employment Tax
│       ├── 940 - FUTA Tax
│       └── W-2 - Wage Statement
├── TAX.INFO - Information Returns
│   ├── 1099-MISC - Miscellaneous Income
│   ├── 1099-INT - Interest Income
│   ├── 1099-DIV - Dividend Income
│   ├── 1099-K - Payment Card Transactions
│   └── W-9 - Taxpayer ID Request
└── TAX.REG - Regulatory Compliance
    ├── FBAR - Foreign Bank Account Report
    ├── 8938 - Foreign Financial Assets
    └── State_Reg - State Registrations
```

### LEG - Legal

```
LEG
├── LEG.CON - Contracts
│   ├── LEG.CON.EMP - Employment
│   │   ├── Employment_Agreement
│   │   ├── NDA - Non-Disclosure
│   │   ├── Non_Compete
│   │   └── Severance_Agreement
│   ├── LEG.CON.RE - Real Estate
│   │   ├── Lease_Residential
│   │   ├── Lease_Commercial
│   │   ├── Purchase_Agreement
│   │   └── Deed
│   ├── LEG.CON.BUS - Business
│   │   ├── Service_Agreement
│   │   ├── Vendor_Contract
│   │   ├── License_Agreement
│   │   └── Partnership_Agreement
│   └── LEG.CON.FIN - Financial
│       ├── Loan_Agreement
│       ├── Promissory_Note
│       └── Security_Agreement
├── LEG.CRT - Court Documents
│   ├── LEG.CRT.PLG - Pleadings
│   │   ├── Complaint
│   │   ├── Answer
│   │   ├── Motion
│   │   └── Brief
│   ├── LEG.CRT.ORD - Orders
│   │   ├── Court_Order
│   │   ├── Judgment
│   │   └── Decree
│   └── LEG.CRT.EVD - Evidence
│       ├── Exhibit
│       ├── Deposition
│       └── Affidavit
├── LEG.EST - Estate Planning
│   ├── Will
│   ├── Trust
│   ├── Power_of_Attorney
│   └── Living_Will
└── LEG.IP - Intellectual Property
    ├── Patent_Application
    ├── Trademark_Registration
    └── Copyright_Filing
```

### FIN - Financial

```
FIN
├── FIN.INV - Invoices & Receipts
│   ├── FIN.INV.STD - Standard Invoices
│   │   ├── Commercial_Invoice
│   │   ├── Service_Invoice
│   │   └── Pro_Forma_Invoice
│   ├── FIN.INV.RCP - Receipts
│   │   ├── Sales_Receipt
│   │   ├── Payment_Receipt
│   │   └── Expense_Receipt
│   └── FIN.INV.PO - Purchase Orders
│       ├── Purchase_Order
│       ├── Quote
│       └── Estimate
├── FIN.STM - Statements
│   ├── FIN.STM.BNK - Banking
│   │   ├── Bank_Statement
│   │   ├── Check_Image
│   │   └── Wire_Transfer
│   ├── FIN.STM.CRD - Credit
│   │   ├── Credit_Card_Statement
│   │   └── Credit_Report
│   └── FIN.STM.INV - Investment
│       ├── Brokerage_Statement
│       ├── 401k_Statement
│       └── IRA_Statement
├── FIN.ACC - Accounting
│   ├── FIN.ACC.GL - General Ledger
│   ├── FIN.ACC.BS - Balance Sheet
│   ├── FIN.ACC.PL - Profit & Loss
│   └── FIN.ACC.CF - Cash Flow Statement
└── FIN.INS - Insurance
    ├── Policy_Document
    ├── Claim_Form
    ├── EOB - Explanation of Benefits
    └── Certificate_of_Insurance
```

### TEC - Technical

```
TEC
├── TEC.MAN - Manuals
│   ├── TEC.MAN.USR - User Manuals
│   ├── TEC.MAN.SVC - Service Manuals
│   ├── TEC.MAN.INS - Installation Guides
│   └── TEC.MAN.QRG - Quick Reference Guides
├── TEC.SPC - Specifications
│   ├── TEC.SPC.PRD - Product Specs
│   ├── TEC.SPC.ENG - Engineering Specs
│   └── TEC.SPC.MAT - Material Specs
├── TEC.DWG - Drawings
│   ├── TEC.DWG.CAD - CAD Drawings
│   ├── TEC.DWG.SCH - Schematics
│   ├── TEC.DWG.FLW - Flowcharts
│   └── TEC.DWG.ARC - Architecture Diagrams
└── TEC.RPT - Technical Reports
    ├── Test_Report
    ├── Analysis_Report
    └── Inspection_Report
```

### SCI - Scientific

```
SCI
├── SCI.PUB - Publications
│   ├── SCI.PUB.JRN - Journal Articles
│   ├── SCI.PUB.CNF - Conference Papers
│   ├── SCI.PUB.PRE - Preprints
│   └── SCI.PUB.REV - Review Articles
├── SCI.LAB - Lab Documents
│   ├── SCI.LAB.RPT - Lab Reports
│   ├── SCI.LAB.NOT - Lab Notebooks
│   └── SCI.LAB.PRO - Protocols
├── SCI.DAT - Data Documents
│   ├── SCI.DAT.TBL - Data Tables
│   ├── SCI.DAT.CHT - Charts/Graphs
│   └── SCI.DAT.STA - Statistical Reports
└── SCI.GRT - Grants & Proposals
    ├── Grant_Application
    ├── Research_Proposal
    └── Progress_Report
```

### ADM - Administrative

```
ADM
├── ADM.COR - Correspondence
│   ├── ADM.COR.LTR - Letters
│   ├── ADM.COR.MEM - Memos
│   ├── ADM.COR.EML - Printed Emails
│   └── ADM.COR.FAX - Fax Cover Sheets
├── ADM.HR - Human Resources
│   ├── ADM.HR.APP - Applications
│   │   ├── Job_Application
│   │   └── Resume
│   ├── ADM.HR.EMP - Employee Records
│   │   ├── Offer_Letter
│   │   ├── Performance_Review
│   │   └── Termination_Letter
│   └── ADM.HR.BEN - Benefits
│       ├── Benefits_Enrollment
│       └── Benefits_Summary
├── ADM.MTG - Meetings
│   ├── ADM.MTG.AGD - Agendas
│   ├── ADM.MTG.MIN - Minutes
│   └── ADM.MTG.PRE - Presentations
└── ADM.POL - Policies
    ├── Policy_Document
    ├── Procedure_Manual
    └── Handbook
```

### MED - Medical/Healthcare

```
MED
├── MED.PAT - Patient Records
│   ├── MED.PAT.HIS - Medical History
│   ├── MED.PAT.PRO - Progress Notes
│   ├── MED.PAT.DIS - Discharge Summary
│   └── MED.PAT.CON - Consent Forms
├── MED.RX - Prescriptions
│   ├── MED.RX.STD - Standard Prescription
│   ├── MED.RX.REF - Refill Request
│   └── MED.RX.PRE - Prior Authorization
├── MED.LAB - Lab Results
│   ├── MED.LAB.BLD - Blood Work
│   ├── MED.LAB.IMG - Imaging Reports
│   └── MED.LAB.PAT - Pathology Reports
├── MED.INS - Insurance
│   ├── MED.INS.CLM - Claim Forms
│   ├── MED.INS.EOB - EOB
│   └── MED.INS.PRE - Pre-authorization
└── MED.REG - Regulatory
    ├── HIPAA_Forms
    └── Compliance_Documents
```

### EDU - Educational

```
EDU
├── EDU.ACD - Academic
│   ├── EDU.ACD.TXT - Textbook Pages
│   ├── EDU.ACD.SYL - Syllabi
│   ├── EDU.ACD.LEC - Lecture Notes
│   └── EDU.ACD.HND - Handouts
├── EDU.ASS - Assessments
│   ├── EDU.ASS.EXM - Exams
│   ├── EDU.ASS.QIZ - Quizzes
│   ├── EDU.ASS.HW - Homework
│   └── EDU.ASS.GRD - Graded Papers
├── EDU.REC - Records
│   ├── EDU.REC.TRS - Transcripts
│   ├── EDU.REC.RPT - Report Cards
│   └── EDU.REC.ATT - Attendance Records
└── EDU.CRT - Certificates
    ├── Diploma
    ├── Degree_Certificate
    └── Training_Certificate
```

### PER - Personal

```
PER
├── PER.ID - Identity Documents
│   ├── PER.ID.DL - Driver's License
│   ├── PER.ID.PSP - Passport
│   ├── PER.ID.SSN - Social Security Card
│   └── PER.ID.BC - Birth Certificate
├── PER.CRT - Certificates
│   ├── PER.CRT.MAR - Marriage Certificate
│   ├── PER.CRT.DTH - Death Certificate
│   └── PER.CRT.NAT - Naturalization Certificate
├── PER.COR - Correspondence
│   ├── PER.COR.LTR - Personal Letters
│   ├── PER.COR.CRD - Cards
│   └── PER.COR.INV - Invitations
└── PER.FIN - Personal Finance
    ├── PER.FIN.BIL - Bills
    ├── PER.FIN.BGT - Budgets
    └── PER.FIN.WRN - Warranties
```

---

## Structure Taxonomy (Axis 2)

Documents are also classified by their structural characteristics:

### Text Density

| Level | Code | Characteristics | Example Documents |
|-------|------|-----------------|-------------------|
| **Sparse** | `SPR` | <30% text coverage, mostly whitespace/images | Forms (empty), ID cards, certificates |
| **Moderate** | `MOD` | 30-70% text coverage, balanced layout | Business letters, invoices, receipts |
| **Dense** | `DNS` | >70% text coverage, minimal whitespace | Legal contracts, research papers, textbooks |

### Layout Type

| Type | Code | Characteristics | Example Documents |
|------|------|-----------------|-------------------|
| **Single Column** | `1COL` | Linear top-to-bottom flow | Letters, memos, simple reports |
| **Multi-Column** | `MCOL` | 2+ columns, complex reading order | Newspapers, magazines, academic papers |
| **Mixed** | `MIX` | Combination of layouts | Technical manuals, textbooks |
| **Form-Based** | `FORM` | Structured fields, boxes, checkboxes | Tax forms, applications, surveys |
| **Tabular** | `TBL` | Primarily table-structured | Spreadsheets, ledgers, statements |

### Element Types (multi-select)

| Element | Code | Detection Priority |
|---------|------|-------------------|
| **Tables** | `TBL` | P0 - Critical |
| **Figures/Images** | `FIG` | P0 - Critical |
| **Charts/Graphs** | `CHT` | P1 - High |
| **Diagrams** | `DGM` | P1 - High |
| **Photographs** | `PHO` | P1 - High |
| **Formulas/Equations** | `EQN` | P1 - High |
| **Handwriting** | `HW` | P1 - High |
| **Signatures** | `SIG` | P2 - Medium |
| **Stamps/Seals** | `STP` | P2 - Medium |
| **Logos** | `LGO` | P3 - Low |
| **Barcodes/QR** | `BAR` | P2 - Medium |

---

## Production Method Taxonomy (Axis 3)

| Method | Code | Era | Expected Quality |
|--------|------|-----|------------------|
| **Born Digital** | `BD` | 2000-present | High - minimal degradation |
| **Printed Modern** | `PM` | 1990-present | Medium - occasional artifacts |
| **Printed Legacy** | `PL` | 1970-1990 | Variable - dot matrix, early laser |
| **Typewritten** | `TW` | 1900-1980 | Variable - key strike variations |
| **Handwritten Cursive** | `HC` | Any | Low - OCR challenging |
| **Handwritten Print** | `HP` | Any | Medium - block letters more readable |
| **Mixed** | `MX` | Any | Variable - multiple methods |

### Handwriting Percentage

| Range | Code | Training Considerations |
|-------|------|------------------------|
| 0% | `HW0` | Pure printed/typed |
| 1-25% | `HW25` | Primarily printed with annotations |
| 26-50% | `HW50` | Significant handwriting presence |
| 51-75% | `HW75` | Primarily handwritten with printed sections |
| 76-100% | `HW100` | Fully or mostly handwritten |

---

## Coverage Matrix: Domain × Capture Method

This matrix tracks dataset coverage for critical domain/capture combinations:

| Domain | Born Digital | Scanner Flatbed | Scanner ADF | Camera Pro | Smartphone | Fax |
|--------|--------------|-----------------|-------------|------------|------------|-----|
| TAX.IND | ● | ● | ● | ○ | ● | ● |
| TAX.BUS | ● | ● | ● | ○ | ○ | ● |
| LEG.CON | ● | ● | ● | ○ | ○ | ● |
| FIN.INV | ● | ● | ● | ● | ● | ○ |
| FIN.STM | ● | ● | ○ | ○ | ● | ○ |
| TEC.MAN | ● | ○ | ○ | ○ | ● | ○ |
| SCI.PUB | ● | ● | ○ | ○ | ○ | ○ |
| ADM.COR | ● | ● | ● | ○ | ● | ● |
| MED.PAT | ● | ● | ● | ○ | ● | ● |
| EDU.ACD | ● | ● | ○ | ● | ● | ○ |
| PER.ID | ○ | ● | ○ | ● | ● | ○ |

**Legend**: ● = adequate coverage (>1000 samples), ◐ = partial coverage (100-1000), ○ = gap (<100)

---

## Annotation Schema

### Document Type Annotation

```yaml
document:
  id: string

  domain:
    level1: enum[TAX, LEG, FIN, TEC, SCI, ADM, MED, EDU, PER]
    level2: string    # e.g., "TAX.IND", "LEG.CON"
    level3: string    # e.g., "TAX.IND.1040", "LEG.CON.EMP"
    level4: string    # e.g., "1040-SR", "NDA"
    confidence: float # 0.0-1.0

  structure:
    text_density: enum[sparse, moderate, dense]
    layout_type: enum[single_column, multi_column, mixed, form_based, tabular]
    element_types: list[string]  # Multi-select from element codes
    reading_order: enum[linear, non_linear, form_flow]

  production:
    method: enum[born_digital, printed_modern, printed_legacy,
                 typewritten, handwritten_cursive, handwritten_print, mixed]
    handwriting_percentage: enum[0, 1-25, 26-50, 51-75, 76-100]
    era: enum[contemporary, recent, late_20th_century, mid_20th_century, historical]
```

### Document Type Vector Format

For ML training, document types are encoded as a hierarchical vector:

```python
# Level 1 encoding (one-hot, 9 dimensions)
DOMAIN_L1_INDEX = {
    'TAX': 0, 'LEG': 1, 'FIN': 2, 'TEC': 3, 'SCI': 4,
    'ADM': 5, 'MED': 6, 'EDU': 7, 'PER': 8
}

# Structure encoding (multi-hot for element types)
STRUCTURE_INDEX = {
    'text_density_sparse': 0, 'text_density_moderate': 1, 'text_density_dense': 2,
    'layout_1col': 3, 'layout_mcol': 4, 'layout_mix': 5, 'layout_form': 6, 'layout_tbl': 7,
    'elem_table': 8, 'elem_figure': 9, 'elem_chart': 10, 'elem_diagram': 11,
    'elem_photo': 12, 'elem_formula': 13, 'elem_handwriting': 14, 'elem_signature': 15,
    'elem_stamp': 16, 'elem_logo': 17, 'elem_barcode': 18
}

# Production encoding
PRODUCTION_INDEX = {
    'born_digital': 0, 'printed_modern': 1, 'printed_legacy': 2,
    'typewritten': 3, 'handwritten_cursive': 4, 'handwritten_print': 5, 'mixed': 6,
    'hw_0': 7, 'hw_25': 8, 'hw_50': 9, 'hw_75': 10, 'hw_100': 11
}
```

---

## Integration with Detection Taxonomy

The document type taxonomy integrates with the [detection-taxonomy.md](detection-taxonomy.md) through:

1. **Expected Degradation Patterns**: Each domain/capture combination has expected degradation distributions
2. **Quality Baselines**: Different document types have different "acceptable" quality thresholds
3. **Routing Decisions**: Document type informs OCR routing strategy

### Domain-Specific Quality Expectations

| Domain | Typical Capture | Expected Degradations | Quality Threshold |
|--------|-----------------|----------------------|-------------------|
| TAX | Scanner ADF, Fax | Skew, compression, bleed-through | Moderate |
| LEG | Scanner Flatbed | Minimal | High |
| FIN.INV | Smartphone | Shadows, perspective, blur | Low |
| MED | Scanner ADF | Skew, fading, bleed-through | Moderate |
| PER.ID | Smartphone | Glare, perspective, shadows | Low |

---

## References

- [detection-taxonomy.md](detection-taxonomy.md): Degradation and capture method taxonomy
- [document-type-coverage.md](document-type-coverage.md): Dataset coverage by document type
- [DATASET_CATALOG.md](../DATASET_CATALOG.md): Complete dataset inventory

---

**Created**: 2025-12-17 (Phase 7 - Taxonomy Solidification)
**Status**: 🚧 **In Progress** - Initial taxonomy definition
**Next Steps**:

1. Validate taxonomy against existing dataset samples
2. Create automated document type classifier
3. Generate coverage reports for training data
**Next Review**: Phase 7 Week 2
