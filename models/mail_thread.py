# -*- coding: utf-8 -*-
"""
邮件消息扩展模型
拦截备注消息并优化飞书推送格式
"""

import logging
import re
from html.parser import HTMLParser
from odoo import models, api, _
from odoo.tools import html2plaintext
from .notify_message import send_lark_notification
from datetime import datetime

_logger = logging.getLogger(__name__)


class HTMLTagCleaner(HTMLParser):
    """
    HTML标签清理器
    提取纯文本内容
    """
    def __init__(self):
        super().__init__()
        self.text_content = []

    def handle_data(self, data):
        """处理文本数据"""
        self.text_content.append(data)

    def get_text(self):
        """获取清理后的文本"""
        return ' '.join(self.text_content).strip()


class MailThread(models.AbstractModel):
    """
    扩展mail.thread模型
    优化备注消息的飞书推送格式
    """
    _inherit = 'mail.thread'

    def message_post(self, *, body='', message_type='notification', **kwargs):
        """
        重写message_post方法
        拦截备注消息并优化飞书推送格式
        """
        # 调用父类方法完成Odoo内部消息发送
        message = super(MailThread, self).message_post(
            body=body,
            message_type=message_type,
            **kwargs
        )

        # 检查是否应该发送飞书通知
        try:
            if self._should_send_lark_notification(message):
                self._send_optimized_lark_notification(message, body)
        except Exception as e:
            _logger.error(f"Error sending optimized Lark notification: {e}", exc_info=True)

        return message

    def _should_send_lark_notification(self, message):
        """
        判断是否应该发送飞书通知
        """
        # 1. 检查消息类型（只处理评论/备注）
        if message.message_type not in ['comment', 'notification']:
            return False

        # 2. 检查记录类型（只处理业务对象）
        supported_models = [
            'project.task',        # 项目任务
            'project.project',     # 项目
            'crm.lead',            # CRM线索
            'res.partner',         # 联系人
        ]

        if self._name not in supported_models:
            return False

        # 3. 检查是否有内容
        if not message.body:
            return False

        # 4. 检查是否是系统消息（避免循环）
        if message.author_id and message.author_id.id == self.env.ref('base.partner_root').id:
            return False

        return True

    def _send_optimized_lark_notification(self, message, body):
        """
        发送优化后的飞书通知
        """
        # 1. 提取纯文本内容
        clean_text = self._extract_clean_text(body)

        if not clean_text:
            return

        # 2. 获取通知对象
        notify_users = self._get_message_recipients(message)

        if not notify_users:
            return

        # 3. 过滤开启飞书通知的用户
        notify_users = notify_users.filtered(lambda u: u.notify_by_lark)

        if not notify_users:
            return

        # 4. 获取飞书Open ID
        open_ids = self._get_user_open_ids(notify_users)

        if not open_ids:
            return

        # 5. 构建美观的消息卡片
        card_message = self._build_note_card(message, clean_text)

        # 6. 发送通知
        send_lark_notification(self.env, open_ids, card_message)

    def _extract_clean_text(self, body):
        """
        从HTML中提取纯文本内容
        """
        if not body:
            return ''

        # 方法1：使用Odoo内置的html2plaintext
        try:
            text = html2plaintext(body)
            # 清理多余空白
            text = re.sub(r'\n\s*\n', '\n\n', text)
            text = text.strip()
            if text:
                return text
        except Exception as e:
            _logger.debug(f"html2plaintext failed: {e}")

        # 方法2：自定义HTML解析
        try:
            cleaner = HTMLTagCleaner()
            cleaner.feed(body)
            text = cleaner.get_text()
            # 清理多余空白
            text = re.sub(r'\s+', ' ', text).strip()
            if text:
                return text
        except Exception as e:
            _logger.debug(f"HTMLTagCleaner failed: {e}")

        # 方法3：正则表达式清理
        try:
            # 移除HTML标签
            text = re.sub(r'<[^>]+>', ' ', body)
            # 清理HTML实体
            text = re.sub(r'&nbsp;', ' ', text)
            text = re.sub(r'&lt;', '<', text)
            text = re.sub(r'&gt;', '>', text)
            text = re.sub(r'&amp;', '&', text)
            # 清理多余空白
            text = re.sub(r'\s+', ' ', text).strip()
            return text
        except Exception as e:
            _logger.error(f"All text extraction methods failed: {e}")
            return ''

    def _get_message_recipients(self, message):
        """
        获取消息的接收者
        """
        users = self.env['res.users']

        # 1. 消息的接收者（notification_pids）
        if message.notification_ids:
            for notif in message.notification_ids:
                if notif.res_partner_id and notif.res_partner_id.user_ids:
                    users |= notif.res_partner_id.user_ids

        # 2. 记录的关注者
        if hasattr(self, 'message_partner_ids') and self.message_partner_ids:
            for partner in self.message_partner_ids:
                if partner.user_ids:
                    users |= partner.user_ids

        # 3. 记录的负责人
        if hasattr(self, 'user_id') and self.user_id:
            users |= self.user_id

        # 4. 记录的多负责人（任务）
        if hasattr(self, 'user_ids') and self.user_ids:
            users |= self.user_ids

        # 5. 项目经理（项目相关）
        if hasattr(self, 'project_id') and self.project_id:
            if hasattr(self.project_id, 'user_id') and self.project_id.user_id:
                users |= self.project_id.user_id

        # 6. 作者（排除系统用户）
        if message.author_id and message.author_id.user_ids:
            author_users = message.author_id.user_ids
            # 排除系统用户
            if not self.env.ref('base.user_root', raise_if_not_found=False) or \
               author_users.id != self.env.ref('base.user_root').id:
                pass  # 不添加作者到通知列表

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

    def _build_note_card(self, message, clean_text):
        """
        构建美观的备注通知卡片（优化版）
        """
        # 获取记录信息
        record_name = self.display_name or '未命名'
        model_names = {
            'project.task': '项目任务',
            'project.project': '项目',
            'crm.lead': 'CRM线索',
            'res.partner': '联系人',
        }
        model_display = model_names.get(self._name, self._name)

        # 获取作者
        author_name = message.author_id.name if message.author_id else '系统'

        # 获取时间
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

        # 构建Odoo链接
        odoo_url = self._build_odoo_url()

        # 截断过长的文本（飞书限制）
        max_length = 1000
        if len(clean_text) > max_length:
            clean_text = clean_text[:max_length] + '...'

        # 构建卡片元素
        elements = []

        # 1. 记录名称
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**📝 {record_name}**"
            }
        })

        # 2. 分隔线
        elements.append({
            "tag": "hr"
        })

        # 3. 备注内容
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": clean_text
            }
        })

        # 4. 分隔线
        elements.append({
            "tag": "hr"
        })

        # 5. 操作人和时间
        elements.append({
            "tag": "note",
            "elements": [
                {
                    "tag": "plain_text",
                    "content": f"👤 {author_name} · 🕐 {timestamp}"
                }
            ]
        })

        # 6. 查看详情按钮
        if odoo_url and odoo_url != "#":
            elements.append({
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "🔗 查看详情"
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
                "template": "blue",
                "title": {
                    "tag": "plain_text",
                    "content": f"💬 {model_display} - 新备注"
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
            return "#"
        base_url = base_url.rstrip('/')
        return f"{base_url}/web?model={self._name}&id={self.id}&cids={self.env.company.id}&view_type=form"
