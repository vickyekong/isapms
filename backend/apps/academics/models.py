from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.accounts.models import SoftDeleteModel


class Faculty(SoftDeleteModel):
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "faculties"

    def __str__(self):
        return self.name


class Department(SoftDeleteModel):
    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name="departments")
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["faculty__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["faculty", "code"], name="unique_department_code_per_faculty"),
        ]
        indexes = [models.Index(fields=["faculty", "name"])]

    def __str__(self):
        return f"{self.name} ({self.faculty.code})"


class AcademicSession(SoftDeleteModel):
    name = models.CharField(max_length=20, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.name


class Semester(SoftDeleteModel):
    class Name(models.TextChoices):
        FIRST = "first", "First semester"
        SECOND = "second", "Second semester"

    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name="semesters")
    name = models.CharField(max_length=20, choices=Name.choices)
    is_current = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["session__start_date", "name"]
        constraints = [
            models.UniqueConstraint(fields=["session", "name"], name="unique_semester_per_session"),
        ]

    def __str__(self):
        return f"{self.session.name} {self.get_name_display()}"


class Student(SoftDeleteModel):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        GRADUATED = "graduated", "Graduated"
        WITHDRAWN = "withdrawn", "Withdrawn"

    class Level(models.IntegerChoices):
        L100 = 100, "100"
        L200 = 200, "200"
        L300 = 300, "300"
        L400 = 400, "400"
        L500 = 500, "500"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="student_profile"
    )
    matric_number = models.CharField(max_length=32, unique=True)
    first_name = models.CharField(max_length=80)
    surname = models.CharField(max_length=80)
    email = models.EmailField(unique=True)
    telephone = models.CharField(max_length=20)
    gender = models.CharField(max_length=10, choices=Gender.choices)
    date_of_birth = models.DateField()
    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name="students")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="students")
    programme = models.CharField(max_length=160)
    level = models.PositiveSmallIntegerField(choices=Level.choices, db_index=True)
    admission_year = models.PositiveSmallIntegerField()
    current_session = models.ForeignKey(
        AcademicSession, null=True, blank=True, on_delete=models.SET_NULL, related_name="current_students"
    )
    prior_cgpa = models.DecimalField(
        max_digits=4, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    current_cgpa = models.DecimalField(
        max_digits=4, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        ordering = ["surname", "first_name"]
        indexes = [
            models.Index(fields=["faculty", "department", "level"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.matric_number} {self.surname}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.surname}"


class Lecturer(SoftDeleteModel):
    class EmploymentStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        ON_LEAVE = "on_leave", "On leave"
        RETIRED = "retired", "Retired"
        INACTIVE = "inactive", "Inactive"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="lecturer_profile"
    )
    staff_id = models.CharField(max_length=32, unique=True)
    first_name = models.CharField(max_length=80)
    surname = models.CharField(max_length=80)
    email = models.EmailField(unique=True)
    telephone = models.CharField(max_length=20, blank=True)
    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name="lecturers")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="lecturers")
    employment_status = models.CharField(
        max_length=20, choices=EmploymentStatus.choices, default=EmploymentStatus.ACTIVE, db_index=True
    )

    class Meta:
        ordering = ["surname", "first_name"]

    def __str__(self):
        return f"{self.staff_id} {self.full_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.surname}"


class Course(SoftDeleteModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    code = models.CharField(max_length=20)
    title = models.CharField(max_length=200)
    credit_units = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(6)])
    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name="courses")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="courses")
    level = models.PositiveSmallIntegerField(choices=Student.Level.choices)
    academic_session = models.ForeignKey(AcademicSession, on_delete=models.PROTECT, related_name="courses")
    semester = models.ForeignKey(Semester, on_delete=models.PROTECT, related_name="courses")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["code", "academic_session", "semester"],
                name="unique_course_code_per_academic_context",
            )
        ]
        indexes = [models.Index(fields=["department", "level", "status"])]

    def __str__(self):
        return f"{self.code} {self.title}"


class CourseAssignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="assignments")
    lecturer = models.ForeignKey(Lecturer, on_delete=models.CASCADE, related_name="assignments")
    is_primary = models.BooleanField(default=False)
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_sample = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["course", "lecturer"], name="unique_lecturer_course_assignment"),
        ]

    def __str__(self):
        return f"{self.lecturer.staff_id} -> {self.course.code}"


class Enrolment(SoftDeleteModel):
    class Status(models.TextChoices):
        ENROLLED = "enrolled", "Enrolled"
        DROPPED = "dropped", "Dropped"

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrolments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrolments")
    session = models.ForeignKey(AcademicSession, on_delete=models.PROTECT, related_name="enrolments")
    semester = models.ForeignKey(Semester, on_delete=models.PROTECT, related_name="enrolments")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ENROLLED, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "course"], name="unique_student_course_enrolment"),
        ]
        indexes = [models.Index(fields=["session", "semester", "status"])]

    def __str__(self):
        return f"{self.student.matric_number} {self.course.code}"
