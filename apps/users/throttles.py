from rest_framework.throttling import SimpleRateThrottle


class SMSRateThrottle(SimpleRateThrottle):
    """
    短信发送频率限制
    基于手机号和模板类型进行限流
    """
    scope = 'sms_send'

    def get_cache_key(self, request, view):
        # 获取手机号和模板类型
        phone = request.data.get('phone')
        template_type = request.data.get('template_type')

        if phone and template_type:
            return f'sms_rate_limit_{template_type}_{phone}'
        return None
