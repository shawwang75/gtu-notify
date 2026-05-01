# -*- coding: utf-8 -*-
"""
用户模型扩展
添加飞书通知偏好设置
"""

from odoo import models, fields, _


class ResUsers(models.Model):
    """
    扩展用户模型
    添加飞书通知偏好
    """
    _inherit = 'res.users'

    notify_by_lark = fields.Boolean(
        string=_('Notify by Lark'),
        default=True,
        help=_('Whether to receive notifications via Lark')
    )
