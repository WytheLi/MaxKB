import random
import logging

from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.sms.v20210111 import sms_client, models
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class SMSService:
    """
    腾讯云短信服务相关文档：https://cloud.tencent.com/document/product/382/43196
    """

    def __init__(self):
        self.sdk_appid = settings.TENCENTCLOUD_SMS_CONFIG['SDK_APPID']
        self.secret_id = settings.TENCENTCLOUD_SMS_CONFIG['SECRET_ID']
        self.secret_key = settings.TENCENTCLOUD_SMS_CONFIG['SECRET_KEY']
        self.sign_name = settings.TENCENTCLOUD_SMS_CONFIG['SIGN_NAME']
        self.template_code = settings.TENCENTCLOUD_SMS_CONFIG['TEMPLATE_CODE']
        self.region = settings.TENCENTCLOUD_SMS_CONFIG['REGION']

        _credential = credential.Credential(self.secret_id, self.secret_key)
        self.client = sms_client.SmsClient(_credential, self.region)

    def send_verification_code(self, phone_number):
        """发送验证码短信"""
        # 生成6位随机验证码
        sms_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

        try:
            # 检查发送频率限制（60秒内只能发送一次）
            rate_limit_key = f'sms_rate_limit_{phone_number}'
            if cache.has_key(rate_limit_key):
                return False, '发送过于频繁，请稍后再试'

            # 创建发送短信请求对象
            req = models.SendSmsRequest()
            # 设置请求参数
            req.SmsSdkAppId = self.sdk_appid
            req.SignName = self.sign_name
            req.TemplateId = self.template_code
            req.TemplateParamSet = [sms_code]  # 模板参数，按照模板中的顺序传入
            req.PhoneNumberSet = ["+86" + phone_number]  # 手机号格式需要加上国家码

            # 发送请求
            resp = self.client.SendSms(req)

            # 检查响应
            if resp.SendStatusSet and resp.SendStatusSet[0].Code == "Ok":
                # 发送成功，将验证码存入Redis（5分钟有效期）
                cache_key = f'sms_verification_{phone_number}'
                cache.set(cache_key, sms_code, timeout=300)

                # 设置频率限制（60秒内不能再次发送）
                cache.set(rate_limit_key, '1', timeout=60)

                logger.info(f"短信验证码发送成功，手机号: {phone_number}")
                return True, '发送成功'
            else:
                error_msg = resp.SendStatusSet[0].Message if resp.SendStatusSet else "未知错误"
                logger.error(f"短信发送失败，手机号: {phone_number}, 错误: {error_msg}")
                return False, error_msg

        except TencentCloudSDKException as e:
            logger.exception(f"腾讯云短信发送异常，手机号: {phone_number}")
            return False, str(e)
        except Exception as e:
            logger.exception(f"短信发送异常，手机号: {phone_number}")
            return False, str(e)

    def verify_code(self, phone_number, code):
        """验证短信验证码"""
        cache_key = f'sms_verification_{phone_number}'
        cached_code = cache.get(cache_key)

        if not cached_code:
            return False, '验证码已过期'

        if cached_code != code:
            # 错误次数限制
            error_count_key = f'sms_error_count_{phone_number}'
            error_count = cache.get(error_count_key, 0)

            if error_count >= 5:  # 最多允许错误5次
                cache.delete(cache_key)  # 删除验证码，需要重新获取
                return False, '错误次数过多，请重新获取验证码'

            cache.set(error_count_key, error_count + 1, timeout=300)  # 5分钟内错误计数
            return False, '验证码错误'

        # 验证成功后删除相关缓存
        cache.delete(cache_key)
        cache.delete(f'sms_error_count_{phone_number}')
        return True, '验证成功'
