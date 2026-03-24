from rest_framework import serializers

class ChatRequestSerializer(serializers.Serializer):
    document_id = serializers.UUIDField(required=False, allow_null=True)
    question = serializers.CharField(max_length=1000)
