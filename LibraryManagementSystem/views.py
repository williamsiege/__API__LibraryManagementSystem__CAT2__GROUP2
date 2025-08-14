# views.py
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Author, Genre, Publisher, Book, BookCopy, Member, Loan
from .serializers import (
    AuthorSerializer, GenreSerializer, PublisherSerializer,
    BookSerializer, BookCopySerializer, MemberSerializer, LoanSerializer
)
# Permission Classes
# =====================
class IsStaffOrReadOnly(permissions.BasePermission):
    """Allow staff full access, others read-only"""

    def has_permission(self, request, view):
        return bool(
            request.method in permissions.SAFE_METHODS or
            request.user and request.user.is_staff
        )


class IsStaff(permissions.BasePermission):
    """Require staff status for all operations"""

    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class IsSelfOrStaff(permissions.BasePermission):
    """Allow users to access their own data, staff full access"""

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj == request.user


# =====================
# ViewSets
# =====================
class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrReadOnly]

    # ... (search implementation remains the same) ...


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrReadOnly]


class PublisherViewSet(viewsets.ModelViewSet):
    queryset = Publisher.objects.all()
    serializer_class = PublisherSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrReadOnly]


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrReadOnly]

    # ... (search implementation remains the same) ...


class BookCopyViewSet(viewsets.ModelViewSet):
    queryset = BookCopy.objects.all()
    serializer_class = BookCopySerializer
    permission_classes = [permissions.IsAuthenticated, IsStaff]

    # ... (filter implementation remains the same) ...


class MemberViewSet(viewsets.ModelViewSet):
    serializer_class = MemberSerializer
    permission_classes = [permissions.IsAuthenticated, IsSelfOrStaff]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Member.objects.all()
        return Member.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class LoanViewSet(viewsets.ModelViewSet):
    serializer_class = LoanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Loan.objects.select_related('member', 'book_copy', 'book_copy__book')

        if self.request.user.is_staff:
            return queryset

        # For non-staff, return only user's loans
        return queryset.filter(member=self.request.user)

    def get_permissions(self):
        """Require staff status for loan creation and updates"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsStaff()]
        return super().get_permissions()