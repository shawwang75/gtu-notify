# -*- coding: utf-8 -*-
"""
员工模型扩展
添加飞书账号绑定字段
"""

from odoo import models, fields, _


class HrEmployee(models.Model):
    """
    扩展员工模型
    添加飞书账号绑定
    """
    _inherit = 'hr.employee'
    
    # 飞书账号绑定
    lark_open_id = fields.Char(
        string=_('Lark Open ID'),
        help=_('Lark user Open ID for sending messages')
    )
    
    lark_user_id = fields.Char(
        string=_('Lark User ID'),
        help=_('Lark user User ID')
    )
