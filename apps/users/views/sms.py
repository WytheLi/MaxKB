from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from users.serializers.sms import SMSVerificationSerializer
from users.throttles import SMSRateThrottle
from users.utils.sms import SMSService


class SendSMSAPIView(APIView):
    """发送短信验证码API视图"""
    throttle_classes = [SMSRateThrottle]

    def post(self, request):
        serializer = SMSVerificationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        phone_number = serializer.validated_data['phone']
        template_type = serializer.validated_data['template_type']

        sms_service = SMSService()
        success, message = sms_service.send_verification_code(phone_number, template_type)

        status_code = status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST
        return Response({'success': success, 'message': message}, status=status_code)
