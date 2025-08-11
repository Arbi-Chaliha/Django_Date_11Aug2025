from django.urls import path, include
from . import views

# A clear namespace for the app's URLs is a great practice.
app_name = 'troubleshooter_app'

urlpatterns = [
    # The main troubleshooter page.
    path('', views.troubleshooter_view, name='troubleshooter'),
    
    # New API endpoint to get choices for the dynamic dropdowns.
    path('api/get_choices/', views.get_form_choices, name='get_form_choices'),
    
    # New API endpoint for fetching the troubleshooter data.
    path('api/troubleshooter_data/', views.get_troubleshooter_data, name='get_troubleshooter_data'),

    # This is the new modular API inclusion.
    # All Teradata API endpoints will be under the 'troubleshooter/api/' path.
    path('api/', include('troubleshooter_app.api_urls')),
]
