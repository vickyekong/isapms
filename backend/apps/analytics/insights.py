from collections import Counter

from django.db.models import Count, Max

from apps.accounts.models import AuditLog
from apps.accounts.services import get_setting
from apps.academics.models import Course, Department, Enrolment, Faculty, Lecturer, Student
from apps.analytics.engine import PREDICTION_DISCLAIMER
from apps.analytics.models import ModelVersion, Prediction
from apps.records.models import Attendance, Result
from apps.records.services import attendance_stats, semester_gpa


def _student_brief(student):
    return {
        "id": student.id,
        "matric_number": student.matric_number,
        "full_name": student.full_name,
        "department": student.department.name,
        "department_id": student.department_id,
        "faculty": student.faculty.name,
        "faculty_id": student.faculty_id,
        "level": student.level,
    }


def risk_counts(queryset):
    latest_ids = queryset.values("student_id").annotate(latest_id=Max("id")).values_list("latest_id", flat=True)
    latest = Prediction.objects.filter(id__in=list(latest_ids))
    counts = Counter(latest.values_list("risk_level", flat=True))
    return {"low": counts.get("low", 0), "medium": counts.get("medium", 0), "high": counts.get("high", 0)}


def attendance_trend(enrolment_ids):
    rows = (
        Attendance.objects.filter(enrolment_id__in=enrolment_ids)
        .values("date", "status")
        .annotate(total=Count("id"))
        .order_by("date")
    )
    grouped = {}
    for row in rows:
        bucket = grouped.setdefault(str(row["date"]), {"date": str(row["date"]), "present": 0, "absent": 0, "excused": 0})
        bucket[row["status"]] = row["total"]
    return list(grouped.values())[-12:]


def at_risk_alerts(user):
    from apps.records.services import scoped_enrolments, scoped_students

    students = list(scoped_students(user).select_related("faculty", "department"))
    student_ids = [student.id for student in students]
    latest_ids = (
        Prediction.objects.filter(student_id__in=student_ids)
        .values("student_id")
        .annotate(latest_id=Max("id"))
        .values_list("latest_id", flat=True)
    )
    predictions = Prediction.objects.filter(id__in=list(latest_ids), risk_level__in=["medium", "high"]).select_related(
        "student__faculty", "student__department", "course"
    )
    alerts = []
    seen = set()
    for prediction in predictions:
        seen.add(prediction.student_id)
        alerts.append(
            {
                "student": _student_brief(prediction.student),
                "course": {"id": prediction.course_id, "code": prediction.course.code, "title": prediction.course.title}
                if prediction.course
                else None,
                "risk_level": prediction.risk_level,
                "predicted_grade": prediction.predicted_grade,
                "confidence": prediction.confidence,
                "reason": f"Predicted grade {prediction.predicted_grade}",
                "attendance_percentage": prediction.feature_snapshot.get("attendance_percentage"),
            }
        )
    threshold = float(get_setting("attendance_threshold", 75))
    enrolments = scoped_enrolments(user).filter(status="enrolled", student_id__in=student_ids).select_related(
        "student__faculty", "student__department", "course"
    )
    for enrolment in enrolments:
        stats = attendance_stats(enrolment)
        if stats["percentage"] is None or stats["percentage"] >= threshold:
            continue
        alerts.append(
            {
                "student": _student_brief(enrolment.student),
                "course": {"id": enrolment.course_id, "code": enrolment.course.code, "title": enrolment.course.title},
                "risk_level": "high" if stats["percentage"] < threshold - 15 else "medium",
                "predicted_grade": None,
                "confidence": None,
                "reason": f"Attendance {stats['percentage']}% is below the {threshold:g}% threshold",
                "attendance_percentage": stats["percentage"],
            }
        )
    return alerts


def admin_dashboard():
    students = Student.objects.filter(is_deleted=False)
    faculty_rows = Faculty.objects.filter(is_deleted=False).annotate(total=Count("students", distinct=True))
    department_rows = Department.objects.filter(is_deleted=False).select_related("faculty").annotate(
        total=Count("students", distinct=True)
    )
    grades = Result.objects.values("grade").annotate(total=Count("id")).order_by("grade")
    predictions = Prediction.objects.select_related("student", "course").order_by("-created_at")[:8]
    activity = AuditLog.objects.select_related("actor").order_by("-created_at")[:8]
    model = ModelVersion.objects.filter(is_active=True).first()
    return {
        "role": "admin",
        "disclaimer": PREDICTION_DISCLAIMER,
        "totals": {
            "students": students.count(),
            "lecturers": Lecturer.objects.filter(is_deleted=False).count(),
            "courses": Course.objects.filter(is_deleted=False, status="active").count(),
            "faculties": Faculty.objects.filter(is_deleted=False).count(),
        },
        "students_by_faculty": [{"name": row.name, "value": row.total} for row in faculty_rows],
        "students_by_department": [
            {"name": row.name, "faculty": row.faculty.name, "value": row.total} for row in department_rows
        ],
        "grade_distribution": [{"name": row["grade"], "value": row["total"]} for row in grades],
        "attendance_trends": attendance_trend(Enrolment.objects.filter(is_deleted=False).values_list("id", flat=True)),
        "risk_counts": risk_counts(Prediction.objects.all()),
        "at_risk_alerts": at_risk_alerts_for_ids(students.values_list("id", flat=True))[:8],
        "recent_predictions": [
            {
                "id": item.id,
                "student": item.student.full_name,
                "matric_number": item.student.matric_number,
                "course": item.course.code if item.course else "",
                "predicted_grade": item.predicted_grade,
                "risk_level": item.risk_level,
                "confidence": item.confidence,
                "created_at": item.created_at.isoformat(),
            }
            for item in predictions
        ],
        "recent_activity": [
            {
                "id": item.id,
                "action": item.action,
                "description": item.description,
                "actor": item.actor.get_full_name() if item.actor else "System",
                "created_at": item.created_at.isoformat(),
            }
            for item in activity
        ],
        "active_model": None
        if model is None
        else {
            "version": model.version,
            "accuracy": model.accuracy,
            "precision": model.precision,
            "recall": model.recall,
            "f1_score": model.f1_score,
            "trained_at": model.trained_at.isoformat(),
        },
    }


