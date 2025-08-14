from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import AbstractUser

class Author(models.Model):
    name = models.CharField(max_length=200, unique=True)
    birth_date = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Publisher(models.Model):
    name = models.CharField(max_length=200, unique=True)
    address = models.TextField(blank=True)
    website = models.URLField(blank=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=200)
    authors = models.ManyToManyField(Author, related_name='books')
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True)
    publisher = models.ForeignKey(Publisher, on_delete=models.SET_NULL, null=True)
    publication_date = models.DateField()
    isbn = models.CharField(max_length=13, unique=True)
    pages = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    language = models.CharField(max_length=50, default='English')

    def __str__(self):
        return f"{self.title} ({self.isbn})"


class BookCopy(models.Model):
    COPY_STATUS = [
        ('available', 'Available'),
        ('on_loan', 'On Loan'),
        ('maintenance', 'Under Maintenance'),
        ('lost', 'Lost'),
    ]

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='copies')
    copy_id = models.CharField(max_length=20, unique=True)
    acquisition_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=COPY_STATUS, default='available')
    condition_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )

    def __str__(self):
        return f"Copy {self.copy_id} of {self.book.title}"

class Member(AbstractUser):
    MEMBERSHIP_TYPES = [
        ('standard', 'Standard'),
        ('premium', 'Premium'),
        ('student', 'Student'),
    ]
    membership_type = models.CharField(max_length=20, choices=MEMBERSHIP_TYPES, default='standard')
    join_date = models.DateField(default=timezone.now)
    phone = models.CharField(max_length=15, blank=True)
    # Add related_name to avoid clashes
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        related_name='library_members',
        related_query_name='member'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        related_name='library_members',
        related_query_name='member'
    )

    def __str__(self):
        return self.username


class Loan(models.Model):
    book_copy = models.ForeignKey(BookCopy, on_delete=models.PROTECT, related_name='loans')
    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name='loans')
    loan_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    return_date = models.DateField(null=True, blank=True)
    fine_amount = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Loan #{self.id} - {self.member} ({self.book_copy})"
