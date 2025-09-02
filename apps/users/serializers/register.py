import re

from django.db import transaction
from rest_framework import serializers

from modules.models import Company
from users.models import User
from users.utils.sms import SMSService


class CompanyRegisterSerializer(serializers.ModelSerializer):
    """企业注册序列化器"""

    class Meta:
        model = Company
        fields = ('name', 'uscc', 'remark', 'license_image')
        extra_kwargs = {
            'remark': {'required': False, 'allow_blank': True},
            'license_image': {'required': False, 'allow_blank': True},
        }

    def validate_uscc(self, value):
        """验证统一社会信用代码格式"""
        pattern = r'^[0-9A-Z]{18}$'
        if not re.match(pattern, value):
            raise serializers.ValidationError("统一社会信用代码格式不正确")
        return value


class UserRegisterSerializer(serializers.ModelSerializer):
    """用户注册序列化器"""
    company = CompanyRegisterSerializer()
    sms_code = serializers.CharField(max_length=6, min_length=6)

    class Meta:
        model = User
        fields = (
            'username', 'sms_code', 'email', 'phone', 'company'
        )
        extra_kwargs = {
            'email': {'required': False, 'allow_blank': True},
        }

    def validate(self, attrs):
        """验证密码是否匹配"""
        sms_service = SMSService()
        success, message = sms_service.verify_code(attrs['phone'], attrs['sms_code'])
        if not success:
            raise serializers.ValidationError({"sms_code": message})

        # 检查用户名是否已存在
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError({"username": "该用户名已存在"})

        # 检查手机号是否已存在
        if User.objects.filter(phone=attrs['phone']).exists():
            raise serializers.ValidationError({"phone": "该手机号已注册"})

        # 检查统一社会信用代码是否已存在
        if Company.objects.filter(uscc=attrs['company']['uscc']).exists():
            raise serializers.ValidationError({"company": {"uscc": "该统一社会信用代码已注册"}})

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """创建用户和企业"""
        company_data = validated_data.pop('company')
        _ = validated_data.pop('sms_code')

        # 创建企业
        company = Company.objects.create(**company_data)

        # 创建用户并关联企业
        user = User.objects.create(
            **validated_data,
            company=company,
            role='company_admin',  # 设置为管理员角色
            source='LOCAL'
        )

        # 设置密码
        password = "Bohao@123.."
        user.set_password(password)
        user.save()

        return user


class SMSVerificationSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=11, min_length=11)

    def validate_phone(self, value):
        # 简单的手机号格式验证
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式不正确')
        return value
