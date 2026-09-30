from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Q

from apps.accounts.services import get_setting


class ScoreError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


def grading_scale():
    scale = get_setting("grading_scale") or []
    cleaned = []
    for band in scale:
        try:
            cleaned.append(
                {
                    "grade": str(band["grade"]).upper(),
                    "min": float(band["min"]),
                    "max": float(band["max"]),
                    "point": Decimal(str(band["point"])),
                    "remark": band.get("remark") or band["grade"],
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(cleaned, key=lambda item: item["min"], reverse=True)


def score_limits():
    return float(get_setting("ca_max", 40)), float(get_setting("exam_max", 60))


def validate_scores(ca_score, exam_score):
    ca_max, exam_max = score_limits()
    if ca_score is None:
        raise ScoreError("Continuous assessment score is required.")
    ca_value = float(ca_score)
    if ca_value < 0 or ca_value > ca_max:
        raise ScoreError(f"Continuous assessment must be between 0 and {ca_max:g}.")
    exam_value = None
    if exam_score is not None and exam_score != "":
        exam_value = float(exam_score)
        if exam_value < 0 or exam_value > exam_max:
            raise ScoreError(f"Examination score must be between 0 and {exam_max:g}.")
    total = ca_value + (exam_value or 0)
    if total > 100:
        raise ScoreError("Total score cannot exceed 100.")
    return ca_value, exam_value


def assign_grade(total):
    total_value = float(total)
    if total_value < 0 or total_value > 100:
        raise ScoreError("Total score must be between 0 and 100.")
    for band in grading_scale():
        if total_value >= band["min"]:
            return band["grade"], band["point"], band["remark"]
    return "F", Decimal("0"), "Fail"


def quantize_score(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def attendance_stats(enrolment):
    records = enrolment.attendance_records.all()
    present = records.filter(status="present").count()
    absent = records.filter(status="absent").count()
    excused = records.filter(status="excused").count()
    counted = present + absent
    percentage = round((present / counted) * 100, 2) if counted else None
    threshold = float(get_setting("attendance_threshold", 75))
    return {
        "present": present,
        "absent": absent,
        "excused": excused,
        "sessions": present + absent + excused,
        "percentage": percentage,
        "below_threshold": percentage is not None and percentage < threshold,
        "threshold": threshold,
    }


def gpa_for_results(results):
    units = 0
    points = Decimal("0")
    for result in results:
        credit_units = result.enrolment.course.credit_units
        units += credit_units
        points += Decimal(result.grade_point) * Decimal(credit_units)
    if units == 0:
        return None
    return (points / Decimal(units)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def earlier_results(student, session, semester, exclude_result_id=None):
    from apps.records.models import Result

    query = Result.objects.filter(enrolment__student=student).select_related(
        "enrolment__course", "enrolment__session", "enrolment__semester"
    )
    if exclude_result_id:
        query = query.exclude(pk=exclude_result_id)
    selected = []
    for result in query:
        result_session = result.enrolment.session
        result_semester = result.enrolment.semester.name
        if result_session.start_date < session.start_date:
            selected.append(result)
        elif result_session.id == session.id and result_semester == "first" and semester.name == "second":
            selected.append(result)
    return selected


def semester_gpa(student, session, semester):
    from apps.records.models import Result

    results = Result.objects.filter(
        enrolment__student=student,
        enrolment__session=session,
        enrolment__semester=semester,
        enrolment__status="enrolled",
        enrolment__is_deleted=False,
    ).select_related("enrolment__course")
    return gpa_for_results(results)


def update_student_cgpa(student):
    from apps.records.models import Result

    results = Result.objects.filter(enrolment__student=student, enrolment__is_deleted=False).select_related(
        "enrolment__course"
    )
    cgpa = gpa_for_results(results)
    student.current_cgpa = cgpa if cgpa is not None else student.prior_cgpa
    student.save(update_fields=["current_cgpa", "updated_at"])
    return student.current_cgpa


def apply_assessment(enrolment, ca_score, exam_score, actor, sample=False):
    from apps.records.models import Assessment, Result

    existing_result = Result.objects.filter(enrolment=enrolment).first()
    if existing_result and existing_result.is_locked and getattr(actor, "role", None) != "admin":
        raise ScoreError("This result is locked and can only be changed by an administrator.")

    ca_value, exam_value = validate_scores(ca_score, exam_score)
    assessment, _created = Assessment.objects.get_or_create(
        enrolment=enrolment,
        defaults={
            "ca_score": quantize_score(ca_value),
            "exam_score": quantize_score(exam_value) if exam_value is not None else None,
            "recorded_by": actor if getattr(actor, "is_authenticated", False) else None,
            "is_sample": sample,
        },
    )
    assessment.ca_score = quantize_score(ca_value)
    assessment.exam_score = quantize_score(exam_value) if exam_value is not None else None
    assessment.recorded_by = actor if getattr(actor, "is_authenticated", False) else assessment.recorded_by
    assessment.save()

    result = Result.objects.filter(assessment=assessment).first()
    if exam_value is None:
        return assessment, result

    total = quantize_score(ca_value + exam_value)
    grade, point, remark = assign_grade(total)
    if result is None:
        result = Result.objects.create(
            enrolment=enrolment,
            assessment=assessment,
            total_score=total,
            grade=grade,
            grade_point=point,
            remark=remark,
            is_validated=True,
            is_sample=sample,
        )
    else:
        result.total_score = total
        result.grade = grade
        result.grade_point = point
        result.remark = remark
        result.is_validated = True
        result.save()
    update_student_cgpa(enrolment.student)
    return assessment, result


def lecturer_can_access_course(user, course_id):
    if getattr(user, "role", None) == "admin":
        return True
    if getattr(user, "role", None) != "lecturer":
        return False
    profile = getattr(user, "lecturer_profile", None)
    if profile is None:
        return False
    return profile.assignments.filter(course_id=course_id).exists()


def scoped_enrolments(user):
    from apps.academics.models import Enrolment

    query = Enrolment.objects.filter(is_deleted=False).select_related(
        "student", "course", "session", "semester", "student__department", "student__faculty"
    )
    role = getattr(user, "role", None)
    if role == "admin":
        return query
    if role == "lecturer":
        profile = getattr(user, "lecturer_profile", None)
        course_ids = profile.assignments.values_list("course_id", flat=True) if profile else []
        return query.filter(course_id__in=course_ids)
    if role == "student":
        profile = getattr(user, "student_profile", None)
        return query.filter(student=profile) if profile else query.none()
    return query.none()


def scoped_students(user):
    from apps.academics.models import Student

    query = Student.objects.filter(is_deleted=False).select_related("faculty", "department", "current_session", "user")
    role = getattr(user, "role", None)
    if role == "admin":
        return query
    if role == "lecturer":
        profile = getattr(user, "lecturer_profile", None)
        course_ids = profile.assignments.values_list("course_id", flat=True) if profile else []
        return query.filter(enrolments__course_id__in=course_ids, enrolments__is_deleted=False).distinct()
    if role == "student":
        profile = getattr(user, "student_profile", None)
        return query.filter(pk=getattr(profile, "pk", None))
    return query.none()
