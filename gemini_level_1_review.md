# Gemini Review of Level 1 Architecture (index.md)

This document provides a critical analysis of the `docs/architecture/diagrams/level-1/index.md` file. It identifies potential gaps, ambiguities, and missing workflows in the described architecture for Project A.

## Summary of Findings

The Level 1 architecture document provides a good, high-level overview of the five interconnected workstreams. The separation of concerns between data preparation, labeling, and model training is clear and logical. However, several areas could be improved to create a more robust and complete architectural description.

## Recommendations and Potential Gaps

### 1. Clarify Production Inference Model

- **Observation:** The "Production Runtime" workstream description ambiguously lists "ML IQA (student/teacher)" as part of the quality analysis step. In a typical student-teacher paradigm, only the lightweight student model is deployed to production for efficiency.
- **Recommendation:** Explicitly state that only the **IQA Student model** is used for inference in the production runtime (Workstream 1). The IQA Teacher model should be confined to Workstream 2, where its role is to distill knowledge into the student model. This will remove ambiguity about the production environment's setup.

### 2. Introduce a Production Feedback Loop

- **Observation:** The "Workstream Data Flow" diagram presents a one-way flow from data preparation to production. There is no documented process for capturing data from the production environment for continuous improvement.
- **Recommendation:** Define a **"Feedback Loop"** workflow. This workflow should capture images and documents from the production runtime (Workstream 1) that are outliers, have low confidence scores, or are identified as incorrectly processed. This data should be funneled back into Workstream 3 (Data Preparation) for re-labeling (in Workstream 4) and eventual inclusion in future training datasets for Workstream 2. This creates a cycle of continuous learning and model improvement.

### 3. Address Undocumented "Labeling Model Training" Workstream

- **Observation:** The document explicitly states that the Level 2 documentation for "Workstream 5: Labeling Model Training" is **"Planned"**.
- **Recommendation:** Prioritize the creation of the Level 2 documentation for this workstream. This is a critical architectural dependency. Without it, the pseudo-labeling process (Workstream 4) lacks a clear foundation, which in turn impacts the entire production model training pipeline (Workstream 2).

### 4. Incorporate Model Monitoring and Experiment Tracking

- **Observation:** The architecture lacks any mention of monitoring production models or tracking ML experiments.
- **Recommendation:**
  - **Model Monitoring:** Add a "Model Monitoring" component to Workstream 1. This component should be responsible for tracking the performance of production models over time, detecting data and concept drift, and triggering alerts for performance degradation.
  - **Experiment Tracking:** Explicitly mention the use of an experiment tracking system (e.g., MLflow, DVC, Weights & Biases) for Workstreams 2 and 5. This is crucial for ensuring reproducibility, comparing model versions, and managing the model lifecycle.

### 5. Define Strategy for Expensive Labeling Models

- **Observation:** Workstream 4 (Pseudo-Labeling) proposes using large Vision Language Models (VLMs) like `Qwen3-VL-8B`. These models are powerful but have high computational costs.
- **Recommendation:** Briefly outline the strategy for using these VLMs at the Level 1 stage. For example, are they used for a one-time "bulk labeling" effort, or are they part of an ongoing, automated pipeline? Mentioning cost-control strategies (e.g., using smaller fine-tuned models, few-shot prompting) would strengthen the architectural description.

### 6. Elaborate on "Classification & Routing"

- **Observation:** The "Classification & Routing" component in Workstream 1 is vague. The terms "PDF type classification" and "text gate" are not self-explanatory.
- **Recommendation:** Provide a more descriptive summary of this component. For example, what types of PDFs are being classified (e.g., scanned, native text, portfolio)? What is the purpose of the "text gate"—does it route text-heavy documents to a different pipeline, bypassing IQA? A sentence or two of clarification would improve clarity.
