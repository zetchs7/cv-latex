from dataclasses import dataclass

from app.models import CV


MIN_RECOMMENDED_CV_LENGTH = 280
MAX_RECOMMENDED_CV_LENGTH = 4500
MAX_ATS_SCORE = 100


@dataclass(frozen=True)
class AtsChecklistItem:
    key: str
    label: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class AtsAnalysisResult:
    cv_id: int
    cv_title: str
    score: int
    max_score: int
    status: str
    total_characters: int
    checklist: list[AtsChecklistItem]
    empty_sections: list[str]
    recommendations: list[str]
    warnings: list[str]


def analyze_cv_ats(cv: CV) -> AtsAnalysisResult:
    normalized_sections = {
        "email": _normalize_text(cv.email),
        "phone": _normalize_text(cv.phone),
        "professional_summary": _normalize_text(cv.professional_summary),
        "experience_summary": _normalize_text(cv.experience_summary),
        "education_summary": _normalize_text(cv.education_summary),
        "skills": _normalize_text(cv.skills),
    }
    total_characters = _estimate_cv_length(cv)
    has_experience = bool(normalized_sections["experience_summary"])
    has_education = bool(normalized_sections["education_summary"])
    length_is_recommended = MIN_RECOMMENDED_CV_LENGTH <= total_characters <= MAX_RECOMMENDED_CV_LENGTH

    checklist = [
        AtsChecklistItem(
            key="email",
            label="Email presente",
            passed=bool(normalized_sections["email"]),
            detail="Incluye un email de contacto visible." if normalized_sections["email"] else "Falta email de contacto.",
        ),
        AtsChecklistItem(
            key="phone",
            label="Telefono presente",
            passed=bool(normalized_sections["phone"]),
            detail="Incluye un telefono de contacto visible." if normalized_sections["phone"] else "Falta telefono de contacto.",
        ),
        AtsChecklistItem(
            key="professional_summary",
            label="Resumen profesional presente",
            passed=bool(normalized_sections["professional_summary"]),
            detail="El CV incluye un resumen profesional." if normalized_sections["professional_summary"] else "Falta el resumen profesional.",
        ),
        AtsChecklistItem(
            key="experience_summary",
            label="Experiencia presente",
            passed=has_experience,
            detail="La experiencia laboral o de proyectos esta cargada." if has_experience else "Falta la seccion de experiencia.",
        ),
        AtsChecklistItem(
            key="education_summary",
            label="Educacion presente",
            passed=has_education,
            detail="La educacion o certificaciones estan cargadas." if has_education else "Falta la seccion de educacion.",
        ),
        AtsChecklistItem(
            key="skills",
            label="Skills cargadas",
            passed=bool(normalized_sections["skills"]),
            detail="La seccion de skills tiene contenido." if normalized_sections["skills"] else "Falta la seccion de skills.",
        ),
        AtsChecklistItem(
            key="length",
            label="Longitud aproximada adecuada",
            passed=length_is_recommended,
            detail=_build_length_detail(total_characters, length_is_recommended),
        ),
    ]

    empty_sections = [
        label
        for label, key in (
            ("Email", "email"),
            ("Telefono", "phone"),
            ("Resumen profesional", "professional_summary"),
            ("Experiencia", "experience_summary"),
            ("Educacion", "education_summary"),
            ("Skills", "skills"),
        )
        if not normalized_sections[key]
    ]

    recommendations = _build_recommendations(normalized_sections, total_characters)
    warnings = _build_warnings(empty_sections, total_characters)
    passed_checks = sum(1 for item in checklist if item.passed)
    score = int(round((passed_checks / len(checklist)) * MAX_ATS_SCORE))

    return AtsAnalysisResult(
        cv_id=cv.id,
        cv_title=cv.title,
        score=score,
        max_score=MAX_ATS_SCORE,
        status=_build_status(score),
        total_characters=total_characters,
        checklist=checklist,
        empty_sections=empty_sections,
        recommendations=recommendations,
        warnings=warnings,
    )


def _build_status(score: int) -> str:
    if score >= 85:
        return "Bueno"
    if score >= 60:
        return "Mejorable"
    return "Insuficiente"


def _build_length_detail(total_characters: int, length_is_recommended: bool) -> str:
    if length_is_recommended:
        return f"Longitud estimada correcta: {total_characters} caracteres."
    if total_characters < MIN_RECOMMENDED_CV_LENGTH:
        return f"El CV es corto para este chequeo basico: {total_characters} caracteres."
    return f"El CV puede estar demasiado extenso para una lectura ATS simple: {total_characters} caracteres."


def _build_recommendations(normalized_sections: dict[str, str], total_characters: int) -> list[str]:
    recommendations: list[str] = []
    has_experience = bool(normalized_sections["experience_summary"])
    has_education = bool(normalized_sections["education_summary"])

    if not normalized_sections["email"]:
        recommendations.append("Agregar un email de contacto claro y profesional.")
    if not normalized_sections["phone"]:
        recommendations.append("Agregar un telefono de contacto visible.")
    if not normalized_sections["professional_summary"]:
        recommendations.append("Completar el resumen profesional con un perfil breve y orientado al puesto.")
    if not has_experience and not has_education:
        recommendations.append("Cargar experiencia, educacion o ambas para dar contexto al perfil.")
    elif not has_experience:
        recommendations.append("Agregar experiencia laboral o proyectos relevantes.")
    elif not has_education:
        recommendations.append("Agregar educacion o certificaciones para reforzar el perfil.")
    if not normalized_sections["skills"]:
        recommendations.append("Listar skills concretas, tecnologias y herramientas.")
    if total_characters < MIN_RECOMMENDED_CV_LENGTH:
        recommendations.append("Ampliar el contenido del CV con logros, contexto y resultados medibles.")
    if total_characters > MAX_RECOMMENDED_CV_LENGTH:
        recommendations.append("Reducir el contenido para dejar un CV mas escaneable y directo.")

    if not recommendations:
        recommendations.append("El CV cubre los puntos basicos de este chequeo ATS. Mantener el contenido actualizado y especifico.")

    return recommendations


def _build_warnings(empty_sections: list[str], total_characters: int) -> list[str]:
    warnings: list[str] = []

    for section_name in empty_sections:
        warnings.append(f"Seccion vacia detectada: {section_name}.")

    if total_characters < MIN_RECOMMENDED_CV_LENGTH:
        warnings.append("El contenido total puede resultar demasiado breve para filtros basicos.")
    if total_characters > MAX_RECOMMENDED_CV_LENGTH:
        warnings.append("El contenido total puede ser demasiado largo para una lectura inicial rapida.")

    return warnings


def _estimate_cv_length(cv: CV) -> int:
    blocks = (
        cv.title,
        cv.full_name,
        cv.email,
        cv.phone,
        cv.professional_summary,
        cv.experience_summary,
        cv.education_summary,
        cv.skills,
    )
    return len(" ".join(_normalize_text(block) for block in blocks if _normalize_text(block)))


def _normalize_text(value: str) -> str:
    return " ".join(value.split()).strip()
