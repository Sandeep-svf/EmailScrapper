from django.contrib import admin
from django.urls import path

from . import views
from .views import home




from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', home, name='home'),
    path('scrape/', views.start_scraping, name='start_scraping'),
    path('batch/<str:batch_name>/', views.batch_detail, name='batch_detail'),
    path('batch/<str:batch_name>/download/', views.download_batch_csv, name='download_batch_csv'),
    path('progress/', views.scraping_progress, name='scraping_progress'),



    path('admin/', admin.site.urls),

]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
