from django.apps import AppConfig



class LibrarymanagementsystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'LibraryManagementSystem'

    def ready(self):
        pass
        # Import signals here to ensure they are registered when the app is ready
        import LibraryManagementSystem.signals  # Adjust the import path as necessary
        # This ensures that the signals are connected when the app is loaded


