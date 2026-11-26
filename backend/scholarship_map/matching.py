"""Conservative eligibility checks; preference scores are not admission probabilities."""
from .models import MatchResult, Profile, Scholarship


def recommend(record: Scholarship, profile: Profile) -> MatchResult:
    reasons, unknown, excluded = [], [], []
    if profile.nationality in record.excluded_nationalities:
        excluded.append("الجنسية مستثناة من هذه المنحة")
    elif not record.nationalities:
        unknown.append("الجنسية المطلوبة غير محددة في المصدر")
    elif "*" not in record.nationalities and profile.nationality not in record.nationalities:
        excluded.append("الجنسية لا تطابق الجنسيات المذكورة")
    else:
        reasons.append("الجنسية ضمن الفئات المذكورة")

    if not record.degrees:
        unknown.append("المرحلة الدراسية بحاجة تحقق")
    elif profile.degree not in record.degrees:
        excluded.append("المرحلة الدراسية لا تطابق طلبك")
    else:
        reasons.append("المرحلة الدراسية مطابقة")

    field_match = profile.field in record.fields or "all" in record.fields
    if not record.fields:
        unknown.append("التخصصات المتاحة غير محددة")
    elif not field_match:
        excluded.append("التخصص ليس ضمن المجالات المذكورة")
    else:
        reasons.append("التخصص ضمن المجالات المتاحة")

    if record.minimum_gpa is None:
        unknown.append("لم يذكر المصدر حدًا واضحًا للمعدل")
    elif profile.gpa is None:
        unknown.append("أدخل معدلك لفحص شرط المعدل")
    elif record.gpa_scale != profile.gpa_scale:
        unknown.append("مقياس المعدل مختلف؛ يلزم الرجوع لمعادلة الجهة المانحة")
    elif profile.gpa < record.minimum_gpa:
        excluded.append("المعدل أقل من الحد المعلن")
    else:
        reasons.append("المعدل يحقق الحد المعلن")

    country_match = bool(set(profile.preferred_countries) & set(record.countries))
    if country_match:
        reasons.append("الوجهة ضمن دولك المفضلة")
    field_score = 1.0 if field_match else 0.0
    if "all" in record.fields and profile.field not in record.fields:
        field_score = 0.65
    score = (70 * field_score + 30 * country_match) if profile.preferred_countries else 100 * field_score
    unknown.extend(record.extra_requirements)
    return MatchResult(
        compatible=not excluded,
        status="excluded" if excluded else "potential" if unknown else "matched",
        score=round(score, 1), reasons=reasons, uncertainties=list(dict.fromkeys(unknown)),
        excluded_reasons=excluded,
    )
