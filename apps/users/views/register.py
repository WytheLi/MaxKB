from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from users.serializers.register import UserRegisterSerializer, SMSVerificationSerializer
from users.utils.sms import SMSService


class UserRegisterView(APIView):
    """用户注册视图"""

    def post(self, request):
        serializer = UserRegisterSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            # 返回注册成功响应
            return Response({
                "success": True,
                "message": "注册成功",
                "data": {
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "company_name": user.company.name
                }
            }, status=status.HTTP_201_CREATED)

        # 返回验证错误
        return Response({
            "success": False,
            "message": "注册失败",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class SendSMSAPIView(APIView):
    """发送短信验证码API视图"""

    def post(self, request):
        serializer = SMSVerificationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        phone_number = serializer.validated_data['phone']
        sms_service = SMSService()
        success, message = sms_service.send_verification_code(phone_number)

        status_code = status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
        return Response({'success': success, 'message': message}, status=status_code)
