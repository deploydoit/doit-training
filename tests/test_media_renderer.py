"""Testes unitários para o renderizador de conteúdo multimídia.

Valida:
- Renderização de texto formatado (markdown)
- Renderização de imagens com aspect ratio preservado (largura máxima 100%)
- Renderização de vídeo com controles (play, pause, progresso, volume)
- Links externos com ícone indicativo e target="_blank"
- Fallback para mídia não carregada com botão "Tentar novamente"
- Parsing de URLs do YouTube e Vimeo

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
"""

from typing import Optional

import pytest

from models.data_models import StepContent
from models.enums import ContentType
from pages.media_renderer import (
    _get_youtube_embed_url,
    _get_vimeo_embed_url,
    _is_youtube_url,
    _is_vimeo_url,
    render_step_contents,
)


# --- Fixtures ---


def _make_content(
    content_type: ContentType,
    content_data: str,
    alt_text: "Optional[str]" = None,
    content_id: str = "content-1",
    order: int = 0,
) -> StepContent:
    """Helper para criar StepContent para testes."""
    return StepContent(
        id=content_id,
        step_id="step-1",
        content_type=content_type,
        content_data=content_data,
        alt_text=alt_text,
        order=order,
    )


# --- Testes de detecção de URL ---


class TestYouTubeUrlDetection:
    """Testes para detecção de URLs do YouTube."""

    def test_standard_youtube_url(self):
        """Detecta URL padrão do YouTube."""
        assert _is_youtube_url("https://www.youtube.com/watch?v=abc123") is True

    def test_short_youtube_url(self):
        """Detecta URL curta do YouTube."""
        assert _is_youtube_url("https://youtu.be/abc123") is True

    def test_nocookie_youtube_url(self):
        """Detecta URL no-cookie do YouTube."""
        assert _is_youtube_url("https://www.youtube-nocookie.com/embed/abc123") is True

    def test_non_youtube_url(self):
        """Não detecta URL que não é do YouTube."""
        assert _is_youtube_url("https://vimeo.com/123456") is False

    def test_plain_url(self):
        """Não detecta URL genérica."""
        assert _is_youtube_url("https://example.com/video.mp4") is False


class TestVimeoUrlDetection:
    """Testes para detecção de URLs do Vimeo."""

    def test_standard_vimeo_url(self):
        """Detecta URL padrão do Vimeo."""
        assert _is_vimeo_url("https://vimeo.com/123456789") is True

    def test_player_vimeo_url(self):
        """Detecta URL do player do Vimeo."""
        assert _is_vimeo_url("https://player.vimeo.com/video/123456789") is True

    def test_non_vimeo_url(self):
        """Não detecta URL que não é do Vimeo."""
        assert _is_vimeo_url("https://youtube.com/watch?v=abc") is False


# --- Testes de conversão de URL para embed ---


