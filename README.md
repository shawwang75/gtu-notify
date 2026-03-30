# GTU Notify - Lark Business Notifications for Odoo

**GTU Notify** is a powerful Odoo module that automatically pushes business notifications to Lark (Feishu), helping teams stay informed about critical business events in real-time.

## 🚀 Key Features

### Business Event Notifications
- **CRM**: Lead creation, assignment, stage changes, amount updates, closure
- **Projects**: Project creation, task assignment, status changes, deadline updates, completion
- **Timesheets**: Creation, updates, deletion

### Notification Control
- Three-level notification switches (global/module/event)
- User-level notification preferences
- Rich message cards with direct links to Odoo

### Technical Advantages
- ✅ Fully standalone, zero dependencies
- ✅ No other Lark modules required
- ✅ Lark App configuration management
- ✅ Employee Lark account binding
- ✅ Automatic token refresh mechanism
- ✅ Fail-safe design, won't break business operations
- ✅ Fully based on Odoo standard inheritance, zero source code modification

## 📦 Installation

1. Download this module
2. Place it in your Odoo addons directory
3. Update the addons list
4. Install the module
5. Configure your Lark App credentials
6. Bind employee Lark accounts
7. Enable notifications

## ⚙️ Configuration

### 1. Create a Lark App
- Go to [Lark Developer Console](https://open.feishu.cn/app)
- Create a new app
- Get App ID and App Secret

### 2. Configure in Odoo
- Navigate to **Settings → GTU Notify → Lark Configuration**
- Enter your App ID and App Secret
- Test the connection

### 3. Bind Employee Lark Accounts
- Go to **Employees**
- Edit each employee
- Fill in their Lark Open ID or Phone Number

### 4. Enable Notifications
- Navigate to **Settings → GTU Notify → Notification Configuration**
- Enable notifications for specific events

## 📋 Supported Events

| Module | Events |
|--------|--------|
| CRM Lead | Created, Assigned, Stage Changed, Closed |
| Project Task | Assigned, Status Changed, Deadline Updated, Completed |
| Timesheet | Created, Modified, Deleted |

## 💰 Pricing

**€59** (One-time purchase)

Includes:
- Unlimited usage
- All future updates
- Email support

## 🆘 Support

- **Email**: support@gtucloud.com
- **Website**: https://www.gtucloud.com

## 📄 License

OPL-1 (Odoo Proprietary License v1.0)

## 👥 Author

**上海逸广信息科技有限公司**  
Shanghai Yiguang Information Technology Co., Ltd.

---

**Made with ❤️ by GTU Cloud**
