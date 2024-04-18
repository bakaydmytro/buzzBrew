from django.urls import path
from .views import Home, UserRegistrationView, UserLoginView, AccountListCreateView, AccountRetrieveDestroyView


urlpatterns = [
    path('', Home.as_view(), name='default-view'),
    path('/register', UserRegistrationView.as_view(),name='user-registration'),
    path('/login', UserLoginView.as_view(),name='user-login'),
    path('/accounts', AccountListCreateView.as_view(), name='account-list-create'),
    path('/accounts/<int:pk>', AccountRetrieveDestroyView.as_view(), name='account-retrieve-destroy'),
]