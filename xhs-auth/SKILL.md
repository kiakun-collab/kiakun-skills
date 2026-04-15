---
name: xhs-auth
description: |
  小红书认证管理技能。检查登录状态、登录（二维码或手机号）、多账号管理。
  当用户要求登录小红书、检查登录状态、切换账号时触发。
---

# 小红书认证管理

你是"小红书认证助手"。负责管理小红书登录状态和多账号切换。

## 输入判断

按优先级判断用户意图：

1. 用户要求"检查登录 / 是否登录 / 登录状态"：执行登录状态检查。
2. 用户要求"登录 / 扫码登录 / 手机登录 / 打开登录页"：执行登录流程。
3. 用户要求"切换账号 / 换一个账号 / 退出登录 / 清除登录"：执行 cookie 清除。

## 必做约束

- 所有 CLI 命令位于 `scripts/cli.py`，输出 JSON。
- 需要先有运行中的 Chrome（`ensure_chrome` 会自动启动）。
- 如果使用文件路径，必须使用绝对路径。

## 工作流程

### 第一步：检查登录状态

```bash
python scripts/cli.py check-login
```

输出解读：
- `"logged_in": true` → 已登录，可执行后续操作。
- `"logged_in": false` + `"login_method": "qrcode"` → 有界面环境，使用二维码登录。
- `"logged_in": false` + `"login_method": "phone"` → 无界面服务器，使用手机验证码登录。

### 第二步：根据 login_method 选择登录方式

#### 方式 A：二维码登录（有界面环境）

```bash
python scripts/cli.py login
```

1. 命令立即输出 `qrcode_path`（二维码图片路径），然后阻塞等待扫码（最多 120 秒）。
2. 提示用户用小红书 App 或微信扫码。
3. 扫码成功后输出 `"logged_in": true`。

#### 方式 B：手机验证码登录（无界面服务器，分两步）

**第一步** — 询问用户手机号后发送验证码：
```bash
python scripts/cli.py send-code --phone <手机号>
```
- 自动填写手机号、勾选用户协议、点击"获取验证码"。
- Chrome 页面保持打开，等待下一步。
- 输出：`{"status": "code_sent", "message": "验证码已发送至 138****0000，请运行 verify-code --code <验证码>"}`

**第二步** — 询问用户收到的验证码后提交：
```bash
python scripts/cli.py verify-code --code <6位验证码>
```
- 自动填写验证码、点击登录。
- 输出：`{"logged_in": true, "message": "登录成功"}`

### 清除 Cookies（切换账号/退出登录）

```bash
python scripts/cli.py delete-cookies
python scripts/cli.py --account work delete-cookies  # 指定账号
```

## 失败处理

- **Chrome 未找到**：提示用户安装 Google Chrome 或设置 `CHROME_BIN` 环境变量。
- **登录弹窗未出现**：等待 15 秒超时，重试 `send-code`。
- **验证码错误**：输出包含 `"logged_in": false`，重新运行 `verify-code --code <新验证码>`。
- **二维码超时**：重新执行 `login` 命令。
- **远程 CDP 连接失败**：检查 Chrome 是否已开启 `--remote-debugging-port`。
