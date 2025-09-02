import re

from rest_framework import serializers

from users.utils.sms import SMSTemplateType


class SMSVerificationSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=11, min_length=11)
    template_type = serializers.ChoiceField(choices=[(tag.value, tag.name) for tag in SMSTemplateType])

    def validate_phone(self, value):
        # 简单的手机号格式验证
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('手机号格式不正确')
        return value
