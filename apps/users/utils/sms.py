import random
import logging
from enum import Enum
from typing import Tuple

from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.sms.v20210111 import sms_client, models
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class SMSTemplateType(Enum):
    """短信模板类型枚举"""
    REGISTER = "register"  # 注册验证码
    LOGIN = "login"        # 登录验证码
    RESET_PASSWORD = "reset_password"  # 重置密码验证码
    BIND_PHONE = "bind_phone"  # 绑定手机验证码
    CHANGE_PHONE = "change_phone"  # 更换手机验证码


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

    def _get_verification_key(self, phone_number: str, template_type: SMSTemplateType) -> str:
        """
        获取缓存键名
        :param phone_number: 手机号
        :param template_type: 模板类型
        :return: (验证码缓存键, 频率限制缓存键, 错误计数缓存键)
        """
        prefix = f"sms_{template_type}_"
        return f"{prefix}verification_{phone_number}"

    def _get_error_count_key(self, phone_number: str, template_type: SMSTemplateType) -> str:
        prefix = f"sms_{template_type}_"
        return f"{prefix}error_count_{phone_number}"

    def _generate_code(self, length: int = 6) -> str:
        """生成指定长度的随机数字验证码"""
        return ''.join([str(random.randint(0, 9)) for _ in range(length)])

    def _send_code(
            self,
            phone_number: str,
            template_type: SMSTemplateType,
            code_length: int = 6,
            expire_time: int = 300
    ) -> Tuple[bool, str]:
        """
        发送验证码短信
        :param phone_number: 手机号码
        :param template_type: 验证码类型
        :param code_length: 验证码长度
        :param expire_time: 验证码过期时间(秒)
        :return: (是否成功, 消息)
        """
        # 生成随机验证码
        sms_code = self._generate_code(code_length)

        # 获取缓存键
        verification_key = self._get_verification_key(phone_number, template_type)

        try:
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
                # 发送成功，将验证码存入缓存
                cache.set(verification_key, sms_code, timeout=expire_time)

                logger.info(f"{template_type}验证码发送成功，手机号: {phone_number}")
                return True, '发送成功'
            else:
                error_msg = resp.SendStatusSet[0].Message if resp.SendStatusSet else "未知错误"
                logger.error(f"{template_type}验证码发送失败，手机号: {phone_number}, 错误: {error_msg}")
                return False, error_msg

        except TencentCloudSDKException as e:
            logger.exception(f"腾讯云短信发送异常，手机号: {phone_number}, 类型: {template_type}")
            return False, str(e)
        except Exception as e:
            logger.exception(f"短信发送异常，手机号: {phone_number}, 类型: {template_type}")
            return False, str(e)

    def _verify_code(
            self,
            phone_number: str,
            code: str,
            template_type: SMSTemplateType,
            max_error_count: int = 5,
            error_count_expire: int = 300
    ) -> Tuple[bool, str]:
        """
        验证短信验证码
        :param phone_number: 手机号码
        :param code: 用户输入的验证码
        :param template_type: 验证码类型
        :param max_error_count: 最大错误次数
        :param error_count_expire: 错误计数过期时间(秒)
        :return: (是否验证成功, 消息)
        """
        # 获取缓存键
        verification_key = self._get_verification_key(phone_number, template_type)
        error_count_key = self._get_error_count_key(phone_number, template_type)

        cached_code = cache.get(verification_key)

        if not cached_code:
            return False, '验证码已过期'

        if cached_code != code:
            # 错误次数限制
            error_count = cache.get(error_count_key, 0)

            if error_count >= max_error_count:
                cache.delete(verification_key)  # 删除验证码，需要重新获取
                cache.delete(error_count_key)  # 删除错误计数
                return False, '错误次数过多，请重新获取验证码'

            cache.set(error_count_key, error_count + 1, timeout=error_count_expire)
            return False, '验证码错误'

        # 验证成功后删除相关缓存
        cache.delete(verification_key)
        cache.delete(error_count_key)
        return True, '验证成功'

    def send_verification_code(self, phone_number: str, template_type: SMSTemplateType) -> Tuple[bool, str]:
        """发送验证码"""
        return self._send_code(phone_number, template_type)

    def verify_code(self, phone_number: str, code: str, template_type: SMSTemplateType) -> Tuple[bool, str]:
        """验证码验证"""
        return self._verify_code(phone_number, code, template_type)
