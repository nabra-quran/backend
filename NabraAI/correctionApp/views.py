from rest_framework import viewsets, status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from sklearn.preprocessing import StandardScaler
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError

from .models import *
from .serializers import *
from .audio_pross_functions import get_mfcc

import os
import ast
import requests
import numpy as np
import pandas as pd
import tensorflow as tf

class UserListView(APIView):
    def get(self, request, format=None):
        try:
            queryset = NabraUser.objects.all()
            serializer = UserSerializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": "Internal Server Error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class RegisterView(generics.CreateAPIView):
    queryset = NabraUser.objects.all()
    serializer_class = RegisterSerializer

class LoginView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            serializer = LoginSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = authenticate(
                request,
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password']
            )
            if not user:
                return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
            print(user)
            user_serializer = EmailSerializer(user)
            return Response({'user': user_serializer.data}, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": "Internal Server Error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserDetailByEmailView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            serializer = UserDetailSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            email = serializer.validated_data['email']
            user = NabraUser.objects.get(email=email)
            user_serializer =  UserSerializer(user)
            return Response({'user': user_serializer.data}, status=status.HTTP_200_OK)
        except NabraUser.DoesNotExist:
            raise Response({'msg': "User not found"},
                            status=status.HTTP_404_NOT_FOUND)

class AudioFileViewSet(viewsets.ModelViewSet):
    queryset = AudioFile.objects.all()
    serializer_class = AudioFileSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        audio_file = serializer.instance
        recorded_file = audio_file.audio_file.path

        predictions_tajweed_score = {}

        predictions_text = apply_deepspeech_model(recorded_file)['predictions_text']
        original_text = get_original_text(audio_file.surah_num, audio_file.ayah_num)

        aya_text_score = calculate_text_score(predictions_text, original_text)
        predictions_tajweed_score['aya_text'] = aya_text_score

        mfcc_data = get_mfcc(recorded_file)
        X_padded = tf.keras.preprocessing.sequence.pad_sequences([mfcc_data], maxlen=8000, padding='post', dtype='float32')
        predictions_tajweed = apply_tajweed_rules(X_padded, audio_file.surah_num, audio_file.ayah_num)
    
        for prediction in predictions_tajweed:
            predicted_list = prediction['predictions_list']
            original_list = prediction['original_list']
            score = calculate_specific_score(predicted_list, original_list)
            predictions_tajweed_score[prediction['rule']] = score

        nabra_user = NabraUser.objects.get(email=audio_file.email)
        user_score, created = UserScore.objects.update_or_create(
            surah_num = audio_file.surah_num,
            aya_num = audio_file.ayah_num,
            nabra_user = nabra_user,
            aya_text_score = predictions_tajweed_score['aya_text'],
            Idgham_score = predictions_tajweed_score['Idgham'],
            Ikhfaa_score = predictions_tajweed_score['Ikhfaa'],
            imala_score = predictions_tajweed_score['imala'],
            madd_2_score = predictions_tajweed_score['madd_2'],
            madd_6_Lazim_score = predictions_tajweed_score['madd_6_Lazim'],
            madd_6_score = predictions_tajweed_score['madd_6'],
            madd_246_score = predictions_tajweed_score['madd_246'],
            qalqala_score = predictions_tajweed_score['qalqala'],
            tafkhim_score = predictions_tajweed_score['tafkhim']
        )
        corrections = identify_correct_predictions(original_text, predictions_text, predictions_tajweed)
        response_data = {
            'surah_num': audio_file.surah_num,
            'ayah_num': audio_file.ayah_num,
            'predictions_tajweed': predictions_tajweed,
            'predictions_text': predictions_text,
            'original_text': original_text,
            'corrections': corrections
        }
        return Response(response_data, status=status.HTTP_201_CREATED)

def get_original_indexing(sura_no, aya_no, rule):
    csv_file_path = 'Data/hizb60_and_alfatiha_text_indexing.csv' 
    try:
        df = pd.read_csv(csv_file_path)
        filtered_df = df[(df['sura_no'] == sura_no) & (df['aya_no'] == aya_no)]
        if not filtered_df.empty:
            indxing_value = ast.literal_eval(filtered_df.iloc[0][rule])
            return indxing_value
        else:
            return None
    except FileNotFoundError:
        print(f"File not found at path: {csv_file_path}")
        return None

def get_original_text(sura_no, aya_no):
    csv_file_path = 'Data/hizb60_and_alfatiha_text_indexing.csv' 
    try:
        df = pd.read_csv(csv_file_path)
        filtered_df = df[(df['sura_no'] == sura_no) & (df['aya_no'] == aya_no)]
        if not filtered_df.empty:
            indxing_value = filtered_df.iloc[0]['aya_text']
            return indxing_value
        else:
            return None
    except FileNotFoundError:
        print(f"File not found at path: {csv_file_path}")
        return None

def apply_tajweed_rules(X_padded, sura_no, aya_no, export_dir='AI Models/New'):
    tajweed_rules = ['madd_6_Lazim', 'madd_246', 'madd_6', 'madd_2', 'Ikhfaa', 'Idgham', 'tafkhim', 'qalqala', 'imala']
    predictions_list = []
    scaler = StandardScaler()
    X_padded_scaled = scaler.fit_transform(X_padded.reshape(-1, X_padded.shape[-1])).reshape(X_padded.shape)

    for rule in tajweed_rules:
        model_filename = f'{rule}_tajweed_rule_model.h5'
        model_path = os.path.join(export_dir, model_filename)
        if os.path.exists(model_path):
            try:
                loaded_model = tf.keras.models.load_model(model_path)
            except Exception as e:
                raise FileNotFoundError(f'Error loading model: {model_path}. Exception: {e}')
        else:
            raise FileNotFoundError(f'Model file not found: {model_path}')
        
        predictions = loaded_model.predict(X_padded_scaled)
        predictions[predictions < 0] = -1
        predictions = np.round(predictions).astype('int32')
        original_list = get_original_indexing(sura_no, aya_no, rule)
        intersection_set = set(predictions.flatten().tolist()).intersection(original_list)
        if len(intersection_set) == 0:
            intersection_set.add(-1)

        predictions_list.append({
            'rule': rule,
            'predictions_list': list(intersection_set),
            'original_list': original_list,
        })
    return predictions_list

def apply_deepspeech_model(recorded_file):
    try:
        url = 'http://127.0.0.1:8000/transcribe/'
        data = {
            'audio_file_path': recorded_file,
        }
        response = requests.post(url, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            return {'error': f'Failed to process audio: {response}'}
    except Exception as e:
        return {'error': f'Error processing audio: {e}'}

def identify_correct_predictions(original_text, predicted_text, predictions_tajweed):
    corrections = []
    try:
        min_length = min(len(original_text), len(predicted_text))
        original_text = original_text[:min_length]
        predicted_text = predicted_text[:min_length]

        for i in range(min_length):
            if original_text[i] != predicted_text[i]:
                correct_letter = predicted_text[i]
                rule_applied = None
        
                for prediction in predictions_tajweed:
                    if i in prediction['original_list']:
                        rule_applied = prediction['rule']
                        break

                corrections.append({
                    'index': i,
                    'original_letter': original_text[i],
                    'predicted_letter': correct_letter,
                    'rule_applied': rule_applied
                })
    except Exception as e:
        print(f"Error in identify_correct_predictions: {e}")
        return []
    return corrections

def calculate_specific_score(predicted_list, original_list):
    if not original_list:
        return 0
    intersection_count = len(set(predicted_list).intersection(original_list))
    total_count = len(original_list)
    return (intersection_count / total_count) * 100

def calculate_text_score(predicted_text, original_text):
    if not original_text:
        return 0
    intersection_count = sum(1 for p, o in zip(predicted_text, original_text) if p == o)
    total_count = len(original_text)
    return (intersection_count / total_count) * 100
