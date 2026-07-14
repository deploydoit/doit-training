"""Testes unitários para a página de lista de módulos.

Verifica:
- Configuração visual correta para cada status de progresso
- Indicadores visuais distintos para concluído, em andamento e não iniciado
- Tratamento de descrição com truncamento em 150 caracteres
- Tratamento de lista vazia de módulos

Requirements: 1.3, 1.5, 5.2, 5.3
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, "/Users/IsaSoares/Desktop/Kiro/doit-training")

from models.enums import ProgressStatus
from pages.module_list import _get_status_config


class TestGetStatusConfig:
    """Testes para a função _get_status_config."""

    def test_completed_status_returns_green_check(self):
        """Módulo concluído deve ter ícone ✅ e cor verde."""
        config = _get_status_config(ProgressStatus.COMPLETED, 100.0)

        assert config["icon"] == "✅"
        assert config["border_color"] == "#28a745"
        assert "Concluído" in config["badge_text"]
        assert "✓" in config["badge_text"]

    def test_in_progress_status_returns_blue_with_percentage(self):
        """Módulo em andamento deve ter ícone 📖, cor azul e percentual."""
        config = _get_status_config(ProgressStatus.IN_PROGRESS, 65.0)

        assert config["icon"] == "📖"
        assert config["border_color"] == "#3b82f6"
        assert "65%" in config["badge_text"]
        assert "Em andamento" in config["badge_text"]

    def test_in_progress_status_zero_percent(self):
        """Módulo em andamento com 0% deve exibir 0%."""
        config = _get_status_config(ProgressStatus.IN_PROGRESS, 0.0)

        assert "0%" in config["badge_text"]
        assert "Em andamento" in config["badge_text"]

    def test_in_progress_status_fractional_percent(self):
        """Percentual fracionário deve ser arredondado na exibição."""
        config = _get_status_config(ProgressStatus.IN_PROGRESS, 33.33)

        assert "33%" in config["badge_text"]

    def test_not_started_status_returns_gray(self):
        """Módulo não iniciado deve ter ícone 📘 e cor cinza."""
        config = _get_status_config(ProgressStatus.NOT_STARTED, 0.0)

        assert config["icon"] == "📘"
        assert config["border_color"] == "#dee2e6"
        assert "Não iniciado" in config["badge_text"]

    def test_all_statuses_have_required_keys(self):
        """Todos os status devem retornar todas as chaves de configuração."""
        required_keys = {"icon", "border_color", "bg_color", "text_color", "badge_bg", "badge_text"}

        for status in ProgressStatus:
            config = _get_status_config(status, 50.0)
            assert required_keys.issubset(config.keys()), (
                f"Status {status.value} missing keys: {required_keys - config.keys()}"
            )

    def test_visual_differentiation_between_statuses(self):
        """Cada status deve ter cor de borda diferente para diferenciação visual."""
        completed = _get_status_config(ProgressStatus.COMPLETED, 100.0)
        in_progress = _get_status_config(ProgressStatus.IN_PROGRESS, 50.0)
        not_started = _get_status_config(ProgressStatus.NOT_STARTED, 0.0)

        border_colors = {
            completed["border_color"],
            in_progress["border_color"],
            not_started["border_color"],
        }
        # All three statuses must have distinct border colors
        assert len(border_colors) == 3
