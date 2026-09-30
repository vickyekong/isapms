from django.conf import settings

from apps.accounts.models import SystemSetting

DEFAULT_GRADING_SCALE = [
    {"grade": "A", "min": 70, "max": 100, "point": 5, "remark": "Excellent"},
    {"grade": "B", "min": 60, "max": 69.99, "point": 4, "remark": "Very good"},
    {"grade": "C", "min": 50, "max": 59.99, "point": 3, "remark": "Good"},
    {"grade": "D", "min": 45, "max": 49.99, "point": 2, "remark": "Pass"},
    {"grade": "F", "min": 0, "max": 44.99, "point": 0, "remark": "Fail"},
]

DEFAULT_SETTINGS = {
    "institution_name": {
        "value": getattr(settings, "INSTITUTION_NAME", "Nexus State University"),
        "description": "Institution name shown in the interface and reports.",
    },
    "institution_short_name": {
        "value": getattr(settings, "INSTITUTION_SHORT_NAME", "NSU"),
        "description": "Short institution name.",
    },
    "attendance_threshold": {
        "value": 75,
        "description": "Attendance percentage below which a student is flagged.",
    },
    "ca_max": {"value": 40, "description": "Maximum continuous assessment score."},
    "exam_max": {"value": 60, "description": "Maximum examination score."},
    "grading_scale": {
        "value": DEFAULT_GRADING_SCALE,
        "description": "Configurable grade boundaries and grade points.",
    },
}


def ensure_default_settings():
    for key, payload in DEFAULT_SETTINGS.items():
        SystemSetting.objects.get_or_create(
            key=key, defaults={"value": payload["value"], "description": payload["description"]}
        )


def get_setting(key, default=None):
    try:
        row = SystemSetting.objects.filter(key=key).first()
    except Exception:
        row = None
    if row is None:
        fallback = DEFAULT_SETTINGS.get(key, {}).get("value", default)
        return fallback
    return row.value
