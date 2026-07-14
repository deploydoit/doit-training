"""Renderizador de conteúdo multimídia para etapas de treinamento.

Funções de renderização para cada tipo de conteúdo (ContentType):
- TEXT: texto formatado em markdown
- IMAGE: imagens (PNG, JPG, GIF, SVG) com aspect ratio preservado
- VIDEO: vídeo embarcado com controles de reprodução (máximo 15 min)
- LINK: links externos com ícone indicativo e target="_blank"
- Fallback: mensagem de erro com botão "Tentar novamente"

Requirements: 4.1, 4.2, 4.3, 4.4, 4.5
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from models.data_models import StepContent
from models.enums import ContentType


# Duração máxima de vídeo permitida: 15 minutos em segundos
MAX_VIDEO_DURATION_SECONDS = 15 * 60


def render_content(content: StepContent) -> None:
    """Renderiza um item de conteúdo de acordo com seu tipo.

    Despacha para a função de renderização apropriada com base no
    content_type do StepContent. Em caso de falha no carregamento,
    exibe o fallback com opção de tentar novamente.

    Args:
        content: Objeto StepContent com tipo e dados do conteúdo.
    """
    renderers = {
        ContentType.TEXT: _render_text,
        ContentType.IMAGE: _render_image,
        ContentType.VIDEO: _render_video,
        ContentType.LINK: _render_link,
    }

    renderer = renderers.get(content.content_type)
    if renderer is None:
        st.warning(f"Tipo de conteúdo não suportado: {content.content_type}")
        return

    renderer(content)


def render_step_contents(contents: list[StepContent]) -> None:
    """Renderiza todos os conteúdos de uma etapa em ordem.

    Args:
        contents: Lista de StepContent ordenada por `order`.
    """
    sorted_contents = sorted(contents, key=lambda c: c.order)
    for content in sorted_contents:
        render_content(content)


def _render_text(content: StepContent) -> None:
    """Renderiza texto formatado em markdown.

    Suporta: negrito, itálico, títulos, listas e hiperlinks.

    Requirements: 4.1
    """
    st.markdown(content.content_data)


def _render_image(content: StepContent) -> None:
    """Renderiza imagem com aspect ratio preservado e largura máxima 100%.

    Formatos suportados: PNG, JPG, GIF, SVG.
    A imagem mantém sua proporção original sem gerar rolagem horizontal.
    Exibe fallback se a imagem não puder ser carregada.

    Requirements: 4.3, 4.5
    """
    # Usa session_state para rastrear erros de carregamento por conteúdo
    error_key = f"media_error_{content.id}"
    retry_key = f"media_retry_{content.id}"

    # Verifica se houve um retry solicitado
    if st.session_state.get(retry_key, False):
        st.session_state[error_key] = False
        st.session_state[retry_key] = False

    if st.session_state.get(error_key, False):
        _render_fallback(content)
        return

    try:
        caption = content.alt_text or ""
        # st.image suporta URLs e caminhos locais, preserva aspect ratio
        # use_container_width=True garante largura máxima de 100% do contêiner
        st.image(
            content.content_data,
            caption=caption if caption else None,
            use_container_width=True,
        )
    except Exception:
        st.session_state[error_key] = True
        _render_fallback(content)


def _render_video(content: StepContent) -> None:
    """Renderiza vídeo embarcado com controles de reprodução.

    Controles: play, pause, barra de progresso, controle de volume.
    Duração máxima permitida: 15 minutos.
    Exibe fallback se o vídeo não puder ser carregado.

    Suporta:
    - URLs de vídeo diretas (mp4, webm, etc.) via st.video
    - URLs do YouTube/Vimeo via iframe embed

    Requirements: 4.2, 4.5
    """
    error_key = f"media_error_{content.id}"
    retry_key = f"media_retry_{content.id}"

    if st.session_state.get(retry_key, False):
        st.session_state[error_key] = False
        st.session_state[retry_key] = False

    if st.session_state.get(error_key, False):
        _render_fallback(content)
        return

    try:
        video_url = content.content_data.strip()

        if _is_youtube_url(video_url):
            _render_youtube_embed(video_url, content)
        elif _is_vimeo_url(video_url):
            _render_vimeo_embed(video_url, content)
        else:
            # Vídeo direto (mp4, webm, etc.)
            st.video(video_url)
    except Exception:
        st.session_state[error_key] = True
        _render_fallback(content)


def _render_link(content: StepContent) -> None:
    """Renderiza link externo com ícone indicativo e target="_blank".

    O link abre em uma nova aba do navegador e é identificado
    visualmente como externo por meio de um ícone ().

    Requirements: 4.4
    """
    url = content.content_data.strip()
    label = content.alt_text or url

    # Renderiza link com ícone externo e target="_blank"
    link_html = (
        f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
        f'style="text-decoration: none; color: #1a73e8; font-size: 1rem;">'
        f' {label} <span style="font-size: 0.8em;">↗</span></a>'
    )
    st.markdown(link_html, unsafe_allow_html=True)


def _render_fallback(content: StepContent) -> None:
    """Renderiza fallback para mídia não carregada com botão "Tentar novamente".

    Exibe mensagem indicando que o conteúdo não está disponível
    e oferece opção de retry sem bloquear a navegação.

    Requirements: 4.5
    """
    retry_key = f"media_retry_{content.id}"

    content_type_labels = {
        ContentType.IMAGE: "Imagem",
        ContentType.VIDEO: "Vídeo",
        ContentType.TEXT: "Texto",
        ContentType.LINK: "Link",
    }
    type_label = content_type_labels.get(content.content_type, "Conteúdo")

    st.warning(f" {type_label} indisponível no momento.")

    if st.button("Tentar novamente", key=f"retry_btn_{content.id}"):
        st.session_state[retry_key] = True
        st.rerun()


def _is_youtube_url(url: str) -> bool:
    """Verifica se a URL é do YouTube."""
    return any(
        domain in url
        for domain in ["youtube.com", "youtu.be", "youtube-nocookie.com"]
    )


def _is_vimeo_url(url: str) -> bool:
    """Verifica se a URL é do Vimeo."""
    return "vimeo.com" in url


def _get_youtube_embed_url(url: str) -> str:
    """Converte URL do YouTube para formato embed.

    Suporta:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    """
    if "embed/" in url:
        return url

    video_id = ""
    if "youtu.be/" in url:
        video_id = url.split("youtu.be/")[-1].split("?")[0].split("&")[0]
    elif "watch?v=" in url:
        video_id = url.split("watch?v=")[-1].split("&")[0]
    elif "v=" in url:
        video_id = url.split("v=")[-1].split("&")[0]

    if video_id:
        return f"https://www.youtube.com/embed/{video_id}"
    return url


def _get_vimeo_embed_url(url: str) -> str:
    """Converte URL do Vimeo para formato embed.

    Suporta: https://vimeo.com/VIDEO_ID
    """
    if "player.vimeo.com" in url:
        return url

    # Extrai o ID do vídeo
    parts = url.rstrip("/").split("/")
    video_id = parts[-1] if parts else ""

    if video_id and video_id.isdigit():
        return f"https://player.vimeo.com/video/{video_id}"
    return url


def _render_youtube_embed(url: str, content: StepContent) -> None:
    """Renderiza embed de YouTube com controles."""
    embed_url = _get_youtube_embed_url(url)

    iframe_html = (
        f'<div style="position: relative; padding-bottom: 56.25%; height: 0; '
        f'overflow: hidden; max-width: 100%;">'
        f'<iframe src="{embed_url}" '
        f'style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" '
        f'frameborder="0" '
        f'allow="accelerometer; autoplay; clipboard-write; encrypted-media; '
        f'gyroscope; picture-in-picture" '
        f'allowfullscreen '
        f'title="{content.alt_text or "Vídeo"}">'
        f"</iframe></div>"
    )
    components.html(iframe_html, height=400)


def _render_vimeo_embed(url: str, content: StepContent) -> None:
    """Renderiza embed de Vimeo com controles."""
    embed_url = _get_vimeo_embed_url(url)

    iframe_html = (
        f'<div style="position: relative; padding-bottom: 56.25%; height: 0; '
        f'overflow: hidden; max-width: 100%;">'
        f'<iframe src="{embed_url}" '
        f'style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" '
        f'frameborder="0" '
        f'allow="autoplay; fullscreen; picture-in-picture" '
        f'allowfullscreen '
        f'title="{content.alt_text or "Vídeo"}">'
        f"</iframe></div>"
    )
    components.html(iframe_html, height=400)
