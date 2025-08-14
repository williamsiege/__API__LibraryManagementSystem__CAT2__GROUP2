from django.shortcuts import render
# views.py
from rest_framework import viewsets, permissions
from .models import Author, Genre, Publisher, Book, BookCopy, Member, Loan
from .serializers import (
    AuthorSerializer, GenreSerializer, PublisherSerializer,
    BookSerializer, BookCopySerializer, MemberSerializer, LoanSerializer
)
from django.db.models import Q

# Permission Classes

class IsStaffOrReadOnly(permissions.BasePermission):
    """Allow staff full access, others read-only"""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


class IsStaff(permissions.BasePermission):
    """Require staff status for all operations"""

    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class IsSelfOrStaff(permissions.BasePermission):
    """Allow users to access their own data, staff full access"""

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True

        # Check for Member objects
        if isinstance(obj, Member):
            return obj.email == request.user.email

        # Check for Loan objects
        if isinstance(obj, Loan):
            return obj.member.email == request.user.email

        return False



# ViewSets

class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrReadOnly]

    def get_queryset(self):
        """Enable search by author name"""
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)
        if search:
            return queryset.filter(name__icontains=search)
        return queryset


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

    def get_queryset(self):
        """Enable search by title, author, or ISBN"""
        queryset = super().get_queryset()
        search = self.request.query_params.get('search', None)

        if search:
            return queryset.filter(
                Q(title__icontains=search) |
                Q(authors__name__icontains=search) |
                Q(isbn__icontains=search)
            ).distinct()
        return queryset


class BookCopyViewSet(viewsets.ModelViewSet):
    queryset = BookCopy.objects.all()
    serializer_class = BookCopySerializer
    permission_classes = [permissions.IsAuthenticated, IsStaff]

    def get_queryset(self):
        """Enable filtering by book, status, or condition"""
        queryset = super().get_queryset()
        book_id = self.request.query_params.get('book', None)
        status = self.request.query_params.get('status', None)
        min_condition = self.request.query_params.get('min_condition', None)

        if book_id:
            queryset = queryset.filter(book__id=book_id)
        if status:
            queryset = queryset.filter(status=status)
        if min_condition:
            queryset = queryset.filter(condition_rating__gte=min_condition)

        return queryset


class MemberViewSet(viewsets.ModelViewSet):
    serializer_class = MemberSerializer
    permission_classes = [permissions.IsAuthenticated, IsSelfOrStaff]

    def get_queryset(self):
        """Staff see all members, users see only themselves"""
        if self.request.user.is_staff:
            return Member.objects.all()
        return Member.objects.filter(email=self.request.user.email)


class LoanViewSet(viewsets.ModelViewSet):
    serializer_class = LoanSerializer
    permission_classes = [permissions.IsAuthenticated, IsSelfOrStaff]

    def get_queryset(self):
        """Staff see all loans, users see only their own"""
        queryset = Loan.objects.select_related('member', 'book_copy', 'book_copy__book')

        if self.request.user.is_staff:
            return queryset

        # For non-staff, return only user's loans
        return queryset.filter(member__email=self.request.user.email)

    def get_permissions(self):
        """Require staff status for loan creation and updates"""
        if self.action in ['create', 'update', 'partial_update']:
            return [permissions.IsAuthenticated(), IsStaff()]
        return super().get_permissions()
