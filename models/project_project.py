# -*- coding: utf-8 -*-
"""
项目模型扩展
监听项目状态变更，推送飞书通知
"""

import logging
from odoo import models, api, _
from datetime import datetime
from .notify_message import send_lark_notification

_logger = logging.getLogger(__name__)


class ProjectProject(models.Model):
    """扩展项目模型：状态变更通知"""
    _inherit = 'project.project'

    def write(self, vals):
        """监听 stage_id 变更，推送通知"""
        old_stage = {p.id: p.stage_id.name for p in self} if 'stage_id' in vals else {}
        result = super(ProjectProject, self).write(vals)

        if 'stage_id' in vals:
            try:
                for record in self:
                    new_stage_name = record.stage_id.name or '未命名'
                    old_stage_name = old_stage.get(record.id, '未知')
                    if old_stage_name != new_stage_name:
                        record._send_stage_change_notification(old_stage_name, new_stage_name)
            except Exception as e:
                _logger.error(f"Error sending stage change notification: {e}", exc_info=True)

        return result

    def _send_stage_change_notification(self, old_stage, new_stage):
        """发送项目状态变更卡片"""
        company = self.env.company
        if not company.lark_notify_enabled:
            return

        open_ids = self._get_project_notify_open_ids()
        if not open_ids:
            return

        card = self._build_stage_change_card(old_stage, new_stage)
        send_lark_notification(self.env, open_ids, card)

    def _get_project_notify_open_ids(self):
        """获取项目通知接收者的飞书 Open ID"""
        open_ids = []
        # 项目负责人
        if self.user_id and self.user_id.employee_id and self.user_id.employee_id.lark_open_id:
            open_ids.append(self.user_id.employee_id.lark_open_id)
        # 项目关注者
        for partner in self.message_partner_ids:
            for user in partner.user_ids:
                if user.employee_id and user.employee_id.lark_open_id and user.notify_by_lark:
                    oid = user.employee_id.lark_open_id
                    if oid not in open_ids:
                        open_ids.append(oid)
        return open_ids

    def _build_stage_change_card(self, old_stage, new_stage):
        """构建项目状态变更卡片"""
        project_name = self.name or '未命名'
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        odoo_url = self._build_odoo_url()

        elements = [
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**项目：** {project_name}"}},
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**状态变更：** {old_stage} → {new_stage}"}},
            {"tag": "hr"},
            {"tag": "note", "elements": [{"tag": "plain_text", "content": f"🕐 {timestamp}"}]},
        ]

        if odoo_url and odoo_url != "#":
            elements.append({
                "tag": "action",
                "actions": [{
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "查看项目"},
                    "type": "primary",
                    "url": odoo_url
                }]
            })

        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "template": "blue",
                "title": {"tag": "plain_text", "content": f"📊 项目状态变更"}
            },
            "elements": elements
        }

    def _build_odoo_url(self):
        base_url = self.env.company.lark_notify_odoo_url or self.get_base_url()
        if not base_url:
            return "#"
        base_url = base_url.rstrip('/')
        return f"{base_url}/web?model={self._name}&id={self.id}&cids={self.env.company.id}&view_type=form"
