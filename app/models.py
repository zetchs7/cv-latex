from dataclasses import dataclass


@dataclass(frozen=True)
class CV:
    id: int
    title: str
    full_name: str
    email: str
    phone: str
    professional_summary: str
    experience_summary: str
    education_summary: str
    skills: str
    created_at: str
    updated_at: str
    deleted_at: str | None


@dataclass(frozen=True)
class CoverLetter:
    id: int
    company: str
    position: str
    contact: str
    greeting: str
    introduction: str
    body: str
    closing: str
    signature: str
    associated_cv_id: int | None
    associated_cv_title: str | None
    created_at: str
    updated_at: str
    deleted_at: str | None


@dataclass(frozen=True)
class Application:
    id: int
    company: str
    position: str
    link: str
    source: str
    applied_on: str
    status: str
    associated_cv_id: int | None
    associated_cv_title: str | None
    associated_cover_letter_id: int | None
    associated_cover_letter_label: str | None
    notes: str
    next_action: str
    follow_up_date: str
    created_at: str
    updated_at: str
    deleted_at: str | None
