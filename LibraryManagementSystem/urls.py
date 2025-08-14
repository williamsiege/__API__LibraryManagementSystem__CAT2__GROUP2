# urls.py
from django.urls import include, path
from rest_framework import routers
from LibraryManagementSystem import views

router = routers.DefaultRouter()
router.register(r'authors', views.AuthorViewSet, basename='author')
router.register(r'genres', views.GenreViewSet, basename='genre')
router.register(r'publishers', views.PublisherViewSet, basename='publisher')
router.register(r'books', views.BookViewSet, basename='book')
router.register(r'copies', views.BookCopyViewSet, basename='bookcopy')
router.register(r'members', views.MemberViewSet, basename='member')
router.register(r'loans', views.LoanViewSet, basename='loan')

urlpatterns = [
    path('', include(router.urls)),

]