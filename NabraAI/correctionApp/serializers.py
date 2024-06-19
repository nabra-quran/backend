from rest_framework import serializers
from .models import *

class NabraUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = NabraUser
        fields = ['id', 'email', 'first_name', 'last_name', 'password', 'gender', 'birthday', 'country']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = NabraUser
        fields = ('id', 'email', 'first_name', 'last_name', 'gender', 'birthday', 'score', 'country')

class EmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = NabraUser
        fields = ('email',)

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = NabraUser
        fields = ('email', 'password', 'first_name', 'last_name', 'gender', 'birthday', 'country')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = NabraUser.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            gender=validated_data.get('gender', 'O'),
            birthday=validated_data['birthday'],
            country=validated_data['country']
        )
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class UserDetailSerializer(serializers.Serializer):
    email = serializers.EmailField()

class AudioFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioFile
        fields = ['id', 'audio_file', 'surah_num', 'ayah_num', 'email', 'uploaded_at']

class AudioSearchFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioSearchFile
        fields = ['id', 'audio_file', 'uploaded_at']
