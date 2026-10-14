from app.database import get_connection
from app.models import CV
from app.schemas import CVFormData
from app.services.structured_cv_service import (
    STRUCTURED_PAYLOAD_STATUS_VALID,
    build_structured_cv_write_bundle,
    build_legacy_structured_columns,
    resolve_structured_cv_state,
)
from app.validations.cv_validations import build_cv_form_data, build_duplicate_title, validate_cv_form


class DuplicateCVError(ValueError):
    pass


class StructuredCVLegacyUpdateError(ValueError):
    """El CV destino ya es estructurado y no admite escritura por el formulario plano.

    Un CV estructurado tiene contenido que solo existe en `structured_payload`
    (headline, ubicacion, certificaciones, idiomas, proyectos, links,
    informacion adicional). El formulario plano no puede representar ni
    preservar ese contenido, asi que el punto de escritura compartido rechaza
    la operacion en vez de degradar el CV a legacy o perder datos.
    """


def list_cvs() -> list[CV]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM cvs
            WHERE deleted_at IS NULL
            ORDER BY updated_at DESC, id DESC
            """
        ).fetchall()

    return [_row_to_cv(row) for row in rows]


def get_cv(cv_id: int) -> CV | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM cvs
            WHERE id = ? AND deleted_at IS NULL
            """,
            (cv_id,),
        ).fetchone()

    return _row_to_cv(row) if row else None


def create_cv(form_data: CVFormData) -> int:
    return _insert_cv(form_data, structured_columns=build_legacy_structured_columns())


def create_structured_cv(
    *,
    title: str,
    payload: object,
    metadata_source: str = "structured_editor",
) -> int:
    """Crea un CV estructurado validando todo antes de persistir nada.

    El snapshot legacy y las columnas estructuradas se escriben en una sola
    sentencia INSERT. Un payload invalido o un snapshot legacy invalido lanzan
    `StructuredCVWriteError` sin ninguna escritura parcial.
    """
    bundle = build_structured_cv_write_bundle(title=title, payload=payload, metadata_source=metadata_source)
    return _insert_cv(bundle.form_data, structured_columns=bundle.structured_columns)


def _insert_cv(form_data: CVFormData, *, structured_columns: dict[str, object]) -> int:
    values = form_data.as_database_values()
    values.update(structured_columns)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO cvs (
                title,
                full_name,
                email,
                phone,
                professional_summary,
                experience_summary,
                education_summary,
                skills,
                structured_schema_version,
                structured_payload,
                structured_payload_status
            )
            VALUES (
                :title,
                :full_name,
                :email,
                :phone,
                :professional_summary,
                :experience_summary,
                :education_summary,
                :skills,
                :structured_schema_version,
                :structured_payload,
                :structured_payload_status
            )
            """,
            values,
        )
        connection.commit()

    return int(cursor.lastrowid)


def update_cv(cv_id: int, form_data: CVFormData) -> bool:
    """Actualiza un CV desde el formulario plano.

    Solo filas legacy son escribibles por esta via. Para una fila estructurada
    lanza `StructuredCVLegacyUpdateError` y nunca hay escritura parcial ni
    downgrade silencioso a legacy.

    La pre-verificacion en Python es la via rapida y clara de rechazo, pero no
    alcanza: entre esa lectura y el UPDATE otro escritor puede convertir la fila
    a estructurada. Por eso la precondicion legacy viaja ademas dentro del
    WHERE del propio UPDATE, que es atomico. Si el UPDATE no afecta filas, la
    misma transaccion distingue fila ausente o borrada (`False`) de conflicto
    de estado (error de dominio) y lanza sin commitear.
    """
    current_cv = get_cv(cv_id)
    if current_cv is None:
        return False

    values = form_data.as_database_values()
    values.update(_build_structured_columns_for_legacy_update(current_cv))
    values["id"] = str(cv_id)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE cvs
            SET
                title = :title,
                full_name = :full_name,
                email = :email,
                phone = :phone,
                professional_summary = :professional_summary,
                experience_summary = :experience_summary,
                education_summary = :education_summary,
                skills = :skills,
                structured_schema_version = :structured_schema_version,
                structured_payload = :structured_payload,
                structured_payload_status = :structured_payload_status,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
                AND deleted_at IS NULL
                AND (
                    structured_schema_version IS NULL
                    OR structured_schema_version < 2
                    OR structured_payload IS NULL
                )
            """,
            values,
        )

        if cursor.rowcount == 0:
            return _resolve_zero_row_legacy_update(connection, cv_id)

        connection.commit()

    return True


def _resolve_zero_row_legacy_update(connection, cv_id: int) -> bool:
    """Resuelve un UPDATE legacy que no actualizo ninguna fila.

    O la fila no existe o esta borrada logicamente (semantica `False` de
    siempre), o otro escritor la convertio a estructurada entre la
    pre-verificacion y el UPDATE (conflicto de estado). No se commitea en
    ningun caso y el error de dominio sale del bloque `with`, asi que la
    conexion descarta cualquier escritura pendiente.
    """
    row = connection.execute(
        "SELECT id FROM cvs WHERE id = ? AND deleted_at IS NULL",
        (cv_id,),
    ).fetchone()

    if row is None:
        return False

    raise StructuredCVLegacyUpdateError(
        "El CV tiene datos estructurados validos y no se puede actualizar desde el formulario plano."
    )


