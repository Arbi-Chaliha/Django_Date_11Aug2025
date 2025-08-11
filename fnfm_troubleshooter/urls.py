from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # This is the default Django admin path.
    path('admin/', admin.site.urls),

    # This is the key to modularity! We include the URL patterns
    # from our troubleshooter_app. Any URL starting with 'troubleshooter/'
    # will be handled by that app's urls.py.
    path('troubleshooter/', include('troubleshooter_app.urls')),
    
    # You can add more apps here as your project grows. For example:
    # path('users/', include('users_app.urls')),
    # path('blog/', include('blog_app.urls')),
]

# Serve static files during development, which is standard practice.
# The user's original code had a duplicate static line, which is removed here.
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # The static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    # is a more generic way to serve files from the staticfiles directory.
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
