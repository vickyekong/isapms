import numpy as np
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Notification, User
from apps.accounts.services import ensure_default_settings
from apps.academics.models import (
    AcademicSession,
    Course,
    CourseAssignment,
    Department,
    Enrolment,
    Faculty,
    Lecturer,
    Semester,
    Student,
)
from apps.analytics.engine import train_model
from apps.analytics.models import ModelVersion, Prediction
from apps.records.models import Assessment, Attendance, Result
from apps.records.services import assign_grade, quantize_score, update_student_cgpa

SAMPLE_PASSWORD = "Sample@12345"
FIRST_NAMES = [
    "Adaeze", "Chinedu", "Fatima", "Ibrahim", "Ngozi", "Tunde", "Amina", "Emeka", "Halima", "Olumide",
    "Blessing", "Yusuf", "Chioma", "Musa", "Zainab", "Kelechi", "Aisha", "Segun", "Funmilayo", "Ifeanyi",
    "Maryam", "Chukwudi", "Rasheed", "Nneka", "Bola", "Abdullahi", "Yetunde", "Chiamaka", "Seyi", "Hadiza",
]
SURNAMES = [
    "Adeyemi", "Okonkwo", "Bello", "Eze", "Lawal", "Okafor", "Abubakar", "Balogun", "Nwosu", "Danjuma",
    "Ogunleye", "Ibrahim", "Chukwu", "Mohammed", "Adebayo", "Okeke", "Suleiman", "Ojo", "Nwachukwu", "Garba",
]
BANDS = (["A"] * 24) + (["B"] * 24) + (["C"] * 24) + (["D"] * 24) + (["F"] * 24)
SCORE_PLAN = {"A": (32, 48), "B": (26, 40), "C": (22, 33), "D": (18, 29), "F": (12, 18)}
PRIOR_CGPA = {"A": 4.50, "B": 3.60, "C": 2.80, "D": 2.10, "F": 1.20}
ATTENDANCE_RATE = {"A": 0.95, "B": 0.88, "C": 0.76, "D": 0.62, "F": 0.42}
FACULTIES = [
    ("Faculty of Science", "SCI", [("Computer Science", "CSC", "B.Sc. Computer Science"), ("Mathematics", "MTH", "B.Sc. Mathematics"), ("Biochemistry", "BCH", "B.Sc. Biochemistry")]),
    ("Faculty of Engineering", "ENG", [("Electrical Engineering", "EEE", "B.Eng. Electrical Engineering"), ("Civil Engineering", "CVE", "B.Eng. Civil Engineering")]),
    ("Faculty of Management Sciences", "MGT", [("Accounting", "ACC", "B.Sc. Accounting"), ("Business Administration", "BUS", "B.Sc. Business Administration")]),
    ("Faculty of Arts", "ART", [("English", "ENS", "B.A. English"), ("History", "HIS", "B.A. History")]),
]


