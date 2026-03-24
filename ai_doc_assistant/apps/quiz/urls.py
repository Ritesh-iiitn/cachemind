from django.urls import path
from .views import QuizGenerateAPIView

urlpatterns = [
    path('generate/', QuizGenerateAPIView.as_view(), name='quiz-generate'),
]
