from dataclasses import dataclass


@dataclass(frozen=True)
class CVFormData:
    title: str
    full_name: str
    email: str
    phone: str
    professional_summary: str
    experience_summary: str
    education_summary: str
    skills: str

    def as_database_values(self) -> dict[str, str]:
        return {
            "title": self.title,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "professional_summary": self.professional_summary,
            "experience_summary": self.experience_summary,
            "education_summary": self.education_summary,
            "skills": self.skills,
        }


@dataclass(frozen=True)
class CoverLetterFormData:
    company: str
    position: str
    contact: str
    greeting: str
    introduction: str
    body: str
    closing: str
    signature: str
    associated_cv_id: int | None

    def as_database_values(self) -> dict[str, str | int | None]:
        return {
            "company": self.company,
            "position": self.position,
            "contact": self.contact,
            "greeting": self.greeting,
            "introduction": self.introduction,
            "body": self.body,
            "closing": self.closing,
            "signature": self.signature,
            "associated_cv_id": self.associated_cv_id,
        }
