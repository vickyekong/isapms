from rest_framework import serializers

from apps.analytics.engine import PREDICTION_DISCLAIMER
from apps.analytics.models import ModelVersion, Prediction


class ModelVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelVersion
        fields = [
            "id",
            "version",
            "algorithm",
            "accuracy",
            "precision",
            "recall",
            "f1_score",
            "confusion_matrix",
            "class_metrics",
            "feature_names",
            "training_rows",
            "test_rows",
            "is_active",
            "is_sample",
            "notes",
            "trained_at",
        ]


class PredictionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    matric_number = serializers.CharField(source="student.matric_number", read_only=True)
    course_code = serializers.CharField(source="course.code", read_only=True)
    model_version_label = serializers.CharField(source="model_version.version", read_only=True)
    disclaimer = serializers.SerializerMethodField()

    class Meta:
        model = Prediction
        fields = [
            "id",
            "student",
            "student_name",
            "matric_number",
            "course",
            "course_code",
            "predicted_grade",
            "confidence",
            "risk_level",
            "feature_snapshot",
            "data_status",
            "model_version",
            "model_version_label",
            "disclaimer",
            "is_sample",
            "created_at",
        ]
        read_only_fields = fields

    def get_disclaimer(self, obj):
        return PREDICTION_DISCLAIMER
