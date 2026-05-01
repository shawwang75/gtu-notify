# -*- coding: utf-8 -*-
"""
项目任务模型扩展
监听任务分配变更 + 状态变更，推送飞书通知
"""

import logging
from odoo import models, api, _
from datetime import datetime
from .notify_message import send_lark_notification

_logger = logging.getLogger(__name__)


class ProjectTask(models.Model):
    """扩展项目任务模型：任务分配 + 状态变更通知"""
    _inherit = 'project.task'

    def write(self, vals):
        """监听 user_ids 变更（分配）和 stage_id 变更（状态）"""
        old_user_ids = {}
        old_stage = {}

        if 'user_ids' in vals:
            for task in self:
                old_user_ids[task.id] = set(task.user_ids.ids)
        if 'stage_id' in vals:
            for task in self:
                old_stage[task.id] = task.stage_id.name or '未知'

        result = super(ProjectTask, self).write(vals)

        # 分配通知
        if 'user_ids' in vals:
            try:
                for task in self:
                    new_ids = set(task.user_ids.ids)
                    old_ids = old_user_ids.get(task.id, set())
                    added = task.user_ids.browse(list(new_ids - old_ids))
                    if added:
                        task._send_task_assignment_notification(added)
            except Exception as e:
                _logger.error(f"Error sending task assignment notification: {e}", exc_info=True)

        # 状态变更通知
        if 'stage_id' in vals:
            try:
                for task in self:
                    new_stage_name = task.stage_id.name or '未知'
                    old_stage_name = old_stage.get(task.id, '未知')
                    if old_stage_name != new_stage_name:
                        task._send_task_stage_notification(old_stage_name, new_stage_name)
            except Exception as e:
                _logger.error(f"Error sending task stage notification: {e}", exc_info=True)

        return result

    # ========= 分配通知 =========
    def _send_task_assignment_notification(self, assigned_users):
        company = self.env.company
        if not company.lark_notify_enabled:
            return
        open_ids = self._get_task_recipient_ids(assigned_users)
        if not open_ids:
            return
        card = self._build_assignment_card(assigned_users)
        send_lark_notification(self.env, open_ids, card)

    def _build_assignment_card(self, assigned_users):
        task_name = self.name or '未命名'
        project_name = self.project_id.name or '无项目'
        assignees = ', '.join(u.name for u in assigned_users)
        deadline = str(self.date_deadline) if self.date_deadline else '未设置'
        priority = dict(self._fields['priority'].selection).get(self.priority, '普通')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        odoo_url = self._build_odoo_url()

        elements = [
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**任务：** {task_name}"}},
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**项目：** {project_name}"}},
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**分配给：** {assignees}"}},
            {"tag": "div", "fields": [
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**优先级：**\n{priority}"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**截止日期：**\n{deadline}"}}
            ]},
            {"tag": "hr"},
            {"tag": "note", "elements": [{"tag": "plain_text", "content": f"🕐 {timestamp}"}]},
        ]
        if odoo_url and odoo_url != "#":
            elements.append({
                "tag": "action", "actions": [{
                    "tag": "button", "text": {"tag": "plain_text", "content": "查看任务"},
                    "type": "primary", "url": odoo_url
                }]
            })

        return {
            "config": {"wide_screen_mode": True},
            "header": {"template": "purple", "title": {"tag": "plain_text", "content": "📋 新任务分配"}},
            "elements": elements
        }

    # ========= 状态变更通知 =========
    def _send_task_stage_notification(self, old_stage, new_stage):
        company = self.env.company
        if not company.lark_notify_enabled:
            return
        open_ids = self._get_task_stage_recipient_ids()
        if not open_ids:
            return
        card = self._build_task_stage_card(old_stage, new_stage)
        send_lark_notification(self.env, open_ids, card)

    def _get_task_recipient_ids(self, assigned_users):
        open_ids = []
        for user in assigned_users:
            if user.employee_id and user.employee_id.lark_open_id:
                open_ids.append(user.employee_id.lark_open_id)
        return open_ids

    def _get_task_stage_recipient_ids(self):
        open_ids = []
        # 任务负责人
        for user in self.user_ids:
            if user.employee_id and user.employee_id.lark_open_id:
                open_ids.append(user.employee_id.lark_open_id)
        # 关注者
        for partner in self.message_partner_ids:
            for user in partner.user_ids:
                if user.employee_id and user.employee_id.lark_open_id and user.notify_by_lark:
                    oid = user.employee_id.lark_open_id
                    if oid not in open_ids:
                        open_ids.append(oid)
        return open_ids

    def _build_task_stage_card(self, old_stage, new_stage):
        task_name = self.name or '未命名'
        project_name = self.project_id.name or '无项目'
        assignees = ', '.join(u.name for u in self.user_ids) if self.user_ids else '未分配'
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        odoo_url = self._build_odoo_url()

        elements = [
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**任务：** {task_name}"}},
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**项目：** {project_name}"}},
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**状态变更：** {old_stage} → {new_stage}"}},
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**负责人：** {assignees}"}},
            {"tag": "hr"},
            {"tag": "note", "elements": [{"tag": "plain_text", "content": f"🕐 {timestamp}"}]},
        ]
        if odoo_url and odoo_url != "#":
            elements.append({
                "tag": "action", "actions": [{
                    "tag": "button", "text": {"tag": "plain_text", "content": "查看任务"},
                    "type": "primary", "url": odoo_url
                }]
            })

        return {
            "config": {"wide_screen_mode": True},
            "header": {"template": "blue", "title": {"tag": "plain_text", "content": "🔄 任务状态变更"}},
            "elements": elements
        }

    # ========= 通用 =========
    def _build_odoo_url(self):
        base_url = self.env.company.lark_notify_odoo_url or self.get_base_url()
        if not base_url:
            return "#"
        base_url = base_url.rstrip('/')
        return f"{base_url}/web?model={self._name}&id={self.id}&cids={self.env.company.id}&view_type=form"