class Command(BaseCommand):
    help = "Create clearly labelled sample academic records and train the decision tree."

    def handle(self, *args, **options):
        ensure_default_settings()
        with transaction.atomic():
            self._clear_sample_data()
            sessions = self._sessions()
            departments = self._structure()
            admin = self._admin()
            lecturers = self._lecturers(departments)
            courses = self._courses(departments, sessions, lecturers)
            students = self._students(departments, sessions["current"])
            historical, current = self._enrolments(students, courses, sessions)
            self._attendance_and_scores(students, historical, current)
        model = train_model(sample=True)
        self.stdout.write(self.style.SUCCESS("Sample data created."))
        self.stdout.write("Institution: Nexus State University (sample)")
        self.stdout.write(f"Administrator: sample.admin@nexusstate.edu.ng / {SAMPLE_PASSWORD}")
        self.stdout.write(f"Lecturer example: sample.lecturer01@nexusstate.edu.ng / {SAMPLE_PASSWORD}")
        self.stdout.write(f"Student example: sample.student001@nexusstate.edu.ng / {SAMPLE_PASSWORD}")
        self.stdout.write("Students can also sign in with a sample matriculation number such as NSU/SAMPLE/2026/001.")
        self.stdout.write(
            f"Model {model.version}: accuracy {model.accuracy:.2%}, precision {model.precision:.2%}, "
            f"recall {model.recall:.2%}, F1 {model.f1_score:.2%}."
        )
        self.stdout.write(f"Sample administrator id {admin.id}; sample records are marked is_sample=true.")

    def _clear_sample_data(self):
        Prediction.objects.filter(is_sample=True).delete()
        Notification.objects.filter(recipient__is_sample=True).delete()
        Attendance.objects.filter(is_sample=True).delete()
        Result.objects.filter(is_sample=True).delete()
        Assessment.objects.filter(is_sample=True).delete()
        Enrolment.objects.filter(is_sample=True).delete()
        CourseAssignment.objects.filter(is_sample=True).delete()
        Course.objects.filter(is_sample=True).delete()
        Student.objects.filter(is_sample=True).delete()
        Lecturer.objects.filter(is_sample=True).delete()
        Semester.objects.filter(is_sample=True).delete()
        AcademicSession.objects.filter(is_sample=True).delete()
        Department.objects.filter(is_sample=True).delete()
        Faculty.objects.filter(is_sample=True).delete()
        ModelVersion.objects.filter(is_sample=True).delete()
        User.objects.filter(is_sample=True).delete()

    def _sessions(self):
        historical = AcademicSession.objects.create(
            name="2025/2026", start_date="2025-09-15", end_date="2026-07-31", is_current=False, is_sample=True
        )
        current = AcademicSession.objects.create(
            name="2026/2027", start_date="2026-09-14", end_date="2027-07-30", is_current=True, is_sample=True
        )
        historical_semester = Semester.objects.create(session=historical, name=Semester.Name.SECOND, is_current=False, is_sample=True)
        current_semester = Semester.objects.create(session=current, name=Semester.Name.FIRST, is_current=True, is_sample=True)
        return {
            "historical": historical,
            "current": current,
            "historical_semester": historical_semester,
            "current_semester": current_semester,
        }

    def _structure(self):
        departments = []
        for faculty_name, faculty_code, department_rows in FACULTIES:
            faculty = Faculty.objects.create(name=faculty_name, code=faculty_code, description="Sample faculty.", is_sample=True)
            for name, code, programme in department_rows:
                department = Department.objects.create(faculty=faculty, name=name, code=code, is_sample=True)
                department.programme = programme
                departments.append(department)
        return departments

    def _user(self, email, username, first_name, surname, role, staff=False):
        return User.objects.create_user(
            email=email,
            username=username,
            password=SAMPLE_PASSWORD,
            first_name=first_name,
            last_name=surname,
            role=role,
            is_staff=staff,
            is_superuser=staff,
            is_sample=True,
        )

    def _admin(self):
        return self._user("sample.admin@nexusstate.edu.ng", "sample.admin", "Sample", "Administrator", User.Role.ADMIN, staff=True)

    def _lecturers(self, departments):
        lecturers = {}
        for index, department in enumerate(departments, start=1):
            first_name = FIRST_NAMES[index]
            surname = SURNAMES[index]
            email = f"sample.lecturer{index:02d}@nexusstate.edu.ng"
            user = self._user(email, f"NSU-STAFF-{index:03d}", first_name, surname, User.Role.LECTURER)
            lecturer = Lecturer.objects.create(
                user=user,
                staff_id=f"NSU-STAFF-{index:03d}",
                first_name=first_name,
                surname=surname,
                email=email,
                telephone=f"080200000{index:02d}",
                faculty=department.faculty,
                department=department,
                employment_status=Lecturer.EmploymentStatus.ACTIVE,
                is_sample=True,
            )
            lecturers[department.id] = lecturer
        return lecturers

    def _courses(self, departments, sessions, lecturers):
        catalogue = {"historical": {}, "current": {}}
        titles = ["Introduction", "Methods", "Practice", "Seminar"]
        for department in departments:
            for level in (100, 200, 300, 400):
                for slot, title in enumerate(titles, start=1):
                    code = f"{department.code}{level // 100}0{slot}"
                    for key, session, semester in (
                        ("historical", sessions["historical"], sessions["historical_semester"]),
                        ("current", sessions["current"], sessions["current_semester"]),
                    ):
                        course = Course.objects.create(
                            code=code,
                            title=f"{title} to {department.name}",
                            credit_units=3 if slot < 4 else 2,
                            faculty=department.faculty,
                            department=department,
                            level=level,
                            academic_session=session,
                            semester=semester,
                            status=Course.Status.ACTIVE,
                            is_sample=True,
                        )
                        CourseAssignment.objects.create(
                            course=course, lecturer=lecturers[department.id], is_primary=True, is_sample=True
                        )
                        catalogue[key].setdefault((department.id, level), []).append(course)
        return catalogue

    def _students(self, departments, current_session):
        students = []
        for index in range(120):
            department = departments[index % len(departments)]
            level = [100, 200, 300, 400][(index // len(departments)) % 4]
            band = BANDS[index]
            first_name = FIRST_NAMES[index % len(FIRST_NAMES)]
            surname = SURNAMES[index % len(SURNAMES)]
            matric = f"NSU/SAMPLE/{2027 - (level // 100)}/{index + 1:03d}"
            email = f"sample.student{index + 1:03d}@nexusstate.edu.ng"
            user = self._user(email, matric.replace("/", "-"), first_name, surname, User.Role.STUDENT)
            student = Student.objects.create(
                user=user,
                matric_number=matric,
                first_name=first_name,
                surname=surname,
                email=email,
                telephone=f"0803{index + 1:07d}",
                gender=Student.Gender.FEMALE if index % 2 else Student.Gender.MALE,
                date_of_birth=f"{2004 + (index % 5)}-{(index % 12) + 1:02d}-15",
                faculty=department.faculty,
                department=department,
                programme=department.programme,
                level=level,
                admission_year=2027 - (level // 100),
                current_session=current_session,
                prior_cgpa=PRIOR_CGPA[band],
                status=Student.Status.ACTIVE,
                is_sample=True,
            )
            student.band = band
            students.append(student)
        return students

    def _enrolments(self, students, courses, sessions):
        historical_rows = []
        current_rows = []
        for student in students:
            for key, bucket, session, semester in (
                ("historical", historical_rows, sessions["historical"], sessions["historical_semester"]),
                ("current", current_rows, sessions["current"], sessions["current_semester"]),
            ):
                for course in courses[key][(student.department_id, student.level)]:
                    bucket.append(
                        Enrolment(
                            student=student,
                            course=course,
                            session=session,
                            semester=semester,
                            status=Enrolment.Status.ENROLLED,
                            is_sample=True,
                        )
                    )
        Enrolment.objects.bulk_create(historical_rows, batch_size=500)
        Enrolment.objects.bulk_create(current_rows, batch_size=500)
        historical = list(Enrolment.objects.filter(is_sample=True, session=sessions["historical"]).select_related("student", "course"))
        current = list(Enrolment.objects.filter(is_sample=True, session=sessions["current"]).select_related("student", "course"))
        return historical, current

    def _attendance_and_scores(self, students, historical, current):
        bands = {student.id: student.band for student in students}
        rng = np.random.default_rng(42)
        attendance_rows = []
        assessments = []
        for enrolment in historical:
            band = bands[enrolment.student_id]
            rate = ATTENDANCE_RATE[band]
            for offset in range(6):
                roll = rng.random()
                if roll < rate:
                    status = Attendance.Status.PRESENT
                elif roll < rate + 0.05:
                    status = Attendance.Status.EXCUSED
                else:
                    status = Attendance.Status.ABSENT
                attendance_rows.append(
                    Attendance(enrolment=enrolment, date=f"2026-02-{10 + offset:02d}", status=status, is_sample=True)
                )
            ca_score, exam_score = SCORE_PLAN[band]
            assessments.append(
                Assessment(
                    enrolment=enrolment,
                    ca_score=quantize_score(ca_score),
                    exam_score=quantize_score(exam_score),
                    is_sample=True,
                )
            )
        Assessment.objects.bulk_create(assessments, batch_size=500)
        saved = {item.enrolment_id: item for item in Assessment.objects.filter(enrolment__in=historical, is_sample=True)}
        results = []
        for enrolment in historical:
            assessment = saved[enrolment.id]
            total = float(assessment.ca_score) + float(assessment.exam_score)
            grade, point, remark = assign_grade(total)
            results.append(
                Result(
                    enrolment=enrolment,
                    assessment=assessment,
                    total_score=quantize_score(total),
                    grade=grade,
                    grade_point=point,
                    remark=remark,
                    is_validated=True,
                    is_sample=True,
                )
            )
        Result.objects.bulk_create(results, batch_size=500)
        current_attendance = []
        current_assessments = []
        for enrolment in current:
            band = bands[enrolment.student_id]
            rate = ATTENDANCE_RATE[band]
            for offset in range(4):
                status = Attendance.Status.PRESENT if rng.random() < rate else Attendance.Status.ABSENT
                current_attendance.append(
                    Attendance(enrolment=enrolment, date=f"2026-09-{16 + offset:02d}", status=status, is_sample=True)
                )
            current_assessments.append(
                Assessment(
                    enrolment=enrolment,
                    ca_score=quantize_score(SCORE_PLAN[band][0]),
                    exam_score=None,
                    is_sample=True,
                )
            )
        Attendance.objects.bulk_create(attendance_rows + current_attendance, batch_size=1000)
        Assessment.objects.bulk_create(current_assessments, batch_size=500)
        for student in students:
            update_student_cgpa(student)
        self.stdout.write(f"Prepared {len(results)} historical results at {timezone.now():%H:%M:%S}.")
