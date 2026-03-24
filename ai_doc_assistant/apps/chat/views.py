from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import ChatRequestSerializer
from .services import ChatService

class ChatAPIView(APIView):
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        if serializer.is_valid():
            question = serializer.validated_data['question']
            document_id = serializer.validated_data.get('document_id')
            
            try:
                answer = ChatService.answer_question(question, str(document_id) if document_id else None)
                return Response({"question": question, "answer": answer}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
