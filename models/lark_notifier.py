# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LarkNotifier(models.AbstractModel):
    """
    飞书业务事件通知工具类
    提供统一的通知发送接口，支持三级开关控制
    """
    _name = 'lark.notifier'
    _description = 'Lark Business Event Notifier'
    
    # 事件类型定义
    EVENT_TYPES = [
        ('create', _('新建')),
        ('write', _('修改')),
        ('unlink', _('删除')),
        ('assign', _('分配')),
        ('stage_change', _('阶段变更')),
        ('amount_change', _('金额变更')),
        ('deadline_change', _('截止日变更')),
        ('complete', _('完成')),
        ('close', _('关闭')),
    ]
    
    # 模块名称映射
    MODEL_MODULES = {
        'res.partner': 'contact',
        'crm.lead': 'crm',
        'project.project': 'project',
        'project.task': 'project',
        'account.analytic.line': 'timesheet',
    }
    
    # 业务类型显示名称
    MODEL_NAMES = {
        'res.partner': _('联系人'),
        'crm.lead': _('CRM线索'),
        'project.project': _('项目'),
        'project.task': _('项目任务'),
        'account.analytic.line': _('工时单'),
    }

    def notify_business_event(self, record, event_type, notify_users=None, 
                              changes=None, custom_message=None):
        """
        发送业务事件通知
        
        :param record: 触发事件的记录 (single recordset)
        :param event_type: 事件类型 (create/write/assign/stage_change...)
        :param notify_users: 需要通知的用户记录集 (res.users)
        :param changes: 变更的字段字典 {field_name: new_value}
        :param custom_message: 自定义消息内容
        :return: 发送结果 (bool)
        """
        try:
            # 1. 参数校验
            if not record or not record.exists():
                _logger.warning("Lark notification skipped: record is empty or deleted")
                return False
            
            if not event_type:
                _logger.warning("Lark notification skipped: event_type is required")
                return False
            
            # 2. 检查是否应该发送通知
            if not self._should_notify(record, event_type):
                return False
            
            # 3. 确定通知对象
            if notify_users is None:
                notify_users = self._get_default_notify_users(record, event_type)
            
            if not notify_users:
                _logger.debug(f"No users to notify for {record._name} {event_type}")
                return False
            
            # 4. 过滤未开启飞书通知的用户
            notify_users = notify_users.filtered(lambda u: u.notify_by_lark)
            if not notify_users:
                _logger.debug("All users have disabled Lark notifications")
                return False
            
            # 5. 获取用户的飞书Open ID
            open_ids = self._get_user_open_ids(notify_users)
            if not open_ids:
                _logger.warning("No valid Lark Open IDs found for notification")
                return False
            
            # 6. 构建消息卡片
            card_message = self._build_card_message(
                record, event_type, changes, custom_message
            )
            
            # 7. 发送消息
            return self._send_notification(open_ids, card_message, record)
            
        except Exception as e:
            _logger.error(f"Error in notify_business_event: {e}", exc_info=True)
            # 降级：记录失败但不阻断业务
            self._log_notification_error(record, event_type, str(e))
            return False

    def _should_notify(self, record, event_type):
        """
        检查是否应该发送通知（三级开关）
        """
        company = self.env.company
        model_name = record._name
        
        # 1. 检查模块级开关
        module_key = self.MODEL_MODULES.get(model_name)
        if module_key:
            module_enabled = getattr(company, f'lark_notify_{module_key}', True)
            if not module_enabled:
                _logger.debug(f"Module {module_key} notification is disabled")
                return False
        
        # 2. 检查事件类型开关
        event_enabled = getattr(company, f'lark_notify_event_{event_type}', True)
        if not event_enabled:
            _logger.debug(f"Event type {event_type} notification is disabled")
            return False
        
        # 3. 检查全局开关
        if not company.lark_notify_enabled:
            _logger.debug("Global Lark notification is disabled")
            return False
        
        return True

    def _get_default_notify_users(self, record, event_type):
        """
        获取默认的通知对象
        子类可以重写此方法自定义通知对象
        """
        users = self.env['res.users']
        
        # 负责人/指派给
        if hasattr(record, 'user_id') and record.user_id:
            users |= record.user_id
        
        # 多负责人（任务）
        if hasattr(record, 'user_ids') and record.user_ids:
            users |= record.user_ids
        
        # 创建者
        if hasattr(record, 'create_uid') and record.create_uid:
            users |= record.create_uid
        
        # 项目经理（项目相关）
        if hasattr(record, 'project_id') and record.project_id:
            if hasattr(record.project_id, 'user_id') and record.project_id.user_id:
                users |= record.project_id.user_id
        
        return users

    def _get_user_open_ids(self, users):
        """
        获取用户的飞书Open ID列表
        """
        open_ids = []
        for user in users:
            # 通过employee获取open_id
            if user.employee_id and user.employee_id.lark_open_id:
                open_ids.append(user.employee_id.lark_open_id)
            else:
                _logger.warning(f"User {user.name} has no Lark Open ID configured")
        return open_ids

    def _build_card_message(self, record, event_type, changes, custom_message):
        """
        构建飞书卡片消息
        """
        model_name = record._name
        record_name = record.display_name or _('未命名')
        model_display = self.MODEL_NAMES.get(model_name, model_name)
        event_display = dict(self.EVENT_TYPES).get(event_type, event_type)
        
        # 获取当前用户和操作时间
        current_user = self.env.user.name
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 构建变更详情
        changes_text = ""
        if changes and isinstance(changes, dict):
            change_items = []
            for field, value in changes.items():
                field_label = record._fields.get(field, {}).string if hasattr(record._fields.get(field), 'string') else field
                change_items.append(f"{field_label}: {value}")
            if change_items:
                changes_text = "\\n".join(change_items)
        
        # 自定义消息
        message_text = custom_message or ""
        
        # 构建Odoo跳转链接
        odoo_url = self._build_odoo_url(record)
        
        # 构建卡片内容
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": self._get_event_color(event_type),
                "title": {
                    "tag": "plain_text",
                    "content": f"📋 {model_display} {event_display}"
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**📝 标题：** {record_name}"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**👤 操作人：** {current_user}"
                    }
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**⏰ 时间：** {timestamp}"
                    }
                }
            ]
        }
        
        # 添加变更详情（如果有）
        if changes_text:
            card["elements"].append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**📊 变更：**\\n{changes_text}"
                }
            })
        
        # 添加自定义消息（如果有）
        if message_text:
            card["elements"].append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**💬 备注：** {message_text}"
                }
            })
        
        # 添加分隔线
        card["elements"].append({
            "tag": "hr"
        })
        
        # 添加操作按钮
        card["elements"].append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {
                        "tag": "plain_text",
                        "content": "🔗 打开 Odoo 处理"
                    },
                    "type": "primary",
                    "url": odoo_url
                }
            ]
        })
        
        return card

    def _get_event_color(self, event_type):
        """
        根据事件类型返回卡片颜色
        """
        colors = {
            'create': 'green',      # 新建 - 绿色
            'write': 'blue',        # 修改 - 蓝色
            'unlink': 'red',        # 删除 - 红色
            'assign': 'orange',     # 分配 - 橙色
            'stage_change': 'blue', # 阶段变更 - 蓝色
            'amount_change': 'yellow', # 金额变更 - 黄色
            'deadline_change': 'purple', # 截止日变更 - 紫色
            'complete': 'green',    # 完成 - 绿色
            'close': 'grey',        # 关闭 - 灰色
        }
        return colors.get(event_type, 'blue')

    def _build_odoo_url(self, record):
        """
        构建Odoo记录跳转链接
        """
        company = self.env.company
        base_url = company.lark_notify_odoo_url or self._get_default_base_url()
        
        if not base_url:
            return "#"
        
        # 移除末尾的斜杠
        base_url = base_url.rstrip('/')
        
        return f"{base_url}/web#id={record.id}&model={record._name}&view_type=form"

    def _get_default_base_url(self):
        """
        获取默认的Odoo基础URL
        """
        # 从系统参数获取
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return base_url

    def _send_notification(self, open_ids, card_message, record):
        """
        发送飞书通知
        """
        try:
            # 获取mommy_lark的消息发送工具
            message_tool = self.env['lark.message']
            
            # 发送给每个用户
            success_count = 0
            for open_id in open_ids:
                try:
                    # 调用mommy_lark的发送方法
                    result = message_tool.send_message(
                        receive_id=open_id,
                        receive_id_type='open_id',
                        content=card_message,
                        msg_type='interactive'
                    )
                    if result:
                        success_count += 1
                except Exception as e:
                    _logger.error(f"Failed to send message to {open_id}: {e}")
            
            # 记录日志
            self._log_notification_success(record, len(open_ids), success_count)
            
            return success_count > 0
            
        except Exception as e:
            _logger.error(f"Error sending Lark notification: {e}", exc_info=True)
            return False

    def _log_notification_success(self, record, total_count, success_count):
        """
        记录通知成功日志
        """
        _logger.info(
            f"Lark notification sent for {record._name}:{record.id} - "
            f"{success_count}/{total_count} success"
        )

    def _log_notification_error(self, record, event_type, error_msg):
        """
        记录通知错误日志
        """
        _logger.error(
            f"Lark notification failed for {record._name}:{record.id} "
            f"event={event_type} error={error_msg}"
        )