from app.database import get_connection
from app.models import CV
from app.schemas import CVFormData


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
    values = form_data.as_database_values()

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
                skills
            )
            VALUES (
                :title,
                :full_name,
                :email,
                :phone,
                :professional_summary,
                :experience_summary,
                :education_summary,
                :skills
            )
            """,
            values,
        )
        connection.commit()

    return int(cursor.lastrowid)


def update_cv(cv_id: int, form_data: CVFormData) -> bool:
    values = form_data.as_database_values()
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

    duplicate_data = CVFormData(
        title=f"{source_cv.title} (copia)",
        full_name=source_cv.full_name,
        email=source_cv.email,
        phone=source_cv.phone,
        professional_summary=source_cv.professional_summary,
        experience_summary=source_cv.experience_summary,
        education_summary=source_cv.education_summary,
        skills=source_cv.skills,
    )

    return create_cv(duplicate_data)


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
    )
