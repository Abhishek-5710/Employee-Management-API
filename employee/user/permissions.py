from rest_framework import permissions


class IsHR(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name="HR").exists()


class IsHROrManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name__in=["HR", "Manager"]).exists()


class IsSelfOrHR(permissions.BasePermission):
    """Employee apna khud ka data edit kar sake, ya HR kisi ka bhi"""
    def has_object_permission(self, request, view, obj):
        if request.user.groups.filter(name="HR").exists():
            return True
        return obj.id == request.user.id