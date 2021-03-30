from django.urls import path
from rest_framework import routers, serializers, viewsets
from django.urls import include
from django.views.generic import TemplateView

from . import views, serializers
from .serializers import ALL_PATH_VIEWSET as WEBAPP_PATH_VIEWSET
from .graphvis import ALL_PATH_VIEWSET as WEBAPP_GRAPHVIS_PATH_VIEWSET

# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()

for p,v in WEBAPP_PATH_VIEWSET.items():
    router.register(p,v)
for p,v in WEBAPP_GRAPHVIS_PATH_VIEWSET.items():
    router.register(p,v)

urlpatterns = [
    path('', views.index, name='index'),
    path('graphvis/', views.graphvis, name='graphvis'),
    path('accounts/profile/', views.user_profile, name='user_profile'),
    path('update/', views.update, name='update'),
    path('scrape_arxiv_vanity/', views.scapeArxivVanity, name='scrape_arxiv_vanity'),
    # path('scrape_pdf/', views.scapePDF, name='scrape_pdf'),
    path('api/', include(router.urls)),
    path('api/user_preference/', serializers.user_preference, name='user_preference'),
    path('api/user_paper/', serializers.user_paper, name='user_paper'),
    path('api/user_tags/', serializers.user_tags, name='user_tags'),
]