def _build_structured_columns_for_legacy_update(current_cv: CV) -> dict[str, object]:
    """Columnas estructuradas para una escritura del formulario plano.

    Un CV legacy se mantiene legacy. Un CV estructurado lanza
    `StructuredCVLegacyUpdateError`: regenerar el payload desde campos planos
    borraria el contenido que solo existe en schema 2, y nullar el payload lo
    degradaria a legacy en silencio. Ninguna escritura ocurre en ese caso.
    """
    if not resolve_structured_cv_state(current_cv).is_structured:
        return build_legacy_structured_columns()

    raise StructuredCVLegacyUpdateError(
        "El CV tiene datos estructurados validos y no se puede actualizar desde el formulario plano."
    )


def update_structured_cv(
    cv_id: int,
    *,
    title: str,
    payload: object,
    metadata_source: str = "structured_editor",
) -> bool:
    """Actualiza un CV como estructurado de forma atomica.

    Valida el payload y el snapshot legacy derivado antes de escribir. La
    escritura actualiza campos legacy y columnas estructuradas en una sola
    sentencia UPDATE. Un CV legacy que pasa por este flujo queda estructurado.
    """
    current_cv = get_cv(cv_id)
    if current_cv is None:
        return False

    bundle = build_structured_cv_write_bundle(title=title, payload=payload, metadata_source=metadata_source)

    values = bundle.form_data.as_database_values()
    values.update(bundle.structured_columns)
    values["id"] = str(cv_id)

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE cvs
            SET
                title = :title,
                full_name = :full_name,
                email = :email,
                phone = :phone,
                professional_summary = :professional_summary,
                experience_summary = :experience_summary,
                education_summary = :education_summary,
                skills = :skills,
                structured_schema_version = :structured_schema_version,
                structured_payload = :structured_payload,
                structured_payload_status = :structured_payload_status,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :id AND deleted_at IS NULL
            """,
            values,
        )
        connection.commit()

    return cursor.rowcount > 0


def duplicate_cv(cv_id: int) -> int | None:
    source_cv = get_cv(cv_id)
    if source_cv is None:
        return None

    duplicate_data = build_cv_form_data(
        {
            "title": build_duplicate_title(source_cv.title),
            "full_name": source_cv.full_name,
            "email": source_cv.email,
            "phone": source_cv.phone,
            "professional_summary": source_cv.professional_summary,
            "experience_summary": source_cv.experience_summary,
            "education_summary": source_cv.education_summary,
            "skills": source_cv.skills,
        }
    )

    errors = validate_cv_form(duplicate_data)
    if errors:
        joined_errors = "; ".join(f"{field}: {message}" for field, message in errors.items())
        raise DuplicateCVError(f"No se pudo duplicar el CV: {joined_errors}")

    structured_columns = build_legacy_structured_columns()
    if resolve_structured_cv_state(source_cv).is_structured:
        structured_columns = {
            "structured_schema_version": source_cv.structured_schema_version,
            "structured_payload": source_cv.structured_payload,
            "structured_payload_status": STRUCTURED_PAYLOAD_STATUS_VALID,
        }

    return _insert_cv(duplicate_data, structured_columns=structured_columns)


def soft_delete_cv(cv_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE cvs
            SET deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND deleted_at IS NULL
            """,
            (cv_id,),
        )
        connection.commit()

    return cursor.rowcount > 0


def hard_delete_cv(cv_id: int) -> bool:
    """Borrado FISICO de un CV, para el entorno de PRUEBAS.

    `soft_delete_cv` solo marca. El vaciado de datos ficticios exige que el
    registro desaparezca de la base, asi que esto es una operacion distinta y no
    comparte camino con el borrado normal que ve el usuario.
    """

    with get_connection() as connection:
        cursor = connection.execute("DELETE FROM cvs WHERE id = ?", (cv_id,))
        connection.commit()

    return cursor.rowcount > 0


def _row_to_cv(row) -> CV:
    return CV(
        id=int(row["id"]),
        title=row["title"],
        full_name=row["full_name"],
        email=row["email"],
        phone=row["phone"],
        professional_summary=row["professional_summary"],
        experience_summary=row["experience_summary"],
        education_summary=row["education_summary"],
        skills=row["skills"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deleted_at=row["deleted_at"],
        structured_schema_version=_row_value(row, "structured_schema_version"),
        structured_payload=_row_value(row, "structured_payload"),
        structured_payload_status=_row_value(row, "structured_payload_status") or "legacy",
    )


def _row_value(row, column_name: str):
    if column_name not in row.keys():
        return None
    return row[column_name]
