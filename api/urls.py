from django.urls import path

from .views import Home, UserRegistrationView, UserLoginView, AccountListCreateView, AccountRetrieveDestroyView, \
    FecebookedirectUrlView, FacebookOauth2Login, UserDataView, CreateInstagramPost, CaptionImage, GenerateDescriptionForImage

urlpatterns = [
    path('', Home.as_view(), name='default-view'),
    path('/register', UserRegistrationView.as_view(),name='user-registration'),
    path('/login', UserLoginView.as_view(),name='user-login'),
    path('/accounts', AccountListCreateView.as_view(), name='account-list-create'),
    path('/accounts/<int:pk>', AccountRetrieveDestroyView.as_view(), name='account-retrieve-destroy'),
    path('/login/oauth2/facebook', FacebookOauth2Login.as_view(), name='login-oauth'),
    path('/login/oauth2/facebook/redirect', FecebookedirectUrlView.as_view(), name='redirect-oauth-url'),
    path('/user/<int:id>', UserDataView.as_view(), name='user-data-view'),
    path('/posts/create', CreateInstagramPost.as_view(), name='create-instagram-post' ),
    path('/posts/caption', CaptionImage.as_view(), name='caption-image'),
    path('/posts/description', GenerateDescriptionForImage.as_view(), name="post-description")
]