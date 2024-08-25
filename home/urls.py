from django.urls import path
from .views import manage_tips, toggle_reaction, get_tips
from django.contrib.staticfiles.storage import staticfiles_storage
from django.views.generic.base import RedirectView

urlpatterns = [
    path('', manage_tips, name='manage_tips'),
    path('toggle_reaction/<str:tip_id>/<str:reaction_type>/', toggle_reaction, name='toggle_reaction'),
    path('get-tips/<str:section>/', get_tips, name='get_tips'),
    path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('images/favicon.ico')))
]