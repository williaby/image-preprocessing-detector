"""Project C: Fine-Tuning & Label Generation.

This module provides training pipelines for DIQA-5000 fine-tuning and
DIQA-style label generation for external datasets.

Project C is the only workstream that performs learning - no benchmarking
or quantization is done here.

Key Components:
    - DIQATrainer: Main training loop with PEFT/LoRA
    - LabelGenerator: Generate DIQA scores for external datasets
    - ModelCardGenerator: Create model cards for trained artifacts

Example:
    >>> from image_preprocessing_detector.labeling.finetuning import DIQATrainer
    >>>
    >>> config = DIQATrainingConfig(
    ...     base_model="meta-llama/Llama-4-Maverick",
    ...     peft_method="lora",
    ...     output_dir="./checkpoints/",
    ... )
    >>> trainer = DIQATrainer(config)
    >>> result = trainer.train(train_dataset, val_dataset)
"""

__all__: list[str] = []
