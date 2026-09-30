from rest_framework.permissions import BasePermission


def _role(user):
    return getattr(user, "role", None)


class IsAdministrator(BasePermission):
    message = "Only an administrator can perform this action."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and _role(request.user) == "admin")


class IsLecturer(BasePermission):
    message = "Only a lecturer can perform this action."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and _role(request.user) == "lecturer")


class IsStudent(BasePermission):
    message = "Only a student can perform this action."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and _role(request.user) == "student")


class IsAdminOrLecturer(BasePermission):
    message = "Only an administrator or lecturer can perform this action."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and _role(request.user) in {"admin", "lecturer"})


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and _role(request.user) == "admin")
