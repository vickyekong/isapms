import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from django.conf import settings
from django.db import transaction
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier

from apps.records.services import attendance_stats, earlier_results, gpa_for_results

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = [
    "attendance_percentage",
    "ca_score",
    "exam_score",
    "courses_registered",
    "previously_failed_courses",
    "previous_cgpa",
    "historical_performance",
]
GRADE_LABELS = ["A", "B", "C", "D", "F"]
RISK_BY_GRADE = {"A": "low", "B": "low", "C": "medium", "D": "high", "F": "high"}
MIN_TRAINING_ROWS = 40
PREDICTION_DISCLAIMER = (
    "This prediction supports lecturers and administrators in identifying students who may need "
    "academic support. It does not replace professional academic judgement and is not a final academic decision."
)


class AnalyticsError(Exception):
    def __init__(self, message):
        super().__init__(message)
        self.message = message


class InsufficientDataError(AnalyticsError):
    pass


def _number(value):
    if value is None:
        return np.nan
    return float(value)


def build_feature_row(enrolment, *, allow_partial=False):
    from apps.records.models import Assessment

    assessment = Assessment.objects.filter(enrolment=enrolment).first()
    if assessment is None or assessment.ca_score is None:
        raise InsufficientDataError(
            "This student does not have enough academic records to generate a reliable prediction. "
            "A continuous assessment score is required."
        )
    if assessment.exam_score is None and not allow_partial:
        raise InsufficientDataError(
            "This student does not have enough academic records to generate a reliable prediction. "
            "The examination score has not been recorded."
        )

    stats = attendance_stats(enrolment)
    if stats["sessions"] == 0 and assessment.exam_score is None:
        raise InsufficientDataError(
            "This student does not have enough academic records to generate a reliable prediction. "
            "Attendance has not been recorded for this course."
        )

    previous = earlier_results(enrolment.student, enrolment.session, enrolment.semester)
    previous_gpa = gpa_for_results(previous)
    if previous_gpa is None:
        previous_gpa = enrolment.student.prior_cgpa
    historical_values = [float(result.total_score) for result in previous]
    historical = float(np.mean(historical_values)) if historical_values else _number(previous_gpa) * 20
    courses_registered = enrolment.student.enrolments.filter(
        session=enrolment.session, semester=enrolment.semester, is_deleted=False, status="enrolled"
    ).count()
    previously_failed = sum(1 for result in previous if result.grade == "F")
    data_status = "partial" if assessment.exam_score is None else "complete"
    return {
        "attendance_percentage": 0 if stats["percentage"] is None else stats["percentage"],
        "ca_score": _number(assessment.ca_score),
        "exam_score": _number(assessment.exam_score),
        "courses_registered": courses_registered,
        "previously_failed_courses": previously_failed,
        "previous_cgpa": _number(previous_gpa),
        "historical_performance": historical,
    }, data_status


def build_training_frame():
    from apps.records.models import Result

    rows = []
    targets = []
    results = Result.objects.select_related(
        "assessment", "enrolment__student", "enrolment__course", "enrolment__session", "enrolment__semester"
    )
    for result in results:
        try:
            features, _status = build_feature_row(result.enrolment, allow_partial=False)
        except InsufficientDataError:
            continue
        if result.grade not in GRADE_LABELS:
            continue
        rows.append(features)
        targets.append(result.grade)
    frame = pd.DataFrame(rows, columns=FEATURE_COLUMNS)
    return frame, targets


def validate_training_frame(frame, targets):
    if frame.empty:
        raise AnalyticsError("The training dataset is empty. Record results before training the model.")
    missing_columns = [column for column in FEATURE_COLUMNS if column not in frame.columns]
    if missing_columns:
        raise AnalyticsError(f"Training data is missing required features: {', '.join(missing_columns)}.")
    if len(frame) < MIN_TRAINING_ROWS:
        raise AnalyticsError(
            f"At least {MIN_TRAINING_ROWS} completed results are required to train the model. "
            f"Only {len(frame)} usable rows were found."
        )
    counts = pd.Series(targets).value_counts()
    too_small = [grade for grade in GRADE_LABELS if counts.get(grade, 0) < 2]
    if too_small:
        raise AnalyticsError(
            "Each grade (A, B, C, D and F) needs at least two sample results before the model can be trained. "
            f"Under-represented grades: {', '.join(too_small)}."
        )
    return frame