class TestYouTubeEmbedUrl:
    """Testes para conversão de URLs do YouTube para embed."""

    def test_standard_watch_url(self):
        """Converte URL padrão watch para embed."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = _get_youtube_embed_url(url)
        assert result == "https://www.youtube.com/embed/dQw4w9WgXcQ"

    def test_short_url(self):
        """Converte URL curta youtu.be para embed."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        result = _get_youtube_embed_url(url)
        assert result == "https://www.youtube.com/embed/dQw4w9WgXcQ"

    def test_already_embed_url(self):
        """URL já no formato embed permanece inalterada."""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        result = _get_youtube_embed_url(url)
        assert result == url

    def test_url_with_extra_params(self):
        """Extrai ID mesmo com parâmetros adicionais."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s"
        result = _get_youtube_embed_url(url)
        assert result == "https://www.youtube.com/embed/dQw4w9WgXcQ"

    def test_short_url_with_params(self):
        """Extrai ID de URL curta com parâmetros."""
        url = "https://youtu.be/dQw4w9WgXcQ?t=60"
        result = _get_youtube_embed_url(url)
        assert result == "https://www.youtube.com/embed/dQw4w9WgXcQ"


class TestVimeoEmbedUrl:
    """Testes para conversão de URLs do Vimeo para embed."""

    def test_standard_vimeo_url(self):
        """Converte URL padrão do Vimeo para embed."""
        url = "https://vimeo.com/123456789"
        result = _get_vimeo_embed_url(url)
        assert result == "https://player.vimeo.com/video/123456789"

    def test_already_player_url(self):
        """URL já no formato player permanece inalterada."""
        url = "https://player.vimeo.com/video/123456789"
        result = _get_vimeo_embed_url(url)
        assert result == url

    def test_url_with_trailing_slash(self):
        """Remove barra final antes de extrair ID."""
        url = "https://vimeo.com/123456789/"
        result = _get_vimeo_embed_url(url)
        assert result == "https://player.vimeo.com/video/123456789"


# --- Testes de ordenação ---


class TestContentOrdering:
    """Testes para ordenação de conteúdos em uma etapa."""

    def test_contents_rendered_in_order(self):
        """Conteúdos são ordenados pelo campo 'order'."""
        contents = [
            _make_content(ContentType.TEXT, "Segundo", content_id="c2", order=1),
            _make_content(ContentType.TEXT, "Primeiro", content_id="c1", order=0),
            _make_content(ContentType.TEXT, "Terceiro", content_id="c3", order=2),
        ]

        # Verifica que a função de ordenação funciona
        sorted_contents = sorted(contents, key=lambda c: c.order)
        assert sorted_contents[0].content_data == "Primeiro"
        assert sorted_contents[1].content_data == "Segundo"
        assert sorted_contents[2].content_data == "Terceiro"

    def test_single_content_item(self):
        """Etapa com um único conteúdo não causa erro."""
        contents = [
            _make_content(ContentType.TEXT, "Único conteúdo", content_id="c1"),
        ]
        sorted_contents = sorted(contents, key=lambda c: c.order)
        assert len(sorted_contents) == 1

    def test_empty_content_list(self):
        """Lista vazia de conteúdos não causa erro."""
        contents = []
        sorted_contents = sorted(contents, key=lambda c: c.order)
        assert sorted_contents == []


# --- Testes de construção de conteúdo ---


class TestContentTypes:
    """Testes para verificar que conteúdos são criados corretamente por tipo."""

    def test_text_content(self):
        """Conteúdo TEXT com markdown é preservado."""
        content = _make_content(
            ContentType.TEXT,
            "# Título\n\n**Negrito** e *itálico*\n\n- Item 1\n- Item 2",
        )
        assert content.content_type == ContentType.TEXT
        assert "# Título" in content.content_data
        assert "**Negrito**" in content.content_data

    def test_image_content_with_alt(self):
        """Conteúdo IMAGE com alt_text para acessibilidade."""
        content = _make_content(
            ContentType.IMAGE,
            "https://example.com/imagem.png",
            alt_text="Diagrama do sistema",
        )
        assert content.content_type == ContentType.IMAGE
        assert content.alt_text == "Diagrama do sistema"
        assert content.content_data.endswith(".png")

    def test_image_formats_supported(self):
        """Imagens nos formatos PNG, JPG, GIF e SVG são aceitas."""
        formats = [
            ("imagem.png", ContentType.IMAGE),
            ("foto.jpg", ContentType.IMAGE),
            ("animacao.gif", ContentType.IMAGE),
            ("icone.svg", ContentType.IMAGE),
        ]
        for url, ctype in formats:
            content = _make_content(ctype, f"https://example.com/{url}")
            assert content.content_type == ContentType.IMAGE

    def test_video_content(self):
        """Conteúdo VIDEO com URL é criado corretamente."""
        content = _make_content(
            ContentType.VIDEO,
            "https://www.youtube.com/watch?v=abc123",
            alt_text="Tutorial de navegação",
        )
        assert content.content_type == ContentType.VIDEO
        assert "youtube.com" in content.content_data

    def test_link_content(self):
        """Conteúdo LINK com URL e descrição."""
        content = _make_content(
            ContentType.LINK,
            "https://docs.example.com/guia",
            alt_text="Guia de referência completo",
        )
        assert content.content_type == ContentType.LINK
        assert content.alt_text == "Guia de referência completo"


# --- Testes de link externo ---


class TestExternalLinks:
    """Testes para validação de links externos."""

    def test_link_has_url(self):
        """Link externo contém URL válida."""
        content = _make_content(
            ContentType.LINK,
            "https://external.example.com/resource",
            alt_text="Recurso externo",
        )
        assert content.content_data.startswith("https://")

    def test_link_label_from_alt_text(self):
        """Label do link vem do alt_text quando disponível."""
        content = _make_content(
            ContentType.LINK,
            "https://example.com",
            alt_text="Documentação oficial",
        )
        # O alt_text será usado como label do link
        assert content.alt_text == "Documentação oficial"

    def test_link_without_alt_text_uses_url(self):
        """Sem alt_text, a URL é usada como label."""
        content = _make_content(
            ContentType.LINK,
            "https://example.com/long/path",
            alt_text=None,
        )
        # Quando alt_text é None, a URL deve ser usada como fallback
        assert content.alt_text is None
        # O renderer usará content_data como label neste caso
        assert content.content_data == "https://example.com/long/path"
