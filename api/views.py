import os

import jwt
import requests
import vertexai
from openai import OpenAI
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from dotenv import load_dotenv
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from vertexai.preview.vision_models import Image, ImageTextModel
from vertexai.language_models import TextGenerationModel

from .models import Account
from .models import User
from .serializers import AccountSerializer
from .serializers import UserRegistrationSerializer, UserLoginSerializer

load_dotenv()

client_id = os.getenv("FACEBOOK_APP_ID")
client_secret = os.getenv("FACEBOOK_APP_SECRET")
redirect_uri = os.getenv("FACEBOOK_APP_REDIRECT_URL")
config_id = os.getenv("FACEBOOK_APP_CONFIGURATION_ID")
oauth2_base_url = os.getenv("FACEBOOK_LOG_IN_API_BASE_URL")
graph_base_url = os.getenv("FACEBOOK_GRAPH_API_BASE_URL")
gcp_project_id = os.getenv("GOOGLE_PROJECT_ID")
openai_api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=openai_api_key)


vertexai.init(project=gcp_project_id, location="europe-west2")

imageModel = ImageTextModel.from_pretrained("imagetext@001")
textModel = TextGenerationModel.from_pretrained("text-bison@002")


class Home(APIView):
    def get(self, request):
        print(request.user.email)
        content = {"message": "Hello, World!"}
        return Response(content)


