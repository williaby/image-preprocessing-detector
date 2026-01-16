# SPDX-FileCopyrightText: 2026 Byron Williams <byronawilliams@gmail.com>
#
# SPDX-License-Identifier: MIT

"""Simplified PCGrad optimizer wrapper.

PCGrad (Projected Conflicting Gradients) mitigates gradient conflicts
in multi-task learning by projecting conflicting gradients.

Reference: Yu et al., "Gradient Surgery for Multi-Task Learning", NeurIPS 2020
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import torch

if TYPE_CHECKING:
    from torch import Tensor
    from torch.optim import Optimizer


class PCGrad:
    """PCGrad optimizer wrapper for multi-task learning.

    Simplified implementation that projects conflicting gradients onto
    the normal plane of each other, allowing non-conflicting components
    to pass through.
    """

    def __init__(self, optimizer: Optimizer) -> None:
        """Initialize PCGrad wrapper.

        Args:
            optimizer: Base optimizer (e.g., Adam, AdamW)
        """
        self._optimizer = optimizer
        self.param_groups = optimizer.param_groups

    def zero_grad(self) -> None:
        """Clear gradients."""
        self._optimizer.zero_grad()

    def step(self) -> None:
        """Optimization step."""
        self._optimizer.step()

    def state_dict(self) -> dict[str, object]:
        """Return optimizer state."""
        return dict(self._optimizer.state_dict())

    def load_state_dict(self, state_dict: dict) -> None:
        """Load optimizer state."""
        self._optimizer.load_state_dict(state_dict)

    def pc_backward(self, losses: list[Tensor]) -> None:
        """Backward pass with gradient projection.

        Args:
            losses: List of losses, one per task [loss1, loss2, loss3]
        """
        # Compute gradients for each task
        grads_task = []

        for i, loss in enumerate(losses):
            # Zero gradients before each backward
            self._optimizer.zero_grad()

            # Compute gradients for this task
            loss.backward(retain_graph=(i < len(losses) - 1))

            # Collect gradients for all parameters
            task_grads = []
            for group in self._optimizer.param_groups:
                for p in group["params"]:
                    if p.grad is not None:
                        task_grads.append(p.grad.clone())
                    else:
                        task_grads.append(torch.zeros_like(p))

            grads_task.append(task_grads)

        # Project conflicting gradients
        num_tasks = len(losses)
        projected_grads = [g.copy() for g in grads_task]

        for i in range(num_tasks):
            for j in range(num_tasks):
                if i == j:
                    continue

                # Compute dot product between gradient vectors
                dot_prod = sum(
                    (g_i * g_j).sum()
                    for g_i, g_j in zip(grads_task[i], grads_task[j], strict=False)
                )

                # If gradients conflict (negative dot product), project
                if dot_prod < 0:
                    # Project g_i onto normal plane of g_j
                    g_j_norm = sum((g**2).sum() for g in grads_task[j])

                    if g_j_norm > 1e-8:
                        proj_coef = dot_prod / g_j_norm

                        # Update projected gradients
                        for k, (g_i, g_j) in enumerate(
                            zip(projected_grads[i], grads_task[j], strict=False)
                        ):
                            projected_grads[i][k] = g_i - proj_coef * g_j

        # Average projected gradients across tasks
        final_grads = []
        for param_idx in range(len(projected_grads[0])):
            avg_grad = sum(proj[param_idx] for proj in projected_grads) / num_tasks
            final_grads.append(avg_grad)

        # Set final gradients
        grad_idx = 0
        for group in self._optimizer.param_groups:
            for p in group["params"]:
                if p.requires_grad:
                    p.grad = final_grads[grad_idx]
                    grad_idx += 1
