# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, _
from odoo.exceptions import UserError
import requests

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = 'res.company'

    lark_app_id = fields.Char(string='Lark App ID', help='Lark application App ID')
    lark_app_secret = fields.Char(string='Lark App Secret', help='Lark application App Secret')
    lark_notify_enabled = fields.Boolean(string='Enable Lark Notifications', default=False, help='Enable Lark message push notifications')
    lark_notify_odoo_url = fields.Char(string='Odoo URL', help='Public URL of Odoo for generating jump links')

    def action_test_lark_connection(self):
        """测试飞书连接 - 使用HTTP请求直接调用飞书API"""
        self.ensure_one()
        
        if not self.lark_app_id or not self.lark_app_secret:
            raise UserError(_('Please fill in Lark App ID and App Secret first'))

        try:
            # 使用HTTP请求获取tenant_access_token
            url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            data = {
                "app_id": self.lark_app_id,
                "app_secret": self.lark_app_secret
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('code') == 0:
                    # 连接成功
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Test Successful'),
                            'message': _('Lark connection successful! App ID and App Secret verified.'),
                            'type': 'success',
                            'sticky': False,
                        }
                    }
                else:
                    # API返回错误
                    error_msg = result.get('msg', 'Unknown error')
                    raise UserError(_('Test failed: %s') % error_msg)
            else:
                # HTTP请求失败
                raise UserError(_('Test failed: HTTP error %s') % response.status_code)
                
        except requests.exceptions.Timeout:
            raise UserError(_('Test failed: Connection timeout. Please check network.'))
        except requests.exceptions.ConnectionError:
            raise UserError(_('Test failed: Network connection failed. Please check server network.'))
        except ImportError:
            raise UserError(_('Please ensure requests library is installed'))
        except Exception as e:
            _logger.error(f"Lark connection test failed: {e}", exc_info=True)
            error_msg = str(e)
            
            # 友好的错误提示
            if 'invalid app_id or app_secret' in error_msg.lower():
                error_msg = _('Invalid App ID or App Secret')
            elif 'network' in error_msg.lower() or 'timeout' in error_msg.lower():
                error_msg = _('Network connection failed, please check server network')
                
            raise UserError(_('Test failed: %s') % error_msg)
