# -*- coding: utf-8 -*-
"""
工时单模型扩展
添加工时单操作的飞书通知功能
"""

import logging
from odoo import models, api, _
from datetime import datetime
from .notify_message import send_lark_notification

_logger = logging.getLogger(__name__)


class AccountAnalyticLine(models.Model):
    """
    扩展工时单模型
    添加创建、修改、删除通知
    """
    _inherit = 'account.analytic.line'

    def _send_lark_notification(self, action_type):
        """
        发送飞书通知

        :param action_type: 操作类型 (create/write/unlink)
        """
        # 检查是否启用通知
        company = self.env.company
        if not company.lark_notify_enabled:
            return

        # 获取通知接收人
        notify_users = self._get_notification_recipients()
        if not notify_users:
            return

        # 过滤开启飞书通知的用户
        notify_users = notify_users.filtered(lambda u: u.notify_by_lark)
        if not notify_users:
            return

        # 获取飞书Open ID
        open_ids = self._get_user_open_ids(notify_users)
        if not open_ids:
            return

        # 构建卡片消息
        card_message = self._build_timesheet_card(action_type)

        # 发送通知
        send_lark_notification(self.env, open_ids, card_message)

    def _get_notification_recipients(self):
        """
        获取通知接收人
        """
        users = self.env['res.users']

        # 1. 员工本人
        if self.employee_id and self.employee_id.user_id:
            users |= self.employee_id.user_id

        # 2. 项目经理
        if self.project_id and self.project_id.user_id:
            users |= self.project_id.user_id

        # 3. 创建者
        if self.create_uid:
            users |= self.create_uid

        return users

    def _get_user_open_ids(self, users):
        """
        获取用户的飞书Open ID
        """
        open_ids = []
        for user in users:
            if user.employee_id and user.employee_id.lark_open_id:
                open_ids.append(user.employee_id.lark_open_id)
        return open_ids

    def _build_timesheet_card(self, action_type):
        """
        构建工时单通知卡片（美观版）
        """
        # 获取工时单信息
        employee_name = self.employee_id.name if self.employee_id else '未知'
        project_name = self.project_id.name if self.project_id else '无项目'
        task_name = self.task_id.name if self.task_id else '无任务'
        hours = self.unit_amount or 0.0
        date = self.date or datetime.now().date()
        description = self.name or ''

        # 操作类型
        action_names = {
            'create': '新建',
            'write': '更新',
            'unlink': '删除',
        }
        action_name = action_names.get(action_type, '变更')

        # 操作颜色
        action_colors = {
            'create': 'green',
            'write': 'blue',
            'unlink': 'red',
        }
        header_color = action_colors.get(action_type, 'blue')

        # 构建Odoo链接
        odoo_url = self._build_odoo_url()

        # 时间戳
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

        # 构建卡片元素
        elements = []

        # 1. 员工信息
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**员工：** {employee_name}"
            }
        })

        # 2. 项目和任务（并排显示）
        elements.append({
            "tag": "div",
            "fields": [
                {
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**项目：**\n{project_name}"
                    }
                },
                {
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**任务：**\n{task_name}"
                    }
                }
            ]
        })

        # 3. 日期和工时（并排显示）
        elements.append({
            "tag": "div",
            "fields": [
                {
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**日期：**\n{str(date)}"
                    }
                },
                {
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**工时：**\n{hours} 小时"
                    }
                }
            ]
        })

        # 4. 描述（如果有）
        if description:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**描述：**\n{description}"
                }
            })

        # 5. 分隔线
        elements.append({
            "tag": "hr"
        })

        # 6. 时间戳
        elements.append({
            "tag": "note",
            "elements": [
                {
                    "tag": "plain_text",
                    "content": f"{timestamp}"
                }
            ]
        })

        # 7. 查看详情按钮（仅创建和修改）
        if action_type != 'unlink' and odoo_url:
            elements.append({
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "查看详情"
                        },
                        "type": "primary",
                        "url": odoo_url
                    }
                ]
            })

        # 构建完整卡片
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": header_color,
                "title": {
                    "tag": "plain_text",
                    "content": f"工时单 {action_name}"
                }
            },
            "elements": elements
        }

        return card

    def _build_odoo_url(self):
        """
        构建Odoo记录链接
        优先使用公司配置的 lark_notify_odoo_url，
        否则回退到系统 web.base.url
        """
        base_url = self.env.company.lark_notify_odoo_url or self.get_base_url()
        if not base_url:
            return None
        base_url = base_url.rstrip('/')
        return f"{base_url}/web?model={self._name}&id={self.id}&cids={self.env.company.id}&view_type=form"

    @api.model
    def create(self, vals):
        """
        创建工时单时发送通知
        """
        record = super(AccountAnalyticLine, self).create(vals)

        try:
            record._send_lark_notification('create')
        except Exception as e:
            _logger.error(f"Error sending create notification: {e}", exc_info=True)

        return record

    def write(self, vals):
        """
        修改工时单时发送通知
        """
        result = super(AccountAnalyticLine, self).write(vals)

        try:
            for record in self:
                record._send_lark_notification('write')
        except Exception as e:
            _logger.error(f"Error sending write notification: {e}", exc_info=True)

        return result

    def unlink(self):
        """
        删除工时单时发送通知
        """
        # 先发送通知，再删除
        try:
            for record in self:
                record._send_lark_notification('unlink')
        except Exception as e:
            _logger.error(f"Error sending unlink notification: {e}", exc_info=True)

        return super(AccountAnalyticLine, self).unlink()
