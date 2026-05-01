# -*- coding: utf-8 -*-
"""
员工模型扩展
添加飞书账号绑定 + 入职通知
"""

import logging
from odoo import models, fields, api, _
from datetime import datetime
from .notify_message import send_lark_notification

_logger = logging.getLogger(__name__)


class HrEmployee(models.Model):
    """扩展员工模型：飞书账号绑定 + 入职通知"""
    _inherit = 'hr.employee'

    lark_open_id = fields.Char(
        string=_('Lark Open ID'),
        help=_('Lark user Open ID for sending messages')
    )
    lark_user_id = fields.Char(
        string=_('Lark User ID'),
        help=_('Lark user User ID')
    )

    @api.model
    def create(self, vals):
        """创建员工时发送入职欢迎通知"""
        employee = super(HrEmployee, self).create(vals)
        try:
            employee._send_onboarding_notification()
        except Exception as e:
            _logger.error(f"Error sending onboarding notification: {e}", exc_info=True)
        return employee

    def _send_onboarding_notification(self):
        """发送员工入职欢迎卡片"""
        company = self.env.company
        if not company.lark_notify_enabled:
            return

        # 接收者：新员工本人 + 公司管理员
        notify_users = self.env['res.users'].search([
            ('share', '=', False),
            ('notify_by_lark', '=', True),
        ])
        if not notify_users:
            return

        open_ids = []
        for user in notify_users:
            if user.employee_id and user.employee_id.lark_open_id:
                open_ids.append(user.employee_id.lark_open_id)

        if not open_ids:
            return

        card = self._build_onboarding_card()
        send_lark_notification(self.env, open_ids, card)

    def _build_onboarding_card(self):
        """构建入职欢迎卡片"""
        employee_name = self.name or '新员工'
        department = self.department_id.name or '未分配'
        job_title = self.job_title or '未设定'
        work_email = self.work_email or '未设置'
        work_phone = self.work_phone or '未设置'
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

        odoo_url = self._build_odoo_url()

        elements = [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**姓名：** {employee_name}"}
            },
            {
                "tag": "div",
                "fields": [
                    {"is_short": True, "text": {"tag": "lark_md", "content": f"**部门：**\n{department}"}},
                    {"is_short": True, "text": {"tag": "lark_md", "content": f"**职位：**\n{job_title}"}}
                ]
            },
            {
                "tag": "div",
                "fields": [
                    {"is_short": True, "text": {"tag": "lark_md", "content": f"**邮箱：**\n{work_email}"}},
                    {"is_short": True, "text": {"tag": "lark_md", "content": f"**电话：**\n{work_phone}"}}
                ]
            },
            {"tag": "hr"},
            {"tag": "note", "elements": [{"tag": "plain_text", "content": f"入职时间：{timestamp}"}]},
        ]

        if odoo_url and odoo_url != "#":
            elements.append({
                "tag": "action",
                "actions": [{
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "查看员工档案"},
                    "type": "primary",
                    "url": odoo_url
                }]
            })

        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "green",
                "title": {"tag": "plain_text", "content": f"🎉 新员工入职 - {employee_name}"}
            },
            "elements": elements
        }

    def _build_odoo_url(self):
        """构建 Odoo 员工档案链接"""
        base_url = self.env.company.lark_notify_odoo_url or self.get_base_url()
        if not base_url:
            return "#"
        base_url = base_url.rstrip('/')
        return f"{base_url}/web?model={self._name}&id={self.id}&cids={self.env.company.id}&view_type=form"