def at_risk_alerts_for_ids(student_ids):
    student_ids = list(student_ids)
    latest_ids = (
        Prediction.objects.filter(student_id__in=student_ids)
        .values("student_id")
        .annotate(latest_id=Max("id"))
        .values_list("latest_id", flat=True)
    )
    predictions = Prediction.objects.filter(id__in=list(latest_ids), risk_level__in=["medium", "high"]).select_related(
        "student__faculty", "student__department", "course"
    )
    return [
        {
            "student": _student_brief(prediction.student),
            "course": prediction.course.code if prediction.course else None,
            "risk_level": prediction.risk_level,
            "predicted_grade": prediction.predicted_grade,
            "reason": f"Predicted grade {prediction.predicted_grade}",
        }
        for prediction in predictions
    ]


def lecturer_dashboard(user):
    try:
        profile = user.lecturer_profile
    except Lecturer.DoesNotExist:
        return {"role": "lecturer", "courses": [], "enrolled_students": 0, "risk_counts": {"low": 0, "medium": 0, "high": 0}, "at_risk_alerts": [], "recent_activity": []}
    assignments = profile.assignments.select_related("course__academic_session", "course__semester", "course__department")
    course_ids = [assignment.course_id for assignment in assignments]
    enrolments = Enrolment.objects.filter(course_id__in=course_ids, is_deleted=False, status="enrolled")
    courses = []
    for assignment in assignments:
        course_enrolments = enrolments.filter(course=assignment.course)
        present = Attendance.objects.filter(enrolment__in=course_enrolments, status="present").count()
        absent = Attendance.objects.filter(enrolment__in=course_enrolments, status="absent").count()
        counted = present + absent
        courses.append(
            {
                "id": assignment.course_id,
                "code": assignment.course.code,
                "title": assignment.course.title,
                "enrolled": course_enrolments.count(),
                "attendance_percentage": round(present / counted * 100, 2) if counted else None,
                "results_recorded": Result.objects.filter(enrolment__in=course_enrolments).count(),
            }
        )
    return {
        "role": "lecturer",
        "disclaimer": PREDICTION_DISCLAIMER,
        "courses": courses,
        "enrolled_students": enrolments.values("student_id").distinct().count(),
        "risk_counts": risk_counts(Prediction.objects.filter(course_id__in=course_ids)),
        "at_risk_alerts": at_risk_alerts(user)[:8],
        "recent_activity": [
            {
                "id": item.id,
                "action": item.action,
                "description": item.description,
                "created_at": item.created_at.isoformat(),
            }
            for item in AuditLog.objects.filter(actor=user).order_by("-created_at")[:8]
        ],
    }


def student_dashboard(user):
    profile = getattr(user, "student_profile", None)
    if profile is None:
        return {"role": "student", "detail": "No student profile is linked to this account."}
    enrolments = (
        Enrolment.objects.filter(student=profile, is_deleted=False, status="enrolled")
        .select_related("course", "session", "semester")
        .order_by("-session__start_date")
    )
    course_rows = []
    for enrolment in enrolments:
        stats = attendance_stats(enrolment)
        result = Result.objects.filter(enrolment=enrolment).first()
        course_rows.append(
            {
                "enrolment_id": enrolment.id,
                "course_id": enrolment.course_id,
                "code": enrolment.course.code,
                "title": enrolment.course.title,
                "credit_units": enrolment.course.credit_units,
                "session": enrolment.session.name,
                "semester": enrolment.semester.name,
                "attendance_percentage": stats["percentage"],
                "below_threshold": stats["below_threshold"],
                "total_score": float(result.total_score) if result else None,
                "grade": result.grade if result else None,
            }
        )
    current = enrolments.filter(session__is_current=True, semester__is_current=True).first()
    sgpa = None
    if current:
        sgpa = semester_gpa(profile, current.session, current.semester)
        sgpa = float(sgpa) if sgpa is not None else None
    trend = [
        {"name": f"{row['code']} {row['session']}", "grade": row["grade"], "score": row["total_score"]}
        for row in course_rows
        if row["total_score"] is not None
    ]
    alerts = list(user.notifications.filter(category="alert").order_by("-created_at")[:5].values("id", "title", "message", "is_read", "created_at"))
    for alert in alerts:
        alert["created_at"] = alert["created_at"].isoformat()
    return {
        "role": "student",
        "disclaimer": PREDICTION_DISCLAIMER,
        "profile": _student_brief(profile),
        "current_cgpa": float(profile.current_cgpa),
        "prior_cgpa": float(profile.prior_cgpa),
        "semester_gpa": sgpa,
        "courses": course_rows,
        "grade_trend": trend,
        "alerts": alerts,
    }


def build_dashboard(user):
    if user.role == "admin":
        return admin_dashboard()
    if user.role == "lecturer":
        return lecturer_dashboard(user)
    return student_dashboard(user)
