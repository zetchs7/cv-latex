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
