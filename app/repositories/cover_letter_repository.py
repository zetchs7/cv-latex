from app.database import get_connection
from app.models import CoverLetter
from app.schemas import CoverLetterFormData


def list_cover_letters() -> list[CoverLetter]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT cover_letters.*, cvs.title AS associated_cv_title
            FROM cover_letters
            LEFT JOIN cvs
                ON cvs.id = cover_letters.associated_cv_id
                AND cvs.deleted_at IS NULL
            WHERE cover_letters.deleted_at IS NULL
            ORDER BY cover_letters.updated_at DESC, cover_letters.id DESC
            """
        ).fetchall()

    return [_row_to_cover_letter(row) for row in rows]


def get_cover_letter(cover_letter_id: int) -> CoverLetter | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT cover_letters.*, cvs.title AS associated_cv_title
            FROM cover_letters
            LEFT JOIN cvs
                ON cvs.id = cover_letters.associated_cv_id
                AND cvs.deleted_at IS NULL
            WHERE cover_letters.id = ? AND cover_letters.deleted_at IS NULL
            """,
            (cover_letter_id,),
        ).fetchone()

    return _row_to_cover_letter(row) if row else None


def create_cover_letter(form_data: CoverLetterFormData) -> int:
    values = form_data.as_database_values()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO cover_letters (
                company,
                position,
                contact,
                greeting,
                introduction,
                body,
                closing,
                signature,
                associated_cv_id
            )
            VALUES (
                :company,
                :position,
                :contact,
                :greeting,
                :introduction,
                :body,
                :closing,
                :signature,
                :associated_cv_id
            )
            """,
            values,
        )
        connection.commit()

    return int(cursor.lastrowid)


def update_cover_letter(cover_letter_id: int, form_data: CoverLetterFormData) -> bool:
    values = form_data.as_database_values()
    values["id"] = cover_letter_id

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE cover_letters
            SET
                company = :company,
                position = :position,
                contact = :contact,
                greeting = :greeting,
                introduction = :introduction,
                body = :body,
                closing = :closing,
                signature = :signature,
                associated_cv_id = :associated_cv_id,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :id AND deleted_at IS NULL
            """,
            values,
        )
        connection.commit()

    return cursor.rowcount > 0


def soft_delete_cover_letter(cover_letter_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE cover_letters
            SET deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND deleted_at IS NULL
            """,
            (cover_letter_id,),
        )
        connection.commit()

    return cursor.rowcount > 0


def _row_to_cover_letter(row) -> CoverLetter:
    return CoverLetter(
        id=int(row["id"]),
        company=row["company"],
        position=row["position"],
        contact=row["contact"],
        greeting=row["greeting"],
        introduction=row["introduction"],
        body=row["body"],
        closing=row["closing"],
        signature=row["signature"],
        associated_cv_id=int(row["associated_cv_id"]) if row["associated_cv_id"] is not None else None,
        associated_cv_title=row["associated_cv_title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deleted_at=row["deleted_at"],
    )
