from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    Author,
    Genre,
    Publisher,
    Book,
    BookCopy,
    Loan,
)


class LibraryApiTests(APITestCase):
    """End-to-end API tests covering permissions, validations, and core flows."""

    def setUp(self) -> None:
        User = get_user_model()
        self.staff_user = User.objects.create_user(
            username="staff", email="staff@example.com", password="Password123!", is_staff=True
        )
        self.member_user = User.objects.create_user(
            username="member", email="member@example.com", password="Password123!", is_staff=False
        )

        self.author = Author.objects.create(name="Isaac Asimov")
        self.genre = Genre.objects.create(name="Science Fiction")
        self.publisher = Publisher.objects.create(name="Penguin")

        self.book = Book.objects.create(
            title="Foundation",
            genre=self.genre,
            publisher=self.publisher,
            publication_date=timezone.now().date(),
            isbn="1234567890123",
            pages=255,
            language="English",
        )
        self.book.authors.add(self.author)

        self.available_copy = BookCopy.objects.create(
            book=self.book,
            copy_id="COPY-001",
            acquisition_date=timezone.now().date(),
            status="available",
            condition_rating=5,
        )

    # Helpers
    def _results(self, response):
        """Return list payload accounting for DRF pagination."""
        data = response.data
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        return data

    # ----------------------------
    # Author endpoints
    # ----------------------------
    def test_author_list_requires_authentication(self):
        url = reverse("author-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_author_read_allowed_for_authenticated_non_staff(self):
        self.client.force_authenticate(self.member_user)
        url = reverse("author-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_author_create_denied_for_non_staff_allowed_for_staff(self):
        url = reverse("author-list")

        # Non-staff cannot create
        self.client.force_authenticate(self.member_user)
        response = self.client.post(url, {"name": "Arthur C. Clarke"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Staff can create
        self.client.force_authenticate(self.staff_user)
        response = self.client.post(url, {"name": "Arthur C. Clarke"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # ----------------------------
    # Book validations and search
    # ----------------------------
    def test_book_invalid_isbn_and_future_publication_date(self):
        self.client.force_authenticate(self.staff_user)
        url = reverse("book-list")
        future_date = (timezone.now().date() + timedelta(days=10)).isoformat()
        payload = {
            "title": "Invalid Book",
            "authors": [self.author.id],
            "genre": self.genre.id,
            "publisher": self.publisher.id,
            "publication_date": future_date,
            "isbn": "12345",  # invalid
            "pages": 100,
            "language": "English",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("isbn", response.data)
        self.assertIn("publication_date", response.data)

    def test_book_search_by_author_title_and_isbn(self):
        self.client.force_authenticate(self.member_user)
        url = reverse("book-list") + "?search=asimov"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [item["title"] for item in self._results(response)]
        self.assertIn("Foundation", titles)

    # ----------------------------
    # BookCopy permissions and filters
    # ----------------------------
    def test_bookcopy_endpoints_staff_only(self):
        list_url = reverse("bookcopy-list")

        # Non-staff cannot access even list
        self.client.force_authenticate(self.member_user)
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Staff can access
        self.client.force_authenticate(self.staff_user)
        response = self.client.get(list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_bookcopy_filtering(self):
        self.client.force_authenticate(self.staff_user)
        url = reverse("bookcopy-list") + f"?book={self.book.id}&status=available&min_condition=4"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(self._results(response)), 1)

    # ----------------------------
    # Member endpoints
    # ----------------------------
    def test_member_me_endpoint_returns_current_user(self):
        self.client.force_authenticate(self.member_user)
        url = reverse("member-me")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], self.member_user.username)

    def test_member_list_visibility(self):
        # Non-staff should only see themselves
        self.client.force_authenticate(self.member_user)
        response = self.client.get(reverse("member-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("count", 1), 1)
        results = self._results(response)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["username"], self.member_user.username)

        # Staff sees all
        self.client.force_authenticate(self.staff_user)
        response = self.client.get(reverse("member-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self._results(response)
        usernames = {u["username"] for u in results}
        self.assertTrue({"member", "staff"}.issubset(usernames))

    # ----------------------------
    # Loan rules
    # ----------------------------
    def test_loan_create_requires_staff(self):
        self.client.force_authenticate(self.member_user)
        url = reverse("loan-list")
        payload = {
            "book_copy": self.available_copy.id,
            "member": self.member_user.id,
            "loan_date": timezone.now().date().isoformat(),
            "due_date": (timezone.now().date() + timedelta(days=7)).isoformat(),
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_loan_creation_and_business_rules(self):
        # Staff can create a valid loan when copy is available
        self.client.force_authenticate(self.staff_user)
        url = reverse("loan-list")

        valid_payload = {
            "book_copy": self.available_copy.id,
            "member": self.member_user.id,
            "loan_date": timezone.now().date().isoformat(),
            "due_date": (timezone.now().date() + timedelta(days=14)).isoformat(),
            "fine_amount": "0.00",
        }
        response = self.client.post(url, valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Mark copy not available and verify validation error
        self.available_copy.status = "on_loan"
        self.available_copy.save()

        invalid_copy_payload = {
            "book_copy": self.available_copy.id,
            "member": self.member_user.id,
            "loan_date": timezone.now().date().isoformat(),
            "due_date": (timezone.now().date() + timedelta(days=7)).isoformat(),
        }
        response = self.client.post(url, invalid_copy_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("book_copy", response.data)

    def test_loan_limit_per_member(self):
        self.client.force_authenticate(self.staff_user)
        # Create 5 active loans for the member
        for i in range(5):
            copy = BookCopy.objects.create(
                book=self.book,
                copy_id=f"COPY-LIMIT-{i}",
                acquisition_date=timezone.now().date(),
                status="available",
                condition_rating=5,
            )
            Loan.objects.create(
                book_copy=copy,
                member=self.member_user,
                loan_date=timezone.now().date(),
                due_date=timezone.now().date() + timedelta(days=7),
            )

        # Sixth loan should fail validation
        sixth_copy = BookCopy.objects.create(
            book=self.book,
            copy_id="COPY-LIMIT-5",
            acquisition_date=timezone.now().date(),
            status="available",
            condition_rating=5,
        )
        url = reverse("loan-list")
        payload = {
            "book_copy": sixth_copy.id,
            "member": self.member_user.id,
            "loan_date": timezone.now().date().isoformat(),
            "due_date": (timezone.now().date() + timedelta(days=7)).isoformat(),
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("member", response.data)
