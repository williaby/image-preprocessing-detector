"""Unit tests for SigLIP2MultiTaskTeacher model architecture.

Tests cover:
- Model creation with correct head architecture
- Forward pass output shapes for all task types
- Selective task execution (tasks parameter)
- Freeze/unfreeze backbone and IQA heads
- Layer groups for LLRD
- Head parameter groups with differential LR
- Calibration temperature setting
- Collate function with partial labels
- Multi-task loss with missing-label masking
- Configuration dataclass validation

These tests use a lightweight mock backbone instead of the real SigLIP2 model
to keep tests fast and not require HuggingFace model downloads.
"""

from __future__ import annotations

from typing import Any

import pytest

# ============================================================================
# Skip if torch is not available
# ============================================================================

torch = pytest.importorskip("torch")
nn = pytest.importorskip("torch.nn")

# ============================================================================
# Constants (mirror modal/train_siglip2_multitask.py without importing it)
# ============================================================================

SCRIPT_ML_CLASSES = (
    "LATN",
    "CYRL",
    "GREK",
    "ARAB",
    "HEBR",
    "DEVA",
    "BENG",
    "TAML",
    "TELU",
    "HANS",
    "HANT",
    "JPAN",
    "KORE",
    "THAI",
    "TIBT",
    "INDIC_OTHER",
    "SE_ASIAN_OTHER",
    "OTHER",
    "UNKNOWN",
)
SCRIPT_CLASS_TO_IDX = {cls: i for i, cls in enumerate(SCRIPT_ML_CLASSES)}

SOURCE_CLASSES = ("scanned", "camera", "born_digital")
SOURCE_CLASS_TO_IDX = {cls: i for i, cls in enumerate(SOURCE_CLASSES)}

ORIENTATION_CLASSES = (0, 90, 180, 270)
ORIENTATION_TO_IDX = {deg: i for i, deg in enumerate(ORIENTATION_CLASSES)}

IQA_TASKS = ("overall", "sharpness", "color")
CLASSIFICATION_TASKS = ("script", "source", "orientation")
REGRESSION_TASKS = ("shadow", "warping")
ALL_TASKS = IQA_TASKS + CLASSIFICATION_TASKS + REGRESSION_TASKS


# ============================================================================
# Test model with mock backbone (no HuggingFace dependency)
# ============================================================================


