"""Gerenciador de Conteúdo do Sistema de Treinamento.

Interface administrativa para criação e edição de conteúdo:
- Criação, atualização e exclusão de módulos
- Criação de etapas com conteúdo
- Publicação com validação de completude
- Versionamento que preserva progresso dos usuários

Requirements: 6.1, 6.3, 6.4, 6.5, 6.6
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from models.data_models import Module, Step, StepContent
from models.database import Database
from models.enums import ContentType, ModuleStatus, StepType

from .errors import (
    ModuleNotFoundError,
    ValidationError,
    ValidationResult,
)


@dataclass
class DeleteResult:
    """Resultado de uma operação de exclusão de módulo.

    Attributes:
        deleted: Se o módulo foi efetivamente excluído.
        affected_users: Quantidade de usuários com progresso afetados.
        requires_confirmation: Se a exclusão requer confirmação adicional.
        message: Mensagem descritiva do resultado.
    """

    deleted: bool
    affected_users: int = 0
    requires_confirmation: bool = False
    message: str = ""


@dataclass
class PublishResult:
    """Resultado de uma operação de publicação de módulo.

    Attributes:
        published: Se o módulo foi publicado com sucesso.
        version: Versão resultante da publicação.
        errors: Lista de erros de validação (se publicação bloqueada).
        migrated_users: Quantidade de usuários cujo progresso foi migrado.
    """

    published: bool
    version: int = 1
    errors: List[str] = field(default_factory=list)
    migrated_users: int = 0


class ContentManager:
    """Gerenciador de conteúdo para administradores.

    Responsável por todas as operações CRUD de módulos e etapas,
    publicação com validação, e versionamento com preservação de
    progresso dos usuários.

    Attributes:
        db: Instância do banco de dados.
        media_path: Caminho para o diretório de arquivos de mídia.
    """

    def __init__(self, db: Database, media_path: str = "media"):
        """Inicializa o ContentManager.

        Args:
            db: Instância do banco de dados SQLite.
            media_path: Caminho para o diretório de mídia.
        """
        self.db = db
        self.media_path = media_path

    def create_module(self, title: str, description: str) -> Module:
        """Cria um novo módulo de treinamento.

        O módulo é criado com status 'draft' e versão 1. Um caminho
        principal (main path) é criado automaticamente.

        Args:
            title: Título do módulo (não pode ser vazio).
            description: Descrição do módulo (máximo 150 caracteres).

        Returns:
            Module criado com todos os campos preenchidos.

        Raises:
            ValidationError: Se título vazio ou descrição > 150 caracteres.

        Requirements: 6.1
        """
        # Validar entrada
        errors: List[str] = []
        if not title or not title.strip():
            errors.append("Título do módulo não pode ser vazio.")
        if len(description) > 150:
            errors.append(
                f"Descrição deve ter no máximo 150 caracteres (tem {len(description)})."
            )
        if errors:
            raise ValidationError(errors)

        module_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        # Inserir módulo
        self.db.execute(
            "INSERT INTO modules (id, title, description, status, version, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (module_id, title.strip(), description, ModuleStatus.DRAFT.value, 1, now, now),
        )

        # Criar caminho principal automaticamente
        main_path_id = str(uuid.uuid4())
        self.db.execute(
            "INSERT INTO paths (id, module_id, parent_branch_id, name, is_main) "
            "VALUES (?, ?, NULL, ?, TRUE)",
            (main_path_id, module_id, "Caminho Principal"),
        )

        self.db.commit()

        return Module(
            id=module_id,
            title=title.strip(),
            description=description,
            status=ModuleStatus.DRAFT,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
            version=1,
        )

    def update_module(self, module_id: str, **kwargs: Any) -> Module:
        """Atualiza um módulo existente preservando progresso dos usuários.

        Apenas os campos fornecidos em kwargs são atualizados.
        Campos permitidos: title, description, status.

        Args:
            module_id: ID do módulo a ser atualizado.
            **kwargs: Campos a atualizar (title, description).

        Returns:
            Module atualizado.

        Raises:
            ModuleNotFoundError: Se o módulo não existe.
            ValidationError: Se os dados fornecidos são inválidos.

        Requirements: 6.1, 6.4
        """
        # Verificar se módulo existe
        module = self._get_module_row(module_id)
        if module is None:
            raise ModuleNotFoundError(f"Módulo '{module_id}' não encontrado.")

        # Validar campos
        errors: List[str] = []
        allowed_fields = {"title", "description"}
        update_fields: Dict[str, Any] = {}

        for key, value in kwargs.items():
            if key not in allowed_fields:
                continue

            if key == "title":
                if not value or not value.strip():
                    errors.append("Título do módulo não pode ser vazio.")
                else:
                    update_fields["title"] = value.strip()

            elif key == "description":
                if len(value) > 150:
                    errors.append(
                        f"Descrição deve ter no máximo 150 caracteres (tem {len(value)})."
                    )
                else:
                    update_fields["description"] = value

        if errors:
            raise ValidationError(errors)

        if not update_fields:
            # Nenhum campo para atualizar, retornar módulo atual
            return self._build_module_from_row(module)

        # Construir query de update
        now = datetime.now().isoformat()
        update_fields["updated_at"] = now

        set_clauses = ", ".join(f"{k} = ?" for k in update_fields.keys())
        values = list(update_fields.values()) + [module_id]

        self.db.execute(
            f"UPDATE modules SET {set_clauses} WHERE id = ?",
            tuple(values),
        )
        self.db.commit()

        # Retornar módulo atualizado
        updated_row = self._get_module_row(module_id)
        return self._build_module_from_row(updated_row)

    def delete_module(self, module_id: str, confirm: bool = False) -> DeleteResult:
        """Exclui módulo (requer confirmação se há usuários com progresso).

        Se há usuários com progresso registrado no módulo:
        - Sem confirmação: retorna informação de afetados e requer confirmação
        - Com confirmação: exclui o módulo e todo o progresso associado

        Args:
            module_id: ID do módulo a ser excluído.
            confirm: Se True, confirma a exclusão mesmo com usuários afetados.

        Returns:
            DeleteResult com informações sobre a operação.

        Raises:
            ModuleNotFoundError: Se o módulo não existe.

        Requirements: 6.1, 6.6
        """
        # Verificar se módulo existe
        module = self._get_module_row(module_id)
        if module is None:
            raise ModuleNotFoundError(f"Módulo '{module_id}' não encontrado.")

        # Contar usuários com progresso neste módulo
        cursor = self.db.execute(
            "SELECT COUNT(DISTINCT user_id) as user_count "
            "FROM user_progress WHERE module_id = ?",
            (module_id,),
        )
        row = cursor.fetchone()
        affected_users = row["user_count"] if row else 0

        # Se há usuários afetados e não houve confirmação
        if affected_users > 0 and not confirm:
            return DeleteResult(
                deleted=False,
                affected_users=affected_users,
                requires_confirmation=True,
                message=(
                    f"Módulo possui {affected_users} usuário(s) com progresso registrado. "
                    "Confirme a exclusão para prosseguir."
                ),
            )

        # Executar exclusão (CASCADE cuida das tabelas dependentes)
        self.db.execute("DELETE FROM modules WHERE id = ?", (module_id,))
        self.db.commit()

        return DeleteResult(
            deleted=True,
            affected_users=affected_users,
            requires_confirmation=False,
            message=f"Módulo excluído com sucesso. {affected_users} usuário(s) afetado(s).",
        )

    def create_step(
        self,
        module_id: str,
        content: StepContent,
        position: int,
        path_id: Optional[str] = None,
        step_type: StepType = StepType.CONTENT,
    ) -> Step:
        """Cria nova etapa em um módulo.

        Se path_id não é fornecido, usa o caminho principal do módulo.

        Args:
            module_id: ID do módulo onde a etapa será criada.
            content: Conteúdo da etapa (StepContent).
            position: Posição sequencial no caminho.
            path_id: ID do caminho (None = caminho principal).
            step_type: Tipo da etapa (content ou branch).

        Returns:
            Step criada com conteúdo associado.

        Raises:
            ModuleNotFoundError: Se o módulo não existe.
            ValidationError: Se a posição é inválida ou já ocupada.

        Requirements: 6.1
        """
        # Verificar se módulo existe
        module = self._get_module_row(module_id)
        if module is None:
            raise ModuleNotFoundError(f"Módulo '{module_id}' não encontrado.")

        # Determinar path_id (usar main path se não fornecido)
        if path_id is None:
            path_id = self._get_main_path_id(module_id)
            if path_id is None:
                raise ValidationError(
                    ["Módulo não possui caminho principal configurado."]
                )

        # Verificar se posição já está ocupada
        cursor = self.db.execute(
            "SELECT id FROM steps WHERE path_id = ? AND position = ?",
            (path_id, position),
        )
        if cursor.fetchone() is not None:
            raise ValidationError(
                [f"Posição {position} já está ocupada no caminho '{path_id}'."]
            )

        # Criar etapa
        step_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        self.db.execute(
            "INSERT INTO steps (id, module_id, path_id, position, step_type, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (step_id, module_id, path_id, position, step_type.value, now),
        )

        # Criar conteúdo associado
        content_id = str(uuid.uuid4())
        self.db.execute(
            "INSERT INTO step_contents (id, step_id, content_type, content_data, alt_text, display_order) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                content_id,
                step_id,
                content.content_type.value,
                content.content_data,
                content.alt_text,
                content.order,
            ),
        )

        self.db.commit()

        created_at = datetime.fromisoformat(now)
        step_content = StepContent(
            id=content_id,
            step_id=step_id,
            content_type=content.content_type,
            content_data=content.content_data,
            alt_text=content.alt_text,
            order=content.order,
        )

        return Step(
            id=step_id,
            module_id=module_id,
            path_id=path_id,
            position=position,
            step_type=step_type,
            content=[step_content],
            created_at=created_at,
        )

    def publish_module(self, module_id: str) -> PublishResult:
        """Publica módulo após validação de completude.

        Fluxo:
        1. Valida o módulo (etapas com conteúdo, ramificações com 2-5 opções)
        2. Se inválido, bloqueia publicação e retorna erros
        3. Se válido, incrementa versão e atualiza status para 'published'
        4. Migra progresso de usuários preservando etapas concluídas

        Args:
            module_id: ID do módulo a publicar.

        Returns:
            PublishResult com status da publicação.

        Raises:
            ModuleNotFoundError: Se o módulo não existe.

        Requirements: 6.4, 6.5
        """
        # Verificar se módulo existe
        module = self._get_module_row(module_id)
        if module is None:
            raise ModuleNotFoundError(f"Módulo '{module_id}' não encontrado.")

        # Validar módulo antes de publicar
        validation_errors = self.validate_module(module_id)
        if validation_errors:
            error_messages = [e.message for e in validation_errors]
            return PublishResult(
                published=False,
                version=module["version"],
                errors=error_messages,
                migrated_users=0,
            )

        # Calcular nova versão
        current_version = module["version"]
        new_version = current_version + 1
        now = datetime.now().isoformat()

        # Migrar progresso dos usuários
        migrated_users = self._migrate_user_progress(module_id)

        # Atualizar módulo: status published, versão incrementada
        self.db.execute(
            "UPDATE modules SET status = ?, version = ?, updated_at = ? WHERE id = ?",
            (ModuleStatus.PUBLISHED.value, new_version, now, module_id),
        )
        self.db.commit()

        return PublishResult(
            published=True,
            version=new_version,
            errors=[],
            migrated_users=migrated_users,
        )

    def validate_module(self, module_id: str) -> List[ValidationErrorItem]:
        """Valida módulo antes de publicação.

        Verifica:
        - Todas as etapas têm pelo menos um conteúdo
        - Todas as ramificações têm entre 2 e 5 opções
        - Todos os rótulos de opções têm entre 3 e 80 caracteres

        Args:
            module_id: ID do módulo a validar.

        Returns:
            Lista de ValidationErrorItem. Lista vazia = módulo válido.

        Raises:
            ModuleNotFoundError: Se o módulo não existe.

        Requirements: 6.3, 6.5
        """
        module = self._get_module_row(module_id)
        if module is None:
            raise ModuleNotFoundError(f"Módulo '{module_id}' não encontrado.")

        errors: List[ValidationErrorItem] = []

        # 1. Verificar etapas sem conteúdo
        cursor = self.db.execute(
            "SELECT s.id, s.position, s.path_id "
            "FROM steps s "
            "WHERE s.module_id = ?",
            (module_id,),
        )
        steps = cursor.fetchall()

        for step in steps:
            content_cursor = self.db.execute(
                "SELECT COUNT(*) as cnt FROM step_contents WHERE step_id = ?",
                (step["id"],),
            )
            content_count = content_cursor.fetchone()["cnt"]
            if content_count == 0:
                errors.append(
                    ValidationErrorItem(
                        element_id=step["id"],
                        element_type="step",
                        message=(
                            f"Etapa na posição {step['position']} "
                            f"(caminho '{step['path_id']}') não possui conteúdo."
                        ),
                    )
                )

        # 2. Validar ramificações usando BranchManager.validate_branch
        cursor = self.db.execute(
            "SELECT s.id FROM steps s "
            "WHERE s.module_id = ? AND s.step_type = ?",
            (module_id, StepType.BRANCH.value),
        )
        branch_steps = cursor.fetchall()

        for branch_step in branch_steps:
            step_id = branch_step["id"]
            result = self._validate_branch_for_module(step_id)
            if not result.is_valid:
                for error_msg in result.errors:
                    errors.append(
                        ValidationErrorItem(
                            element_id=step_id,
                            element_type="branch",
                            message=error_msg,
                        )
                    )

        return errors

    def _validate_branch_for_module(self, step_id: str) -> ValidationResult:
        """Valida uma ramificação para publicação do módulo.

        Verifica:
        - Entre 2 e 5 opções
        - Labels entre 3 e 80 caracteres

        Args:
            step_id: ID da etapa com ramificação.

        Returns:
            ValidationResult com resultado da validação.
        """
        errors: List[str] = []

        # Buscar branch
        cursor = self.db.execute(
            "SELECT id FROM branches WHERE step_id = ?", (step_id,)
        )
        branch_row = cursor.fetchone()

        if branch_row is None:
            errors.append(
                f"Etapa '{step_id}' é do tipo 'branch' mas não possui ramificação configurada."
            )
            return ValidationResult(is_valid=False, errors=errors)

        branch_id = branch_row["id"]

        # Buscar opções
        cursor = self.db.execute(
            "SELECT id, label FROM branch_options WHERE branch_id = ? ORDER BY position",
            (branch_id,),
        )
        options = cursor.fetchall()
        num_options = len(options)

        # Validar quantidade (2-5)
        if num_options < 2:
            errors.append(
                f"Ramificação deve ter no mínimo 2 opções, mas tem {num_options}."
            )
        elif num_options > 5:
            errors.append(
                f"Ramificação deve ter no máximo 5 opções, mas tem {num_options}."
            )

        # Validar labels (3-80 caracteres para admin)
        for option in options:
            label = option["label"]
            label_len = len(label)
            if label_len < 3:
                errors.append(
                    f"Opção '{option['id']}': rótulo deve ter no mínimo 3 caracteres "
                    f"(tem {label_len})."
                )
            elif label_len > 80:
                errors.append(
                    f"Opção '{option['id']}': rótulo deve ter no máximo 80 caracteres "
                    f"(tem {label_len})."
                )

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def _migrate_user_progress(self, module_id: str) -> int:
        """Migra progresso dos usuários ao publicar nova versão.

        Preserva etapas concluídas que ainda existem na nova versão.
        Posiciona o usuário na etapa mais avançada ainda válida.

        Args:
            module_id: ID do módulo sendo publicado.

        Returns:
            Número de usuários migrados.

        Requirements: 6.4
        """
        # Buscar todos os usuários com progresso neste módulo
        cursor = self.db.execute(
            "SELECT id, user_id, current_step_id, current_path_id "
            "FROM user_progress WHERE module_id = ?",
            (module_id,),
        )
        progress_records = cursor.fetchall()

        if not progress_records:
            return 0

        # Obter set de step_ids válidos no módulo atual
        step_cursor = self.db.execute(
            "SELECT id FROM steps WHERE module_id = ?", (module_id,)
        )
        valid_step_ids = {row["id"] for row in step_cursor.fetchall()}

        migrated_count = 0

        for progress in progress_records:
            user_id = progress["user_id"]
            current_step_id = progress["current_step_id"]
            current_path_id = progress["current_path_id"]

            # Verificar se o current_step ainda existe
            if current_step_id in valid_step_ids:
                # Etapa atual ainda é válida, posição não muda
                pass
            else:
                # Etapa atual não existe mais, encontrar a mais avançada válida
                new_step = self._find_most_advanced_valid_step(
                    user_id, module_id, valid_step_ids, current_path_id
                )

                if new_step:
                    # Atualizar progresso para etapa mais avançada válida
                    self.db.execute(
                        "UPDATE user_progress "
                        "SET current_step_id = ?, current_path_id = ?, last_accessed = ? "
                        "WHERE id = ?",
                        (
                            new_step["id"],
                            new_step["path_id"],
                            datetime.now().isoformat(),
                            progress["id"],
                        ),
                    )
                else:
                    # Nenhuma etapa válida, posicionar na primeira etapa do main path
                    first_step = self._get_first_step_of_main_path(module_id)
                    if first_step:
                        self.db.execute(
                            "UPDATE user_progress "
                            "SET current_step_id = ?, current_path_id = ?, "
                            "last_accessed = ? "
                            "WHERE id = ?",
                            (
                                first_step["id"],
                                first_step["path_id"],
                                datetime.now().isoformat(),
                                progress["id"],
                            ),
                        )

            # Remover completed_steps que não existem mais (sempre executar)
            cursor_completed = self.db.execute(
                "SELECT step_id FROM completed_steps WHERE user_id = ?",
                (user_id,),
            )
            completed_steps = cursor_completed.fetchall()
            for cs in completed_steps:
                if cs["step_id"] not in valid_step_ids:
                    self.db.execute(
                        "DELETE FROM completed_steps "
                        "WHERE user_id = ? AND step_id = ?",
                        (user_id, cs["step_id"]),
                    )

            migrated_count += 1

        return migrated_count

    def _find_most_advanced_valid_step(
        self,
        user_id: str,
        module_id: str,
        valid_step_ids: set,
        current_path_id: Optional[str],
    ) -> Optional[dict]:
        """Encontra a etapa mais avançada válida para um usuário.

        Busca nas etapas concluídas pelo usuário aquelas que ainda existem
        no módulo, e retorna a de maior posição.

        Args:
            user_id: ID do usuário.
            module_id: ID do módulo.
            valid_step_ids: Set de IDs de etapas válidas.
            current_path_id: ID do caminho atual (preferência).

        Returns:
            Dict com id e path_id da etapa, ou None se não encontrada.
        """
        # Buscar completed steps do usuário que ainda são válidos
        cursor = self.db.execute(
            "SELECT cs.step_id "
            "FROM completed_steps cs "
            "JOIN steps s ON cs.step_id = s.id "
            "WHERE cs.user_id = ? AND s.module_id = ? "
            "ORDER BY s.position DESC",
            (user_id, module_id),
        )
        completed = cursor.fetchall()

        for row in completed:
            if row["step_id"] in valid_step_ids:
                # Buscar info completa da etapa
                step_cursor = self.db.execute(
                    "SELECT id, path_id FROM steps WHERE id = ?",
                    (row["step_id"],),
                )
                step_row = step_cursor.fetchone()
                if step_row:
                    return {"id": step_row["id"], "path_id": step_row["path_id"]}

        return None

    def _get_first_step_of_main_path(self, module_id: str) -> Optional[dict]:
        """Retorna a primeira etapa do caminho principal do módulo.

        Args:
            module_id: ID do módulo.

        Returns:
            Dict com id e path_id, ou None.
        """
        main_path_id = self._get_main_path_id(module_id)
        if main_path_id is None:
            return None

        cursor = self.db.execute(
            "SELECT id, path_id FROM steps "
            "WHERE path_id = ? ORDER BY position LIMIT 1",
            (main_path_id,),
        )
        row = cursor.fetchone()
        if row:
            return {"id": row["id"], "path_id": row["path_id"]}
        return None

    def _get_module_row(self, module_id: str) -> Optional[Any]:
        """Busca um módulo pelo ID.

        Args:
            module_id: ID do módulo.

        Returns:
            sqlite3.Row ou None se não encontrado.
        """
        cursor = self.db.execute(
            "SELECT id, title, description, status, version, created_at, updated_at "
            "FROM modules WHERE id = ?",
            (module_id,),
        )
        return cursor.fetchone()

    def _get_main_path_id(self, module_id: str) -> Optional[str]:
        """Retorna o ID do caminho principal de um módulo.

        Args:
            module_id: ID do módulo.

        Returns:
            ID do caminho principal ou None.
        """
        cursor = self.db.execute(
            "SELECT id FROM paths WHERE module_id = ? AND is_main = TRUE",
            (module_id,),
        )
        row = cursor.fetchone()
        return row["id"] if row else None

    def _build_module_from_row(self, row) -> Module:
        """Constrói um objeto Module a partir de uma row do banco.

        Args:
            row: sqlite3.Row com colunas do module.

        Returns:
            Module com todos os campos preenchidos.
        """
        created_at = row["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()

        updated_at = row["updated_at"]
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.now()

        return Module(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            status=ModuleStatus(row["status"]),
            created_at=created_at,
            updated_at=updated_at,
            version=row["version"],
        )


@dataclass
class ValidationErrorItem:
    """Item individual de erro de validação do módulo.

    Attributes:
        element_id: ID do elemento com problema (step ou branch).
        element_type: Tipo do elemento ('step' ou 'branch').
        message: Mensagem descritiva do erro.
    """

    element_id: str
    element_type: str
    message: str
