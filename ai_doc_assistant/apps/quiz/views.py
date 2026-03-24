from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import QuizRequestSerializer
from .services import QuizService

class QuizGenerateAPIView(APIView):
    def post(self, request):
        serializer = QuizRequestSerializer(data=request.data)
        if serializer.is_valid():
            document_id = serializer.validated_data['document_id']
            try:
                quiz = QuizService.generate_quiz(document_id)
                return Response({"document_id": document_id, "quiz": quiz}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
