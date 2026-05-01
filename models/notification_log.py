# -*- coding: utf-8 -*-
"""
发送日志模型
记录每次飞书通知的发送结果
"""

import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class NotificationLog(models.Model):
    """飞书通知发送日志"""
    _name = 'notification.log'
    _description = 'Notification Send Log'
    _order = 'send_time desc'
    _rec_name = 'id'

    model_name = fields.Char(
        string='Model',
        required=True,
        index=True,
        help='Trigger model (e.g. hr.employee)'
    )
    record_id = fields.Integer(
        string='Record ID',
        index=True,
        help='ID of the record that triggered the notification'
    )
    event_type = fields.Char(
        string='Event Type',
        required=True,
        index=True,
        help='Event type: create, write, unlink, stage_change, assign'
    )
    recipient_open_id = fields.Char(
        string='Recipient Open ID',
        help='Feishu Open ID of the recipient'
    )
    recipient_name = fields.Char(
        string='Recipient Name',
        help='Display name of the recipient'
    )
    message_content = fields.Text(
        string='Message Content',
        help='Card message JSON content'
    )
    status = fields.Selection([
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ], string='Status', default='sent', required=True, index=True)
    error_message = fields.Text(
        string='Error Message',
        help='Error details if status is failed'
    )
    send_time = fields.Datetime(
        string='Send Time',
        default=fields.Datetime.now,
        required=True,
        index=True
    )

    @api.model
    def log_success(self, model_name, record_id, event_type, recipient_open_id,
                    recipient_name='', message_content=''):
        """记录成功发送"""
        return self.create({
            'model_name': model_name,
            'record_id': record_id,
            'event_type': event_type,
            'recipient_open_id': recipient_open_id,
            'recipient_name': recipient_name,
            'message_content': message_content,
            'status': 'sent',
            'send_time': fields.Datetime.now(),
        })

    @api.model
    def log_failure(self, model_name, record_id, event_type, recipient_open_id,
                    error_message='', recipient_name=''):
        """记录发送失败"""
        return self.create({
            'model_name': model_name,
            'record_id': record_id,
            'event_type': event_type,
            'recipient_open_id': recipient_open_id,
            'recipient_name': recipient_name,
            'status': 'failed',
            'error_message': error_message,
            'send_time': fields.Datetime.now(),
        })

    @api.model
    def log_skip(self, model_name, record_id, event_type, reason=''):
        """记录跳过（未发送）"""
        return self.create({
            'model_name': model_name,
            'record_id': record_id,
            'event_type': event_type,
            'recipient_open_id': '',
            'status': 'skipped',
            'error_message': reason,
            'send_time': fields.Datetime.now(),
        })
