from app.database import get_connection
from app.models import Application
from app.schemas import ApplicationFormData


def list_applications() -> list[Application]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                applications.*,
                cvs.title AS associated_cv_title,
                cover_letters.company AS associated_cover_letter_company,
                cover_letters.position AS associated_cover_letter_position
            FROM applications
            LEFT JOIN cvs
                ON cvs.id = applications.associated_cv_id
                AND cvs.deleted_at IS NULL
            LEFT JOIN cover_letters
                ON cover_letters.id = applications.associated_cover_letter_id
                AND cover_letters.deleted_at IS NULL
            WHERE applications.deleted_at IS NULL
            ORDER BY applications.updated_at DESC, applications.id DESC
            """
        ).fetchall()

    return [_row_to_application(row) for row in rows]


def get_application(application_id: int) -> Application | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                applications.*,
                cvs.title AS associated_cv_title,
                cover_letters.company AS associated_cover_letter_company,
                cover_letters.position AS associated_cover_letter_position
            FROM applications
            LEFT JOIN cvs
                ON cvs.id = applications.associated_cv_id
                AND cvs.deleted_at IS NULL
            LEFT JOIN cover_letters
                ON cover_letters.id = applications.associated_cover_letter_id
                AND cover_letters.deleted_at IS NULL
            WHERE applications.id = ? AND applications.deleted_at IS NULL
            """,
            (application_id,),
        ).fetchone()

    return _row_to_application(row) if row else None


def create_application(form_data: ApplicationFormData) -> int:
    values = form_data.as_database_values()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO applications (
                company,
                position,
                link,
                source,
                applied_on,
                status,
                associated_cv_id,
                associated_cover_letter_id,
                notes,
                next_action,
                follow_up_date
            )
            VALUES (
                :company,
                :position,
                :link,
                :source,
                :applied_on,
                :status,
                :associated_cv_id,
                :associated_cover_letter_id,
                :notes,
                :next_action,
                :follow_up_date
            )
            """,
            values,
        )
        connection.commit()

    return int(cursor.lastrowid)


def update_application(application_id: int, form_data: ApplicationFormData) -> bool:
    values = form_data.as_database_values()
    values["id"] = application_id

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE applications
            SET
                company = :company,
                position = :position,
                link = :link,
                source = :source,
                applied_on = :applied_on,
                status = :status,
                associated_cv_id = :associated_cv_id,
                associated_cover_letter_id = :associated_cover_letter_id,
                notes = :notes,
                next_action = :next_action,
                follow_up_date = :follow_up_date,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :id AND deleted_at IS NULL
            """,
            values,
        )
        connection.commit()

    return cursor.rowcount > 0


def soft_delete_application(application_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE applications
            SET deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND deleted_at IS NULL
            """,
            (application_id,),
        )
        connection.commit()

    return cursor.rowcount > 0


def _row_to_application(row) -> Application:
    return Application(
        id=int(row["id"]),
        company=row["company"],
        position=row["position"],
        link=row["link"],
        source=row["source"],
        applied_on=row["applied_on"],
        status=row["status"],
        associated_cv_id=int(row["associated_cv_id"]) if row["associated_cv_id"] is not None else None,
        associated_cv_title=row["associated_cv_title"],
        associated_cover_letter_id=int(row["associated_cover_letter_id"]) if row["associated_cover_letter_id"] is not None else None,
        associated_cover_letter_label=_build_cover_letter_label(
            row["associated_cover_letter_company"],
            row["associated_cover_letter_position"],
        ),
        notes=row["notes"],
        next_action=row["next_action"],
        follow_up_date=row["follow_up_date"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deleted_at=row["deleted_at"],
    )


def _build_cover_letter_label(company: str | None, position: str | None) -> str | None:
    parts = [part for part in [company, position] if part]
    if not parts:
        return None
    return " - ".join(parts)
