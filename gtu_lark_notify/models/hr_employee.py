# -*- coding: utf-8 -*-
"""
员工模型扩展
添加飞书账号绑定字段
"""

from odoo import models, fields


class HrEmployee(models.Model):
    """
    扩展员工模型
    添加飞书账号绑定
    """
    _inherit = 'hr.employee'
    
    # 飞书账号绑定
    lark_open_id = fields.Char(
        string='飞书Open ID',
        help='飞书用户的Open ID，用于发送消息'
    )
    
    lark_user_id = fields.Char(
        string='飞书用户ID',
        help='飞书用户的User ID'
    )
