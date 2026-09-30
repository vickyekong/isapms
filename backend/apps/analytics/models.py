from django.conf import settings
from django.db import models

from apps.academics.models import Course, Student


class ModelVersion(models.Model):
    version = models.CharField(max_length=40, unique=True)
    algorithm = models.CharField(max_length=80, default="DecisionTreeClassifier")
    accuracy = models.FloatField()
    precision = models.FloatField()
    recall = models.FloatField()
    f1_score = models.FloatField()
    confusion_matrix = models.JSONField(default=dict)
    class_metrics = models.JSONField(default=dict)
    feature_names = models.JSONField(default=list)
    training_rows = models.PositiveIntegerField()
    test_rows = models.PositiveIntegerField()
    artifact_path = models.CharField(max_length=255)
    is_active = models.BooleanField(default=False, db_index=True)
    is_sample = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    trained_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-trained_at"]

    def __str__(self):
        return self.version


class Prediction(models.Model):
    class Risk(models.TextChoices):
        LOW = "low", "Low risk"
        MEDIUM = "medium", "Medium risk"
        HIGH = "high", "High risk"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="predictions")
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.SET_NULL, related_name="predictions")
    model_version = models.ForeignKey(ModelVersion, on_delete=models.PROTECT, related_name="predictions")
    predicted_grade = models.CharField(max_length=2, db_index=True)
    confidence = models.FloatField()
    risk_level = models.CharField(max_length=20, choices=Risk.choices, db_index=True)
    feature_snapshot = models.JSONField(default=dict)
    data_status = models.CharField(max_length=20, default="complete")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="predictions_requested"
    )
    is_sample = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["student", "risk_level"])]

    def __str__(self):
        return f"{self.student_id} {self.predicted_grade} ({self.risk_level})"
