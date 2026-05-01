# -*- coding: utf-8 -*-
"""
飞书消息发送工具
使用HTTP请求直接调用飞书API
Token 持久化到 ir.config_parameter
"""

import logging
import json
import time
import requests
from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TOKEN_KEY = 'gtu_notify.token_value'
TOKEN_EXPIRY_KEY = 'gtu_notify.token_expires_at'


class LarkMessageSender:
    """
    飞书消息发送工具类
    Token 持久化到 ir.config_parameter，跨 Worker 重启共享
    """

    def __init__(self, app_id, app_secret, env=None):
        self.app_id = app_id
        self.app_secret = app_secret
        self.env = env

    def get_tenant_access_token(self):
        """
        获取 tenant_access_token
        优先读数据库缓存，过期则刷新
        """
        if self.env:
            ICP = self.env['ir.config_parameter'].sudo()
            cached_token = ICP.get_param(TOKEN_KEY)
            expires_at = ICP.get_param(TOKEN_EXPIRY_KEY)

            if cached_token and expires_at:
                try:
                    if time.time() < float(expires_at) - 60:  # 提前 60s 刷新
                        return cached_token
                except (ValueError, TypeError):
                    pass  # 过期时间解析失败，重新获取

        # 缓存未命中或已过期，请求新 token
        try:
            url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            headers = {"Content-Type": "application/json"}
            data = {"app_id": self.app_id, "app_secret": self.app_secret}

            response = requests.post(url, headers=headers, json=data, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    token = result.get('tenant_access_token')
                    expire = result.get('expire', 7200)

                    # 持久化到数据库
                    if self.env:
                        ICP = self.env['ir.config_parameter'].sudo()
                        ICP.set_param(TOKEN_KEY, token)
                        ICP.set_param(TOKEN_EXPIRY_KEY, str(time.time() + expire))
                        _logger.debug("Token cached to ir.config_parameter")

                    return token
                else:
                    _logger.error(f"Failed to get tenant_access_token: {result.get('msg')}")
                    return None
            else:
                _logger.error(f"HTTP error getting token: {response.status_code}")
                return None

        except Exception as e:
            _logger.error(f"Exception getting tenant_access_token: {e}", exc_info=True)
            return None

    def send_card_message(self, open_id, card_message):
        """
        发送卡片消息

        :param open_id: 接收者的 open_id
        :param card_message: 卡片消息字典
        :return: 是否成功
        """
        try:
            access_token = self.get_tenant_access_token()
            if not access_token:
                _logger.error("Failed to get access token")
                return False

            url = "https://open.feishu.cn/open-apis/im/v1/messages"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            params = {"receive_id_type": "open_id"}
            data = {
                "receive_id": open_id,
                "msg_type": "interactive",
                "content": json.dumps(card_message)
            }

            response = requests.post(url, headers=headers, params=params, json=data, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get('code') == 0:
                    _logger.info(f"Successfully sent message to {open_id}")
                    return True
                else:
                    _logger.error(f"Failed to send message: {result.get('msg')}")
                    return False
            else:
                _logger.error(f"HTTP error sending message: {response.status_code}")
                return False

        except Exception as e:
            _logger.error(f"Exception sending message: {e}", exc_info=True)
            return False

    def send_card_messages(self, open_ids, card_message):
        """
        批量发送卡片消息
        """
        success_count = 0
        for open_id in open_ids:
            if self.send_card_message(open_id, card_message):
                success_count += 1
        return success_count


def send_lark_notification(env, open_ids, card_message):
    """
    发送飞书通知的便捷函数

    :param env: Odoo 环境
    :param open_ids: 接收者的 open_id 列表
    :param card_message: 卡片消息字典
    :return: 是否成功
    """
    try:
        company = env.company
        if not company.lark_notify_enabled:
            _logger.debug("Lark notification is disabled")
            return False

        if not company.lark_app_id or not company.lark_app_secret:
            _logger.warning("Lark App ID or App Secret is not configured")
            return False

        sender = LarkMessageSender(company.lark_app_id, company.lark_app_secret, env=env)
        success_count = sender.send_card_messages(open_ids, card_message)
        return success_count > 0

    except Exception as e:
        _logger.error(f"Error sending Lark notification: {e}", exc_info=True)
        return False