def train_model(*, actor=None, sample=False):
    from apps.analytics.models import ModelVersion

    frame, targets = build_training_frame()
    frame = validate_training_frame(frame, targets)
    features = frame[FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
    imputer = SimpleImputer(strategy="median")
    transformed = imputer.fit_transform(features)
    try:
        x_train, x_test, y_train, y_test = train_test_split(
            transformed, targets, test_size=0.25, random_state=42, stratify=targets
        )
    except ValueError as exc:
        raise AnalyticsError(
            "The dataset could not be split by grade. Add more results for each grade and try again."
        ) from exc

    classifier = DecisionTreeClassifier(criterion="gini", max_depth=6, min_samples_leaf=2, random_state=42)
    classifier.fit(x_train, y_train)
    predictions = classifier.predict(x_test)
    labels_present = [label for label in GRADE_LABELS if label in set(y_test) or label in set(predictions)]
    matrix = confusion_matrix(y_test, predictions, labels=GRADE_LABELS)
    per_class_precision = precision_score(y_test, predictions, labels=GRADE_LABELS, average=None, zero_division=0)
    per_class_recall = recall_score(y_test, predictions, labels=GRADE_LABELS, average=None, zero_division=0)
    per_class_f1 = f1_score(y_test, predictions, labels=GRADE_LABELS, average=None, zero_division=0)
    class_metrics = {
        grade: {
            "precision": round(float(per_class_precision[index]), 4),
            "recall": round(float(per_class_recall[index]), 4),
            "f1_score": round(float(per_class_f1[index]), 4),
        }
        for index, grade in enumerate(GRADE_LABELS)
    }
    version = datetime.now().strftime("dt-%Y%m%d%H%M%S")
    artifact_dir = Path(settings.MODEL_ARTIFACT_DIR)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / f"{version}.joblib"
    joblib.dump(
        {
            "model": classifier,
            "imputer": imputer,
            "features": FEATURE_COLUMNS,
            "labels": GRADE_LABELS,
        },
        artifact_path,
    )
    with transaction.atomic():
        ModelVersion.objects.filter(is_active=True).update(is_active=False)
        model_version = ModelVersion.objects.create(
            version=version,
            accuracy=round(float(accuracy_score(y_test, predictions)), 4),
            precision=round(float(precision_score(y_test, predictions, average="weighted", zero_division=0)), 4),
            recall=round(float(recall_score(y_test, predictions, average="weighted", zero_division=0)), 4),
            f1_score=round(float(f1_score(y_test, predictions, average="weighted", zero_division=0)), 4),
            confusion_matrix={"labels": GRADE_LABELS, "matrix": matrix.tolist()},
            class_metrics=class_metrics,
            feature_names=FEATURE_COLUMNS,
            training_rows=len(x_train),
            test_rows=len(x_test),
            artifact_path=str(artifact_path),
            is_active=True,
            is_sample=sample,
            notes="Decision Tree Classifier trained on completed course results. " + " ".join(labels_present),
        )
    return model_version


def active_bundle():
    from apps.analytics.models import ModelVersion

    model_version = ModelVersion.objects.filter(is_active=True).first()
    if model_version is None or not Path(model_version.artifact_path).exists():
        raise AnalyticsError("No trained model is available. An administrator needs to train the model first.")
    bundle = joblib.load(model_version.artifact_path)
    return model_version, bundle


def risk_for_grade(grade):
    return RISK_BY_GRADE.get(grade, "high")


def predict_for_enrolment(enrolment, *, actor=None, allow_partial=True, sample=False):
    from apps.analytics.models import Prediction

    model_version, bundle = active_bundle()
    features, data_status = build_feature_row(enrolment, allow_partial=allow_partial)
    frame = pd.DataFrame([features], columns=FEATURE_COLUMNS)
    transformed = bundle["imputer"].transform(frame)
    classifier = bundle["model"]
    predicted = classifier.predict(transformed)[0]
    probabilities = classifier.predict_proba(transformed)[0]
    class_index = list(classifier.classes_).index(predicted)
    confidence = round(float(probabilities[class_index]), 4)
    risk = risk_for_grade(predicted)
    prediction = Prediction.objects.create(
        student=enrolment.student,
        course=enrolment.course,
        model_version=model_version,
        predicted_grade=predicted,
        confidence=confidence,
        risk_level=risk,
        feature_snapshot={key: None if (isinstance(value, float) and np.isnan(value)) else value for key, value in features.items()},
        data_status=data_status,
        requested_by=actor if getattr(actor, "is_authenticated", False) else None,
        is_sample=sample,
    )
    _notify(prediction)
    return prediction


def _notify(prediction):
    from apps.accounts.models import Notification

    student_user = prediction.student.user
    title = f"Academic alert: predicted grade {prediction.predicted_grade}"
    message = (
        f"A decision-support prediction for {prediction.student.full_name} "
        f"({prediction.course.code if prediction.course else 'general'}) "
        f"is grade {prediction.predicted_grade}, {prediction.get_risk_level_display()}, "
        f"confidence {prediction.confidence:.0%}. {PREDICTION_DISCLAIMER}"
    )
    recipients = []
    if student_user:
        recipients.append(student_user)
    if prediction.course:
        for assignment in prediction.course.assignments.select_related("lecturer__user"):
            if assignment.lecturer.user:
                recipients.append(assignment.lecturer.user)
    seen = set()
    for recipient in recipients:
        if recipient.id in seen:
            continue
        seen.add(recipient.id)
        Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            category=Notification.Category.ALERT if prediction.risk_level != "low" else Notification.Category.INFO,
            link="/at-risk" if getattr(recipient, "role", "") != "student" else "/predictions",
        )


def latest_predictions():
    from apps.analytics.models import Prediction

    return Prediction.objects.order_by("student_id", "-created_at").distinct()
