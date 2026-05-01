# -*- coding: utf-8 -*-

import logging
from odoo import models, api, fields, _

_logger = logging.getLogger(__name__)


class AccountAnalyticLine(models.Model):
    """
    扩展工时单模型（account.analytic.line），添加飞书通知功能
    """
    _inherit = 'account.analytic.line'

    @api.model_create_multi
    def create(self, vals_list):
        """新建工时单时发送通知"""
        timesheets = super(AccountAnalyticLine, self).create(vals_list)
        
        for timesheet in timesheets:
            try:
                if not timesheet.task_id:
                    continue
                
                notify_users = timesheet.task_id.user_ids
                if timesheet.user_id and timesheet.user_id in notify_users:
                    notify_users = notify_users - timesheet.user_id
                
                if timesheet.project_id and timesheet.project_id.user_id:
                    if timesheet.project_id.user_id not in notify_users:
                        if timesheet.project_id.user_id != timesheet.user_id:
                            notify_users |= timesheet.project_id.user_id
                
                if notify_users:
                    employee_name = timesheet.employee_id.name if timesheet.employee_id else timesheet.user_id.name
                    custom_message = _("%(employee)s 在任务【%(task)s】填报了 %(hours).2f 小时") % {
                        'employee': employee_name,
                        'task': timesheet.task_id.name,
                        'hours': timesheet.unit_amount
                    }
                    
                    self.env['lark.notifier'].notify_business_event(
                        record=timesheet,
                        event_type='create',
                        notify_users=notify_users,
                        custom_message=custom_message
                    )
            except Exception as e:
                _logger.error(f"Failed to send notification for new timesheet {timesheet.id}: {e}")
        
        return timesheets

    def write(self, vals):
        """工时单修改时发送通知"""
        track_fields = ['unit_amount', 'date', 'task_id', 'project_id']
        tracked_timesheets = []
        
        if any(field in vals for field in track_fields):
            for ts in self:
                if ts.task_id:
                    tracked_timesheets.append({
                        'id': ts.id,
                        'old_hours': ts.unit_amount,
                        'old_date': ts.date,
                        'old_task': ts.task_id,
                        'old_project': ts.project_id,
                        'timesheet': ts
                    })
        
        result = super(AccountAnalyticLine, self).write(vals)
        
        try:
            for info in tracked_timesheets:
                ts = info['timesheet']
                if not ts.exists() or not ts.task_id:
                    continue
                
                changes = {}
                custom_parts = []
                
                if 'unit_amount' in vals:
                    old_val = info['old_hours']
                    new_val = ts.unit_amount
                    if abs(new_val - old_val) >= 0.01:
                        changes['unit_amount'] = f"{old_val:.2f}h → {new_val:.2f}h"
                        custom_parts.append(f"工时从 {old_val:.2f}h 改为 {new_val:.2f}h")
                
                if 'date' in vals:
                    old_val = info['old_date']
                    new_val = ts.date
                    if old_val != new_val:
                        old_str = old_val.strftime('%Y-%m-%d') if old_val else _('未设置')
                        new_str = new_val.strftime('%Y-%m-%d') if new_val else _('未设置')
                        changes['date'] = f"{old_str} → {new_str}"
                        custom_parts.append(f"日期从 {old_str} 改为 {new_str}")
                
                if 'task_id' in vals:
                    old_val = info['old_task']
                    new_val = ts.task_id
                    if old_val != new_val:
                        changes['task_id'] = f"{old_val.name} → {new_val.name}"
                        custom_parts.append(f"任务从【{old_val.name}】改为【{new_val.name}】")
                
                if changes:
                    notify_users = ts.task_id.user_ids
                    if ts.user_id and ts.user_id in notify_users:
                        notify_users = notify_users - ts.user_id
                    
                    if ts.project_id and ts.project_id.user_id:
                        if ts.project_id.user_id not in notify_users and ts.project_id.user_id != ts.user_id:
                            notify_users |= ts.project_id.user_id
                    
                    if notify_users:
                        employee_name = ts.employee_id.name if ts.employee_id else ts.user_id.name
                        custom_message = _("%(employee)s 修改了任务【%(task)s】的工时：%(changes)s") % {
                            'employee': employee_name,
                            'task': ts.task_id.name,
                            'changes': '，'.join(custom_parts)
                        }
                        
                        self.env['lark.notifier'].notify_business_event(
                            record=ts,
                            event_type='write',
                            notify_users=notify_users,
                            changes=changes,
                            custom_message=custom_message
                        )
        except Exception as e:
            _logger.error(f"Error sending notification for timesheet update: {e}")
        
        return result

    def unlink(self):
        """删除工时单时发送通知"""
        delete_info = []
        for ts in self:
            if ts.task_id:
                delete_info.append({
                    'employee_name': ts.employee_id.name if ts.employee_id else ts.user_id.name,
                    'task_name': ts.task_id.name,
                    'hours': ts.unit_amount,
                    'notify_users': ts.task_id.user_ids.filtered(lambda u: u != ts.user_id)
                })
        
        result = super(AccountAnalyticLine, self).unlink()
        
        try:
            for info in delete_info:
                if info['notify_users']:
                    custom_message = _("%(employee)s 删除了任务【%(task)s】的工时记录：%(hours).2f 小时") % {
                        'employee': info['employee_name'],
                        'task': info['task_name'],
                        'hours': info['hours']
                    }
                    self.env['lark.notifier'].sudo().notify_business_event(
                        record=None,
                        event_type='unlink',
                        notify_users=info['notify_users'],
                        custom_message=custom_message
                    )
        except Exception as e:
            _logger.error(f"Error sending notification for timesheet delete: {e}")
        
        return result