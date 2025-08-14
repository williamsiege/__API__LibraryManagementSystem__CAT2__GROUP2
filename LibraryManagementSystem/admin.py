# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Author, Genre, Publisher, Book, BookCopy, Member, Loan

class CustomUserAdmin(UserAdmin):
    model = Member
    list_display = ('username', 'email', 'membership_type', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Library Details', {'fields': ('membership_type', 'phone')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Library Details', {'fields': ('membership_type', 'phone')}),
    )

admin.site.register(Member, CustomUserAdmin)
admin.site.register(Author)
admin.site.register(Genre)
admin.site.register(Publisher)
admin.site.register(Book)
admin.site.register(BookCopy)
admin.site.register(Loan)