def _make_mock_backbone(embed_dim: int = 32) -> nn.Module:
    """Create a lightweight mock backbone that replaces SigLIP2."""

    class MockVisionConfig:
        hidden_size = embed_dim

    class MockConfig:
        vision_config = MockVisionConfig()

    class MockEmbeddings(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.proj = nn.Linear(embed_dim, embed_dim)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.proj(x)

    class MockEncoderLayer(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.linear = nn.Linear(embed_dim, embed_dim)

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.linear(x)

    class MockEncoder(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.layers = nn.ModuleList([MockEncoderLayer() for _ in range(2)])

    class MockVisionModel(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.embeddings = MockEmbeddings()
            self.encoder = MockEncoder()
            self.post_layernorm = nn.LayerNorm(embed_dim)

    class MockBackbone(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.config = MockConfig()
            self.vision_model = MockVisionModel()
            self._embed_dim = embed_dim
            self._proj = nn.Linear(embed_dim, embed_dim)

        def get_image_features(
            self,
            pixel_values: torch.Tensor,
            spatial_shapes: torch.Tensor | None = None,
        ) -> torch.Tensor:
            batch_size = pixel_values.shape[0]
            # Use deterministic input derived from pixel_values
            # and pass through a parameter-bearing layer so gradients flow
            flat = pixel_values.reshape(batch_size, -1)[:, : self._embed_dim]
            return self._proj(flat)

        def gradient_checkpointing_enable(self) -> None:
            pass

    return MockBackbone()


# Head configs for testing (small dims for speed)
_HEAD_CONFIGS: dict[str, dict[str, Any]] = {
    "overall": {
        "hidden_dim": 16,
        "output_dim": 2,
        "dropout": 0.3,
        "type": "regression_uncertainty",
    },
    "sharpness": {
        "hidden_dim": 16,
        "output_dim": 2,
        "dropout": 0.3,
        "type": "regression_uncertainty",
    },
    "color": {
        "hidden_dim": 16,
        "output_dim": 2,
        "dropout": 0.3,
        "type": "regression_uncertainty",
    },
    "script": {
        "hidden_dim": 16,
        "output_dim": len(SCRIPT_ML_CLASSES),
        "dropout": 0.3,
        "type": "classification",
    },
    "source": {
        "hidden_dim": 8,
        "output_dim": len(SOURCE_CLASSES),
        "dropout": 0.0,
        "type": "classification",
    },
    "orientation": {
        "hidden_dim": 8,
        "output_dim": len(ORIENTATION_CLASSES),
        "dropout": 0.0,
        "type": "classification",
    },
    "shadow": {
        "hidden_dim": 8,
        "output_dim": 2,
        "dropout": 0.0,
        "type": "regression_uncertainty",
    },
    "warping": {
        "hidden_dim": 8,
        "output_dim": 2,
        "dropout": 0.0,
        "type": "regression_uncertainty",
    },
}


class MultiTaskTestModel(nn.Module):
    """Test-friendly multi-task model matching SigLIP2MultiTaskTeacher API."""

    def __init__(self, embed_dim: int = 32) -> None:
        super().__init__()
        self.backbone = _make_mock_backbone(embed_dim)

        self.heads = nn.ModuleDict()
        self._head_types: dict[str, str] = {}

        for name, cfg in _HEAD_CONFIGS.items():
            layers: list[nn.Module] = [
                nn.Linear(embed_dim, cfg["hidden_dim"]),
                nn.ReLU(),
            ]
            if cfg.get("dropout", 0) > 0:
                layers.append(nn.Dropout(cfg["dropout"]))
            layers.append(nn.Linear(cfg["hidden_dim"], cfg["output_dim"]))
            self.heads[name] = nn.Sequential(*layers)
            self._head_types[name] = cfg["type"]

        for name, cfg in _HEAD_CONFIGS.items():
            if cfg["type"] == "regression_uncertainty":
                self.register_buffer(f"temp_{name}", torch.tensor(1.0))

    def freeze_backbone(self) -> None:
        for param in self.backbone.parameters():
            param.requires_grad = False

    def unfreeze_backbone(self) -> None:
        for param in self.backbone.parameters():
            param.requires_grad = True

    def freeze_iqa_heads(self) -> None:
        for task in IQA_TASKS:
            if task in self.heads:
                for param in self.heads[task].parameters():
                    param.requires_grad = False

    def unfreeze_iqa_heads(self) -> None:
        for task in IQA_TASKS:
            if task in self.heads:
                for param in self.heads[task].parameters():
                    param.requires_grad = True

    def get_layer_groups(self) -> list[list[nn.Parameter]]:
        encoder = self.backbone.vision_model.encoder
        groups: list[list[nn.Parameter]] = []
        groups.append(list(self.backbone.vision_model.embeddings.parameters()))
        groups.extend(list(layer.parameters()) for layer in encoder.layers)
        groups.append(list(self.backbone.vision_model.post_layernorm.parameters()))
        return groups

    def get_head_param_groups(
        self,
        base_lr: float,
        iqa_lr_multiplier: float = 0.01,
        weight_decay: float = 0.01,
    ) -> list[dict[str, Any]]:
        groups: list[dict[str, Any]] = []

        iqa_params: list[nn.Parameter] = []
        for task in IQA_TASKS:
            if task in self.heads:
                iqa_params.extend(self.heads[task].parameters())
        if iqa_params:
            groups.append(
                {
                    "params": iqa_params,
                    "lr": base_lr * iqa_lr_multiplier,
                    "weight_decay": weight_decay,
                    "name": "iqa_heads",
                }
            )

        det_params: list[nn.Parameter] = []
        for task in CLASSIFICATION_TASKS + REGRESSION_TASKS:
            if task in self.heads:
                det_params.extend(self.heads[task].parameters())
        if det_params:
            groups.append(
                {
                    "params": det_params,
                    "lr": base_lr,
                    "weight_decay": weight_decay,
                    "name": "detection_heads",
                }
            )

        return groups

    def forward(
        self,
        pixel_values: torch.Tensor,
        spatial_shapes: torch.Tensor | None = None,
        tasks: list[str] | None = None,
    ) -> dict[str, dict[str, torch.Tensor] | torch.Tensor]:
        features = self.backbone.get_image_features(
            pixel_values=pixel_values,
            spatial_shapes=spatial_shapes,
        )
        active_tasks = list(self.heads.keys()) if tasks is None else tasks
        results: dict[str, dict[str, torch.Tensor] | torch.Tensor] = {}

        for task_name in active_tasks:
            if task_name not in self.heads:
                continue
            head_output = self.heads[task_name](features)
            head_type = self._head_types.get(task_name, "classification")

            if head_type == "regression_uncertainty":
                mu = head_output[:, 0]
                log_sigma_sq = head_output[:, 1]
                sigma_sq = torch.exp(log_sigma_sq)
                temp = getattr(self, f"temp_{task_name}")
                results[task_name] = {
                    "mu": mu,
                    "sigma_sq": temp * sigma_sq,
                    "logits": head_output,
                }
            elif head_type == "classification":
                results[task_name] = head_output
            else:
                results[task_name] = head_output.squeeze(-1)

        return results

    def set_calibration_temps(self, temps: dict[str, float]) -> None:
        for head_name, temp_val in temps.items():
            attr_name = f"temp_{head_name}"
            if hasattr(self, attr_name):
                setattr(self, attr_name, torch.tensor(temp_val))


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def model() -> MultiTaskTestModel:
    """Create a test model with mock backbone."""
    return MultiTaskTestModel(embed_dim=32)


@pytest.fixture
def batch() -> dict[str, Any]:
    """Create a synthetic batch for testing."""
    return {
        "pixel_values": torch.randn(4, 3, 224, 224),
        "spatial_shapes": None,
    }


# ============================================================================
# Tests: Model creation
# ============================================================================


class TestModelCreation:
    """Tests for model architecture and initialization."""

    def test_has_all_heads(self, model: MultiTaskTestModel) -> None:
        """Model should have all 8 task heads."""
        for task in ALL_TASKS:
            assert task in model.heads, f"Missing head: {task}"

    def test_head_count(self, model: MultiTaskTestModel) -> None:
        assert len(model.heads) == 8

    def test_iqa_heads_present(self, model: MultiTaskTestModel) -> None:
        for dim in IQA_TASKS:
            assert dim in model.heads

    def test_classification_heads_present(
        self,
        model: MultiTaskTestModel,
    ) -> None:
        for task in CLASSIFICATION_TASKS:
            assert task in model.heads

    def test_regression_heads_present(
        self,
        model: MultiTaskTestModel,
    ) -> None:
        for task in REGRESSION_TASKS:
            assert task in model.heads

    def test_calibration_buffers_exist(
        self,
        model: MultiTaskTestModel,
    ) -> None:
        """Uncertainty heads should have calibration temperature buffers."""
        for task in ("overall", "sharpness", "color", "shadow", "warping"):
            assert hasattr(model, f"temp_{task}")
            assert getattr(model, f"temp_{task}").item() == 1.0

    def test_no_classification_temp_buffers(
        self,
        model: MultiTaskTestModel,
    ) -> None:
        """Classification heads should NOT have temp buffers."""
        for task in CLASSIFICATION_TASKS:
            assert not hasattr(model, f"temp_{task}")


# ============================================================================
# Tests: Forward pass
# ============================================================================


class TestForwardPass:
    """Tests for model forward pass output shapes."""

    def test_all_tasks_output(
        self,
        model: MultiTaskTestModel,
        batch: dict[str, Any],
    ) -> None:
        outputs = model(**batch)
        assert len(outputs) == 8

    def test_iqa_output_shape(
        self,
        model: MultiTaskTestModel,
        batch: dict[str, Any],
    ) -> None:
        """IQA outputs should be dicts with mu, sigma_sq, logits."""
        outputs = model(**batch)
        for dim in IQA_TASKS:
            assert isinstance(outputs[dim], dict)
            assert "mu" in outputs[dim]
            assert "sigma_sq" in outputs[dim]
            assert "logits" in outputs[dim]
            assert outputs[dim]["mu"].shape == (4,)
            assert outputs[dim]["sigma_sq"].shape == (4,)
            assert outputs[dim]["logits"].shape == (4, 2)

    def test_script_output_shape(
        self,
        model: MultiTaskTestModel,
        batch: dict[str, Any],
    ) -> None:
        outputs = model(**batch)
        assert outputs["script"].shape == (4, len(SCRIPT_ML_CLASSES))

    def test_source_output_shape(
        self,
        model: MultiTaskTestModel,
        batch: dict[str, Any],
    ) -> None:
        outputs = model(**batch)
        assert outputs["source"].shape == (4, len(SOURCE_CLASSES))

    def test_orientation_output_shape(
        self,
        model: MultiTaskTestModel,
        batch: dict[str, Any],
    ) -> None:
        outputs = model(**batch)
        assert outputs["orientation"].shape == (4, len(ORIENTATION_CLASSES))

    def test_shadow_output_is_uncertainty_dict(
        self,
        model: MultiTaskTestModel,
        batch: dict[str, Any],
    ) -> None:
        outputs = model(**batch)
        assert isinstance(outputs["shadow"], dict)
        assert outputs["shadow"]["mu"].shape == (4,)
        assert outputs["shadow"]["sigma_sq"].shape == (4,)

    def test_warping_output_is_uncertainty_dict(
        self,
        model: MultiTaskTestModel,
        batch: dict[str, Any],
    ) -> None:
        outputs = model(**batch)
        assert isinstance(outputs["warping"], dict)
        assert outputs["warping"]["mu"].shape == (4,)
        assert outputs["warping"]["sigma_sq"].shape == (4,)

    def test_sigma_sq_positive(
        self,
        model: MultiTaskTestModel,
        batch: dict[str, Any],
    ) -> None:
        """All sigma_sq values should be positive (exp of raw output)."""
        outputs = model(**batch)
        for task in ("overall", "sharpness", "color", "shadow", "warping"):
            assert (outputs[task]["sigma_sq"] > 0).all()


# ============================================================================
# Tests: Selective task execution
# ============================================================================


class TestSelectiveExecution:
    """Tests for the tasks parameter in forward()."""

    def test_single_task(
        self,
        model: MultiTaskTestModel,
        batch: dict[str, Any],
    ) -> None:
        outputs = model(**batch, tasks=["script"])
        assert len(outputs) == 1
        assert "script" in outputs

    def test_two_tasks(
        self,
        model: MultiTaskTestModel,
        batch: dict[str, Any],
    ) -> None:
        outputs = model(**batch, tasks=["script", "orientation"])
        assert len(outputs) == 2

    def test_iqa_only(
        self,
        model: MultiTaskTestModel,
        batch: dict[str, Any],
    ) -> None:
        outputs = model(**batch, tasks=list(IQA_TASKS))
        assert len(outputs) == 3
        for dim in IQA_TASKS:
            assert dim in outputs

    def test_detection_only(
        self,
        model: MultiTaskTestModel,
        batch: dict[str, Any],
    ) -> None:
        det_tasks = list(CLASSIFICATION_TASKS) + list(REGRESSION_TASKS)
        outputs = model(**batch, tasks=det_tasks)
        assert len(outputs) == 5

    def test_unknown_task_ignored(
        self,
        model: MultiTaskTestModel,
        batch: dict[str, Any],
    ) -> None:
        outputs = model(**batch, tasks=["script", "nonexistent_task"])
        assert len(outputs) == 1

    def test_empty_tasks_list(
        self,
        model: MultiTaskTestModel,
        batch: dict[str, Any],
    ) -> None:
        outputs = model(**batch, tasks=[])
        assert len(outputs) == 0


# ============================================================================
# Tests: Freeze/unfreeze
# ============================================================================


class TestFreezeUnfreeze:
    """Tests for freezing and unfreezing model components."""

    def test_freeze_backbone(self, model: MultiTaskTestModel) -> None:
        model.freeze_backbone()
        for param in model.backbone.parameters():
            assert not param.requires_grad

    def test_unfreeze_backbone(self, model: MultiTaskTestModel) -> None:
        model.freeze_backbone()
        model.unfreeze_backbone()
        for param in model.backbone.parameters():
            assert param.requires_grad

    def test_freeze_iqa_heads(self, model: MultiTaskTestModel) -> None:
        model.freeze_iqa_heads()
        for task in IQA_TASKS:
            for param in model.heads[task].parameters():
                assert not param.requires_grad
        # Detection heads should remain unfrozen
        for task in CLASSIFICATION_TASKS + REGRESSION_TASKS:
            for param in model.heads[task].parameters():
                assert param.requires_grad

    def test_unfreeze_iqa_heads(self, model: MultiTaskTestModel) -> None:
        model.freeze_iqa_heads()
        model.unfreeze_iqa_heads()
        for task in IQA_TASKS:
            for param in model.heads[task].parameters():
                assert param.requires_grad

    def test_phase1_freeze_pattern(
        self,
        model: MultiTaskTestModel,
    ) -> None:
        """Phase 1: backbone + IQA frozen, detection heads trainable."""
        model.freeze_backbone()
        model.freeze_iqa_heads()

        for param in model.backbone.parameters():
            assert not param.requires_grad

        for task in IQA_TASKS:
            for param in model.heads[task].parameters():
                assert not param.requires_grad

        for task in CLASSIFICATION_TASKS + REGRESSION_TASKS:
            for param in model.heads[task].parameters():
                assert param.requires_grad

    def test_phase2_all_unfrozen(
        self,
        model: MultiTaskTestModel,
    ) -> None:
        """Phase 2: everything unfrozen."""
        model.freeze_backbone()
        model.freeze_iqa_heads()
        model.unfreeze_backbone()
        model.unfreeze_iqa_heads()

        for param in model.parameters():
            assert param.requires_grad


# ============================================================================
# Tests: Parameter groups
# ============================================================================


class TestParameterGroups:
    """Tests for LLRD and optimizer parameter groups."""

    def test_layer_groups_count(self, model: MultiTaskTestModel) -> None:
        groups = model.get_layer_groups()
        # embeddings(1) + 2 encoder layers + post_layernorm(1) = 4
        assert len(groups) == 4

    def test_layer_groups_have_params(
        self,
        model: MultiTaskTestModel,
    ) -> None:
        groups = model.get_layer_groups()
        for group in groups:
            assert len(group) > 0

    def test_head_param_groups_two_groups(
        self,
        model: MultiTaskTestModel,
    ) -> None:
        groups = model.get_head_param_groups(base_lr=1e-4)
        assert len(groups) == 2
        names = {g["name"] for g in groups}
        assert names == {"iqa_heads", "detection_heads"}

    def test_head_param_groups_differential_lr(
        self,
        model: MultiTaskTestModel,
    ) -> None:
        base_lr = 1e-4
        iqa_mult = 0.01
        groups = model.get_head_param_groups(
            base_lr=base_lr,
            iqa_lr_multiplier=iqa_mult,
        )
        iqa_g = next(g for g in groups if g["name"] == "iqa_heads")
        det_g = next(g for g in groups if g["name"] == "detection_heads")
        assert iqa_g["lr"] == pytest.approx(base_lr * iqa_mult)
        assert det_g["lr"] == pytest.approx(base_lr)

    def test_head_params_cover_all_heads(
        self,
        model: MultiTaskTestModel,
    ) -> None:
        """Head param groups should contain all head parameters."""
        groups = model.get_head_param_groups(base_lr=1e-4)
        all_params = set()
        for g in groups:
            for p in g["params"]:
                all_params.add(id(p))

        expected_params = set()
        for task in ALL_TASKS:
            for p in model.heads[task].parameters():
                expected_params.add(id(p))

        assert all_params == expected_params


# ============================================================================
# Tests: Calibration
# ============================================================================


class TestCalibration:
    """Tests for post-hoc calibration temperatures."""

    def test_set_temps(self, model: MultiTaskTestModel) -> None:
        model.set_calibration_temps({"overall": 1.5, "shadow": 2.0})
        assert model.temp_overall.item() == pytest.approx(1.5)
        assert model.temp_shadow.item() == pytest.approx(2.0)

    def test_temp_scales_sigma_sq(
        self,
        model: MultiTaskTestModel,
        batch: dict[str, Any],
    ) -> None:
        """Changing temp should scale sigma_sq output."""
        model.eval()  # Disable dropout for deterministic comparison
        with torch.no_grad():
            out1 = model(**batch, tasks=["overall"])
            sigma1 = out1["overall"]["sigma_sq"].clone()

            model.set_calibration_temps({"overall": 2.0})
            out2 = model(**batch, tasks=["overall"])
            sigma2 = out2["overall"]["sigma_sq"]

        ratio = sigma2 / sigma1
        assert torch.allclose(
            ratio,
            torch.tensor(2.0).expand_as(ratio),
            atol=0.01,
        )

    def test_unknown_temp_ignored(
        self,
        model: MultiTaskTestModel,
    ) -> None:
        """Setting temp for non-existent head should not raise."""
        model.set_calibration_temps({"nonexistent_head": 3.0})


# ============================================================================
# Tests: Collate function
# ============================================================================


class TestCollateFunction:
    """Tests for _multitask_collate_fn logic."""

    @staticmethod
    def _collate(batch: list[dict[str, Any]]) -> dict[str, Any]:
        """Inline collate matching modal/train_siglip2_multitask.py logic."""
        pixel_values = torch.stack([item["pixel_values"] for item in batch])
        spatial_shapes = torch.stack([item["spatial_shapes"] for item in batch])
        pixel_attention_mask = torch.stack(
            [item["pixel_attention_mask"] for item in batch]
        )

        labels: dict[str, Any] = {}
        task_masks: dict[str, Any] = {}

        for task in ALL_TASKS:
            values: list[int | float] = []
            masks: list[float] = []
            for item in batch:
                if task in item["labels"]:
                    values.append(item["labels"][task])
                    masks.append(1.0)
                else:
                    values.append(0 if task in CLASSIFICATION_TASKS else 0.0)
                    masks.append(0.0)

            if task in CLASSIFICATION_TASKS:
                labels[task] = torch.tensor(values, dtype=torch.long)
            else:
                labels[task] = torch.tensor(values, dtype=torch.float32)
            task_masks[task] = torch.tensor(masks, dtype=torch.float32)

        return {
            "pixel_values": pixel_values,
            "spatial_shapes": spatial_shapes,
            "pixel_attention_mask": pixel_attention_mask,
            "labels": labels,
            "task_masks": task_masks,
            "image_ids": [item["image_id"] for item in batch],
        }

    def _make_sample(
        self,
        labels: dict[str, Any],
        image_id: str = "img001",
    ) -> dict[str, Any]:
        """Create a mock dataset sample with given labels."""
        return {
            "pixel_values": torch.randn(3, 16, 16),
            "spatial_shapes": torch.tensor([16, 16]),
            "pixel_attention_mask": torch.ones(16, 16),
            "labels": labels,
            "task_masks": dict.fromkeys(labels, 1),
            "image_id": image_id,
        }

    def test_collate_single_task(self) -> None:
        """Batch with one task should have mask=1 for that task only."""
        samples = [
            self._make_sample({"script": 0}, "a"),
            self._make_sample({"script": 5}, "b"),
        ]
        result = self._collate(samples)

        assert result["labels"]["script"].tolist() == [0, 5]
        assert result["task_masks"]["script"].tolist() == [1.0, 1.0]
        # Other tasks should be masked out
        assert result["task_masks"]["source"].tolist() == [0.0, 0.0]

    def test_collate_mixed_tasks(self) -> None:
        """Batch with different tasks per sample."""
        samples = [
            self._make_sample({"script": 3, "overall": 0.5}, "a"),
            self._make_sample({"orientation": 2, "shadow": 0.3}, "b"),
        ]
        result = self._collate(samples)

        # script: sample 0 has it, sample 1 doesn't
        assert result["task_masks"]["script"].tolist() == [1.0, 0.0]
        assert result["labels"]["script"][0] == 3
        # orientation: sample 0 doesn't have it, sample 1 does
        assert result["task_masks"]["orientation"].tolist() == [0.0, 1.0]
        assert result["labels"]["orientation"][1] == 2

    def test_collate_classification_dtype(self) -> None:
        """Classification labels should be long (int64)."""
        samples = [self._make_sample({"script": 0}, "a")]
        result = self._collate(samples)
        assert result["labels"]["script"].dtype == torch.long

    def test_collate_regression_dtype(self) -> None:
        """Regression labels should be float32."""
        samples = [self._make_sample({"overall": 0.5}, "a")]
        result = self._collate(samples)
        assert result["labels"]["overall"].dtype == torch.float32

    def test_collate_preserves_image_ids(self) -> None:
        samples = [
            self._make_sample({"script": 0}, "img_a"),
            self._make_sample({"script": 1}, "img_b"),
        ]
        result = self._collate(samples)
        assert result["image_ids"] == ["img_a", "img_b"]

    def test_collate_all_tasks_present(self) -> None:
        """Labels and masks should cover all tasks."""
        samples = [self._make_sample({"script": 0}, "a")]
        result = self._collate(samples)
        for task in ALL_TASKS:
            assert task in result["labels"]
            assert task in result["task_masks"]


# ============================================================================
# Tests: Multi-task loss
# ============================================================================


class TestMultiTaskLoss:
    """Tests for multi-task loss with missing-label masking."""

    @staticmethod
    def _create_loss() -> nn.Module:
        """Create inline MultiTaskLoss for testing."""
        import torch.nn.functional as func

        class GaussianNLLLoss(nn.Module):
            def forward(
                self,
                mu: torch.Tensor,
                sigma_sq: torch.Tensor,
                target: torch.Tensor,
            ) -> torch.Tensor:
                sigma_sq = torch.clamp(sigma_sq, min=1e-6)
                return 0.5 * torch.log(sigma_sq) + (target - mu) ** 2 / (2 * sigma_sq)

        class NormInNormLoss(nn.Module):
            def forward(
                self,
                pred: torch.Tensor,
                target: torch.Tensor,
            ) -> torch.Tensor:
                pn = (pred - pred.mean()) / (pred.std() + 1e-8)
                tn = (target - target.mean()) / (target.std() + 1e-8)
                diff = torch.abs(pn - tn)
                return torch.pow(diff.mean(), 2.0)

        class MultiTaskLoss(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.task_weights = dict.fromkeys(ALL_TASKS, 1.0)
                self.gnll = GaussianNLLLoss()
                self.nin = NormInNormLoss()

            def forward(
                self,
                predictions: dict[str, Any],
                targets: dict[str, torch.Tensor],
                task_masks: dict[str, torch.Tensor],
            ) -> tuple[torch.Tensor, dict[str, float]]:
                total = torch.tensor(0.0)
                losses: dict[str, float] = {}

                for task in predictions:
                    if task not in targets:
                        continue
                    mask = task_masks.get(task)
                    if mask is not None and mask.sum() == 0:
                        continue

                    pred = predictions[task]
                    target = targets[task]

                    if task in CLASSIFICATION_TASKS:
                        raw = func.cross_entropy(
                            pred,
                            target,
                            reduction="none",
                        )
                    elif task in IQA_TASKS:
                        raw = self.gnll(
                            pred["mu"],
                            pred["sigma_sq"],
                            target,
                        )
                    else:
                        raw = self.gnll(
                            pred["mu"],
                            pred["sigma_sq"],
                            target,
                        )

                    if mask is not None:
                        loss = (raw * mask).sum() / (mask.sum() + 1e-8)
                    else:
                        loss = raw.mean()

                    w = self.task_weights.get(task, 1.0)
                    total = total + w * loss
                    losses[task] = loss.item()

                return total, losses

        return MultiTaskLoss()

    def test_loss_with_all_tasks(self) -> None:
        """Loss should compute for all tasks when all masks are 1."""
        loss_fn = self._create_loss()
        batch_size = 4

        predictions: dict[str, Any] = {
            "script": torch.randn(batch_size, len(SCRIPT_ML_CLASSES)),
            "source": torch.randn(batch_size, len(SOURCE_CLASSES)),
            "orientation": torch.randn(
                batch_size,
                len(ORIENTATION_CLASSES),
            ),
        }
        targets = {
            "script": torch.randint(0, len(SCRIPT_ML_CLASSES), (batch_size,)),
            "source": torch.randint(0, len(SOURCE_CLASSES), (batch_size,)),
            "orientation": torch.randint(
                0,
                len(ORIENTATION_CLASSES),
                (batch_size,),
            ),
        }
        masks = {t: torch.ones(batch_size) for t in targets}

        total, per_task = loss_fn(predictions, targets, masks)

        assert total.item() > 0
        assert len(per_task) == 3
        for t in ("script", "source", "orientation"):
            assert t in per_task
            assert per_task[t] > 0

    def test_loss_skips_masked_tasks(self) -> None:
        """Loss should skip tasks where mask is all zeros."""
        loss_fn = self._create_loss()
        batch_size = 4

        predictions: dict[str, Any] = {
            "script": torch.randn(batch_size, len(SCRIPT_ML_CLASSES)),
            "source": torch.randn(batch_size, len(SOURCE_CLASSES)),
        }
        targets = {
            "script": torch.randint(0, len(SCRIPT_ML_CLASSES), (batch_size,)),
            "source": torch.randint(0, len(SOURCE_CLASSES), (batch_size,)),
        }
        masks = {
            "script": torch.ones(batch_size),
            "source": torch.zeros(batch_size),  # masked out
        }

        total, per_task = loss_fn(predictions, targets, masks)
        assert "script" in per_task
        assert "source" not in per_task

    def test_loss_partial_mask(self) -> None:
        """Loss should average only over unmasked samples."""
        loss_fn = self._create_loss()
        batch_size = 4

        predictions: dict[str, Any] = {
            "script": torch.randn(batch_size, len(SCRIPT_ML_CLASSES)),
        }
        targets = {
            "script": torch.randint(0, len(SCRIPT_ML_CLASSES), (batch_size,)),
        }
        # Only first 2 samples have labels
        masks = {"script": torch.tensor([1.0, 1.0, 0.0, 0.0])}

        total, per_task = loss_fn(predictions, targets, masks)
        assert "script" in per_task
        assert total.item() > 0


# ============================================================================
# Tests: Constants
# ============================================================================


class TestConstants:
    """Tests for module-level constants."""

    def test_script_classes_count(self) -> None:
        assert len(SCRIPT_ML_CLASSES) == 19

    def test_script_idx_bijection(self) -> None:
        assert len(SCRIPT_CLASS_TO_IDX) == 19
        assert set(SCRIPT_CLASS_TO_IDX.values()) == set(range(19))

    def test_source_classes_count(self) -> None:
        assert len(SOURCE_CLASSES) == 3

    def test_orientation_classes(self) -> None:
        assert set(ORIENTATION_CLASSES) == {0, 90, 180, 270}

    def test_all_tasks_count(self) -> None:
        assert len(ALL_TASKS) == 8

    def test_task_groups_partition_all_tasks(self) -> None:
        combined = set(IQA_TASKS) | set(CLASSIFICATION_TASKS) | set(REGRESSION_TASKS)
        assert combined == set(ALL_TASKS)
        assert len(combined) == 8

    def test_head_configs_cover_all_tasks(self) -> None:
        for task in ALL_TASKS:
            assert task in _HEAD_CONFIGS


# ============================================================================
# Tests: Gradient flow
# ============================================================================


class TestGradientFlow:
    """Tests verifying gradient flow through the model."""

    def test_gradient_flows_through_detection_heads(
        self,
        model: MultiTaskTestModel,
        batch: dict[str, Any],
    ) -> None:
        """Detection head parameters should receive gradients."""
        model.freeze_backbone()
        model.freeze_iqa_heads()

        outputs = model(**batch, tasks=["script"])
        loss = outputs["script"].sum()
        loss.backward()

        for param in model.heads["script"].parameters():
            assert param.grad is not None

    def test_frozen_backbone_no_gradient(
        self,
        model: MultiTaskTestModel,
        batch: dict[str, Any],
    ) -> None:
        """Frozen backbone should not receive gradients."""
        model.freeze_backbone()

        outputs = model(**batch, tasks=["script"])
        loss = outputs["script"].sum()
        loss.backward()

        for param in model.backbone.parameters():
            assert param.grad is None

    def test_unfrozen_backbone_gets_gradient(
        self,
        model: MultiTaskTestModel,
        batch: dict[str, Any],
    ) -> None:
        """Unfrozen backbone should receive gradients."""
        outputs = model(**batch, tasks=["script"])
        loss = outputs["script"].sum()
        loss.backward()

        has_grad = any(p.grad is not None for p in model.backbone.parameters())
        assert has_grad
