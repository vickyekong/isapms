from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.academics.models import Enrolment


class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        EXCUSED = "excused", "Excused"

    enrolment = models.ForeignKey(Enrolment, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="attendance_marked"
    )
    is_sample = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(fields=["enrolment", "date"], name="unique_attendance_per_enrolment_date"),
        ]
        indexes = [models.Index(fields=["enrolment", "status"])]

    def __str__(self):
        return f"{self.enrolment_id} {self.date} {self.status}"


class Assessment(models.Model):
    enrolment = models.OneToOneField(Enrolment, on_delete=models.CASCADE, related_name="assessment")
    ca_score = models.DecimalField(
        max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    exam_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assessments_recorded"
    )
    is_sample = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Assessment {self.enrolment_id}"


class Result(models.Model):
    enrolment = models.OneToOneField(Enrolment, on_delete=models.CASCADE, related_name="result")
    assessment = models.OneToOneField(Assessment, on_delete=models.CASCADE, related_name="result")
    total_score = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=2, db_index=True)
    grade_point = models.DecimalField(max_digits=3, decimal_places=2)
    remark = models.CharField(max_length=80, blank=True)
    is_validated = models.BooleanField(default=False, db_index=True)
    is_locked = models.BooleanField(default=False)
    is_sample = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["grade", "is_validated"])]

    def __str__(self):
        return f"{self.enrolment_id} {self.grade}"
