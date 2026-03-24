from rest_framework import serializers

class QuizRequestSerializer(serializers.Serializer):
    document_id = serializers.UUIDField()
