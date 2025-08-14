# serializers.py
from rest_framework import serializers
from .models import Author, Genre, Publisher, Book, BookCopy, Member, Loan
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = '__all__'

    def validate_name(self, value):
        if len(value) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters long")
        return value

    def validate_birth_date(self, value):
        if value and value > timezone.now().date():
            raise serializers.ValidationError("Birth date cannot be in the future")
        return value


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = '__all__'

    def validate_name(self, value):
        if not value.replace(' ', '').isalnum():
            raise serializers.ValidationError("Genre name can only contain letters, numbers and spaces")
        return value


class PublisherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publisher
        fields = '__all__'

    def validate_website(self, value):
        if value and not value.startswith('http'):
            raise serializers.ValidationError("Website must be a valid URL starting with http/https")
        return value


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'
        extra_kwargs = {
            'isbn': {'validators': []}  # Disable automatic unique validation for updates
        }

    def validate_isbn(self, value):
        if not value.isdigit() or len(value) not in [10, 13]:
            raise serializers.ValidationError("ISBN must be 10 or 13 digits")
        return value

    def validate_publication_date(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError("Publication date cannot be in the future")
        return value

    def validate_pages(self, value):
        if value < 1:
            raise serializers.ValidationError("Book must have at least 1 page")
        return value

    def create(self, validated_data):
        # Handle ISBN uniqueness during creation
        isbn = validated_data.get('isbn')
        if Book.objects.filter(isbn=isbn).exists():
            raise serializers.ValidationError({"isbn": "This ISBN already exists"})
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Handle ISBN uniqueness during updates
        isbn = validated_data.get('isbn', instance.isbn)
        if isbn != instance.isbn and Book.objects.filter(isbn=isbn).exists():
            raise serializers.ValidationError({"isbn": "This ISBN already exists"})
        return super().update(instance, validated_data)


class BookCopySerializer(serializers.ModelSerializer):
    class Meta:
        model = BookCopy
        fields = '__all__'
        extra_kwargs = {
            'copy_id': {'validators': []}  # Disable automatic unique validation
        }

    def validate_acquisition_date(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError("Acquisition date cannot be in the future")
        return value

    def validate_condition_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Condition rating must be between 1-5")
        return value

    def validate(self, data):
        # Check copy_id uniqueness per book
        copy_id = data.get('copy_id', self.instance.copy_id if self.instance else None)
        book = data.get('book', self.instance.book if self.instance else None)

        if book and copy_id:
            queryset = BookCopy.objects.filter(book=book, copy_id=copy_id)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError(
                    {"copy_id": "This copy ID already exists for the selected book"}
                )
        return data


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = '__all__'
        extra_kwargs = {
            'email': {'validators': []}  # Disable automatic unique validation
        }

    def validate_email(self, value):
        if not '@' in value or '.' not in value.split('@')[-1]:
            raise serializers.ValidationError("Enter a valid email address")
        return value

    def validate_join_date(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError("Join date cannot be in the future")
        return value

    def validate(self, data):
        # Handle email uniqueness
        email = data.get('email')
        if self.instance and email != self.instance.email:
            if Member.objects.filter(email=email).exists():
                raise serializers.ValidationError({"email": "This email is already registered"})
        elif not self.instance and email:
            if Member.objects.filter(email=email).exists():
                raise serializers.ValidationError({"email": "This email is already registered"})
        return data


class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = '__all__'

    def validate_loan_date(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError("Loan date cannot be in the future")
        return value

    def validate_due_date(self, value):
        loan_date = self.initial_data.get('loan_date')
        if loan_date:
            if value < timezone.datetime.strptime(loan_date, '%Y-%m-%d').date():
                raise serializers.ValidationError("Due date must be after loan date")
        return value

    def validate_return_date(self, value):
        if value and value > timezone.now().date():
            raise serializers.ValidationError("Return date cannot be in the future")
        return value

    def validate(self, data):
        # Check book copy availability
        book_copy = data.get('book_copy') or (self.instance.book_copy if self.instance else None)
        if book_copy and book_copy.status != 'available' and not self.instance:
            raise serializers.ValidationError(
                {"book_copy": "This copy is not available for loan"}
            )

        # Check active loans limit for member
        member = data.get('member') or (self.instance.member if self.instance else None)
        if member:
            active_loans = Loan.objects.filter(
                member=member,
                return_date__isnull=True
            ).count()
            max_loans = 5  # Business rule: max 5 active loans per member

            if active_loans >= max_loans and not self.instance:
                raise serializers.ValidationError(
                    {"member": f"Member has reached the maximum of {max_loans} active loans"}
                )

        return data