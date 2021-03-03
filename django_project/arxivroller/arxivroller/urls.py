"""arxivroller URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, reverse, reverse_lazy
from django.views.generic import TemplateView
from django.contrib.auth.models import User
from rest_framework import routers, serializers, viewsets
from django_registration.backends.one_step.views import RegistrationView
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import url
from django.views.generic import RedirectView

# Serializers define the API representation.
class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['url', 'username', 'email', 'is_staff']

# ViewSets define the view behavior.
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
# router.register(r'users', UserViewSet)

# from webapp.serializers import ALL_PATH_VIEWSET as WEBAPP_PATH_VIEWSET
# for p,v in WEBAPP_PATH_VIEWSET.items():
#     router.register(p,v)


urlpatterns = [
    path('', include('webapp.urls')),
    path('admin/', admin.site.urls),
    path('accounts/register/',
        RegistrationView.as_view(template_name='registration/register.html', success_url=reverse_lazy('user_profile')),
        name='user_register'),
    path(
        'accounts/change_password/',
        auth_views.PasswordChangeView.as_view(template_name='accounts/password_change_form.html', success_url=reverse_lazy('change_password_done')), 
        name='change_password'
    ),
    path(
        'accounts/change_password/done',
        auth_views.PasswordChangeView.as_view(template_name='accounts/password_change_done.html', success_url=reverse_lazy('change_password_done')), 
        name='change_password_done'
    ),
    path('accounts/', include('django_registration.backends.one_step.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path(
        'accounts/login_require/',
        auth_views.LoginView.as_view(template_name='registration/login_require.html'),
    ),
    # path('api/', include(router.urls)),
    path('api/auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^favicon\.ico$',RedirectView.as_view(url='/static/images/favicon.ico')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)