class UserRegistrationView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=UserRegistrationSerializer)
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            return Response(
                {"token": access_token, "user_id": user.id},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(request_body=UserLoginSerializer)
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data.get("email")
            password = serializer.validated_data.get("password")

            user = authenticate(request, username=email, password=password)

            if user is not None:
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                return Response(
                    {"token": access_token, "user_id": user.id},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FacebookOauth2Login(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.GET.get("userAccessToken")
        format_base_url = f"{oauth2_base_url}/dialog/oauth?client_id={client_id}&redirect_uri={redirect_uri}&config_id={config_id}&state={token}"
        print(f"Formated base url: \n{format_base_url}")
        return HttpResponseRedirect(format_base_url)


class AccountListCreateView(generics.ListCreateAPIView):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer


class AccountRetrieveDestroyView(generics.RetrieveDestroyAPIView):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer


class AccountListByUserView(generics.ListAPIView):
    serializer_class = AccountSerializer

    def get_queryset(self):
        user_id = self.kwargs["user_id"]
        return Account.objects.filter(user_id=user_id)


class FecebookedirectUrlView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        oauth_code = request.query_params.get("code", None)
        token = request.query_params.get("state", None)
        user_id = None
        try:
            decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = decoded_token.get("user_id")
        except Exception as e:
            print("Error parse user token", str(e))

        print("USER ID: " + str(user_id))
        print("OAUTH CODE: " + str(oauth_code))
        if oauth_code and user_id:
            try:
                access_token = getAccessToken(oauth_code)
                ig_id = getInstagramUserId(access_token)

                user = get_user_model().objects.get(id=user_id)
                user.access_token = access_token
                user.instagram_user_id = ig_id
                user.save()
            except Exception as e:
                print("Error to get user data", str(e))
        else:
            print("Code parameter is missing")
        if user_id:
            return redirect(f"http://localhost:3000/user/{user_id}")
        else:
            return redirect(f"http://localhost:3000/error")


def getAccessToken(code):
    print("Code:", code)
    access_token_url = getAccessTokenUrl(code)
    print("Access token url: " + access_token_url)
    try:
        response = requests.get(access_token_url)
        if response.status_code == 200:
            json_data = response.json()
            access_token = json_data.get("access_token")
            print("Access Token: " + access_token)
            return access_token
        else:
            print("Error to get Access Token")
    except Exception as e:
        print("Error to get Access Token", e)


def getAccessTokenUrl(code):
    return f"{graph_base_url}/oauth/access_token?client_id={client_id}&redirect_uri={redirect_uri}&client_secret={client_secret}&code={code}"


def getInstagramUserId(access_token):
    pageId = getFacebookPageId(access_token)
    ig_business_account_url = f"{graph_base_url}/{pageId}?fields=instagram_business_account&access_token={access_token}"
    print("Instagram User Id URL: " + ig_business_account_url)

    ig_business_account_response = requests.get(ig_business_account_url, None)
    if ig_business_account_response.status_code == 200:
        json_body = ig_business_account_response.json()
        ig_user_id = json_body.get("instagram_business_account", {}).get("id")
        print("Instagram business account id: " + ig_user_id)
        return ig_user_id
    else:
        print("Error to get instagram business data")


def getFacebookPageId(access_token):
    get_accounts_url = f"{graph_base_url}/me/accounts?access_token={access_token}"
    print("Accounts URL: " + get_accounts_url)
    accounts_response = requests.get(get_accounts_url, None)
    if accounts_response.status_code == 200:
        json_data = accounts_response.json()
        data = json_data.get("data", [])
        if data:
            page_id = data[0].get("id")
            print("Page id: " + page_id)
            return page_id
        else:
            print("No data found in accounts list")
    else:
        print("Error to get accounts data")
    return None


class UserDataView(APIView):
    def get(self, request, id):
        user = get_object_or_404(User, id=id)
        need_facebook_auth = (
            user.instagram_user_id is None
            or user.instagram_user_id == ""
            or user.access_token is None
            or user.access_token == ""
        )
        user_data = {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "needFacebookAuth": need_facebook_auth,
        }

        return Response(user_data, status=status.HTTP_200_OK)


class CreateInstagramPost(APIView):
    def post(self, request):
        data = request.data
        user = request.user
        instagram_media_response = createInstagramMediaContainer(data, user)
        if instagram_media_response.status_code == 200:
            json = instagram_media_response.json()
            media_container_id = json.get("id")
            publishMediaContainer(media_container_id, user)
        else:
            return Response(
                "Error to create instagram media record",
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response("Instagram post successfully created")


def createInstagramMediaContainer(request_data, user):
    instagram_media_url = f"{graph_base_url}/{user.instagram_user_id}/media"
    data = {
        "image_url": request_data.get("image_url"),
        "caption": request_data.get("description"),
        "access_token": user.access_token,
    }
    response = requests.post(instagram_media_url, data)
    print(f"Response from media: {response}")
    return response


def publishMediaContainer(container_id, user):
    publish_media_url = f"{graph_base_url}/{user.instagram_user_id}/media_publish"
    print(f"Publish media url: {publish_media_url}")
    data = {"creation_id": container_id, "access_token": user.access_token}
    print(f"Publishing media container with data: {data}")
    response = requests.post(publish_media_url, data)
    print(f"Response from publishing container:{response}")
    return response


class CaptionImage(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        image_url = request.GET.get("imageUrl")
        print(f"ImageURL: {image_url}")
        image_path = downloadImage(image_url)
        print("image path: " + image_path)
        source_img = Image.load_from_file(image_path)
        captions = ""
        try:
            captions = imageModel.get_captions(
                image=source_img, language="en", number_of_results=1
            )
        except Exception as e:
            print("Error occurs(", str(e))
        print("Caption: " + str(captions))
        data = {"caption": captions}
        return Response(data, status=status.HTTP_200_OK)


def downloadImage(image_url):
    upload_folder = os.path.join(settings.BASE_DIR, "upload")
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    try:
        response = requests.get(image_url, stream=True)
        response.raise_for_status()
    except requests.RequestException as e:
        print({"error": str(e)}, status=400)
    image_name = image_url.split("/")[-1]
    image_path = os.path.join(upload_folder, image_name)
    if os.path.exists(image_path):
        return image_path

    with open(image_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return image_path


class GenerateDescriptionForImage(APIView):
    def post(self, request):
        data = request.data
        prompt = (
            "Generate a description for an Instagram post using the following data:\n"
        )

        theme = data.get("theme")
        caption = data.get("caption")

        if theme:
            prompt += f"Post theme: {theme}\n"
        if caption:
            prompt += f"Image caption: {' '.join(caption)}"
        response = generateDescription(prompt)
        data = {"description": response}

        return Response(data, status=status.HTTP_200_OK)


def generateDescription(prompt):
    parameters = {
        "temperature": 1,
        "max_output_tokens": 256,
        "top_p": 0.8,
        "top_k": 40,
    }
    response = textModel.predict(
        prompt,
        **parameters,
    )
    print(f"Response from Model: {response.text}")
    return response.text


def generate_image(description):
    try:
        prompt = f"Generate image for instagram post based on image description: {description}"
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        return image_url

    except Exception as e:
        print(f"An error occurred: {e}")
        return None


class GenerateImageBasedOnDescription(APIView):
    def post(self, request):
        data = request.data
        try:
            image_url = generate_image(data["description"])
            if not image_url:
                return Response(
                    "Error to generate image",
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            print(f"Image URL: {image_url}")
            data = {"imageUrl": image_url}
            return Response(data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Response(
                "Error to generate image", status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
