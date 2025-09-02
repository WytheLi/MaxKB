import uuid

from django.core.validators import RegexValidator
from django.db import models

class Company(models.Model):
    """企业信息表"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name="企业名称")
    uscc = models.CharField(
        max_length=18,
        unique=True,
        verbose_name="统一社会信用代码",
        validators=[RegexValidator(
            regex='^[0-9A-Z]{18}$',
            message='统一社会信用代码格式不正确'
        )]
    )
    remark = models.TextField(blank=True, null=True, verbose_name="备注")
    license_image = models.TextField(blank=True, null=True, verbose_name="营业执照")   # 营业执照应该放在一个单独的表中，这里不拆分了
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    is_active = models.BooleanField(default=True, verbose_name="是否激活")

    class Meta:
        db_table = 'company'
        verbose_name = '企业信息'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name
