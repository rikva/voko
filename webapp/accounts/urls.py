from django.conf.urls import patterns, url
from .views import LoginView, RegisterView, PasswordResetView, EmailConfirmView, FinishRegistration, RegisterThanksView, \
    WelcomeView, OverView

urlpatterns = patterns('',
    url(r'^login/$', LoginView.as_view(), name="login"),
    url(r'^register/$', RegisterView.as_view(), name="register"),
    url(r'^register/thanks/$', RegisterThanksView.as_view(), name="register_thanks"),
    url(r'^register/confirm/(?P<pk>[0-9a-zA-Z\-]+)$', EmailConfirmView.as_view(), name="confirm_email"),
    url(r'^register/finish/(?P<pk>[0-9a-zA-Z\-]+)$', FinishRegistration.as_view(), name="finish_registration"),
    url(r'^passwordreset/$', PasswordResetView.as_view()),
    url(r'^welcome/$', WelcomeView.as_view()),
    url(r'^overview/$', OverView.as_view(), name='overview'),
)