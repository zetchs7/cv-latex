from app.database import get_connection
from app.models import CV
from app.schemas import CVFormData
from app.services.structured_cv_service import (
    STRUCTURED_PAYLOAD_STATUS_VALID,
    build_valid_structured_columns_from_legacy,
    build_legacy_structured_columns,
    resolve_structured_cv_state,
)
from app.validations.cv_validations import build_cv_form_data, build_duplicate_title, validate_cv_form


class DuplicateCVError(ValueError):
    pass


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
    current_cv = get_cv(cv_id)
    if current_cv is None:
        return False

    values = form_data.as_database_values()
    values.update(_build_structured_columns_for_legacy_update(current_cv, form_data))
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


def _build_structured_columns_for_legacy_update(current_cv: CV, form_data: CVFormData) -> dict[str, object]:
    if not resolve_structured_cv_state(current_cv).is_structured:
        return build_legacy_structured_columns()

    try:
        return build_valid_structured_columns_from_legacy(form_data, metadata_source="legacy_edit")
    except ValueError:
        return build_legacy_structured_columns()


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
