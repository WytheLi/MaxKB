from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from users.serializers.register import UserRegisterSerializer


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
