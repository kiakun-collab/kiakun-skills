"""抖音登录辅助：获取登录二维码。"""

from __future__ import annotations

import base64
import logging
import time
from pathlib import Path

from playwright.sync_api import Page

logger = logging.getLogger(__name__)

LOGIN_URL = "https://www.douyin.com/"


def check_login_status(page: Page) -> bool:
    """检查是否已登录。"""
    try:
        page.goto(LOGIN_URL, wait_until="networkidle", timeout=15000)
        time.sleep(2)
        # 抖音已登录时右上角会显示用户头像
        avatar_selectors = [
            '[data-e2e="user-avatar"]',
            '.avatar img',
            '[class*="avatar"] img',
        ]
        for sel in avatar_selectors:
            if page.locator(sel).count() > 0:
                logger.info("检测到已登录状态")
                return True
        return False
    except Exception as e:
        logger.debug("检查登录状态失败: %s", e)
        return False


def fetch_qrcode(page: Page) -> tuple[str | None, bool, str | None]:
    """
    获取登录二维码。
    返回: (qrcode_base64_or_path, already_logged_in, screenshot_path)
    screenshot_path 是登录弹窗的截图路径（供备用）
    """
    if check_login_status(page):
        return None, True, None

    # 点击登录按钮或等待二维码出现
    page.goto(LOGIN_URL, wait_until="networkidle", timeout=15000)
    time.sleep(3)

    # 尝试点击"登录"按钮触发二维码
    login_btn_selectors = [
        '[data-e2e="login-button"]',
        '.login-button',
        'text=登录',
        'text=Login',
        'xpath=//button[contains(text(), "登录")]',
    ]
    for sel in login_btn_selectors:
        try:
            btn = page.locator(sel).first
            if btn.count() > 0 and btn.is_visible(timeout=3000):
                btn.click()
                logger.info("点击登录按钮: %s", sel)
                time.sleep(3)
                break
        except Exception as e:
            logger.debug("点击登录按钮失败 %s: %s", sel, e)
            continue

    # 查找二维码图片
    qrcode_selectors = [
        '[data-e2e="qrcode-image"]',
        '.qrcode img',
        '[class*="qrcode"] img',
        'img[src*="qrcode"]',
        'img[alt*="二维码"]',
        'img[alt*="QR"]',
        'img[src*="byteimg.com"]',
    ]

    qrcode_src = None
    for sel in qrcode_selectors:
        try:
            img = page.locator(sel).first
            if img.count() > 0 and img.is_visible(timeout=5000):
                qrcode_src = img.get_attribute("src")
                if qrcode_src:
                    logger.info("找到二维码图片: %s", sel)
                    break
        except Exception:
            continue

    # 如果找到二维码，直接返回
    if qrcode_src:
        return qrcode_src, False, None

    # 如果没找到特定选择器，尝试截图整个登录弹窗区域
    logger.warning("未找到标准二维码，尝试截图登录区域")
    
    # 尝试定位登录弹窗
    modal_selectors = [
        '[data-e2e="login-modal"]',
        '.login-modal',
        '[class*="login-dialog"]',
        '[class*="login-modal"]',
        'div[role="dialog"]',
    ]
    
    modal_screenshot = None
    for sel in modal_selectors:
        try:
            modal = page.locator(sel).first
            if modal.count() > 0 and modal.is_visible(timeout=3000):
                # 截图弹窗元素
                modal_screenshot = "/tmp/douyin_login_modal.png"
                modal.screenshot(path=modal_screenshot)
                logger.info("已截取登录弹窗: %s", sel)
                break
        except Exception as e:
            logger.debug("截图弹窗失败 %s: %s", sel, e)
            continue
    
    if not modal_screenshot:
        # 最后尝试截图整个页面中心区域（通常是登录弹窗位置）
        try:
            page.screenshot(path="/tmp/douyin_login_page.png")
            modal_screenshot = "/tmp/douyin_login_page.png"
            logger.info("已截取整个页面")
        except Exception as e:
            logger.error("截图失败: %s", e)

    return None, False, modal_screenshot


def save_qrcode_to_file(src: str, save_path: str) -> str:
    """将二维码保存为文件。支持base64或URL。"""
    path = Path(save_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if src.startswith("data:image"):
        # base64 编码的图片
        base64_data = src.split(",")[1]
        path.write_bytes(base64.b64decode(base64_data))
    elif src.startswith("http"):
        # URL，需要下载
        import requests
        resp = requests.get(src, timeout=30)
        path.write_bytes(resp.content)
    else:
        raise ValueError(f"不支持的二维码格式: {src[:50]}")

    logger.info("二维码已保存: %s", save_path)
    return str(path.resolve())


def wait_for_login(page: Page, timeout: int = 120) -> bool:
    """等待用户扫码登录完成。"""
    logger.info("等待登录，超时时间: %d 秒", timeout)
    deadline = time.time() + timeout
    check_interval = 3

    while time.time() < deadline:
        if check_login_status(page):
            logger.info("登录成功")
            return True
        time.sleep(check_interval)

    logger.warning("登录超时")
    return False


def send_phone_code(page: Page, phone: str) -> bool:
    """
    发送手机验证码。
    返回 True 表示已发送，False 表示可能已登录或发送失败。
    """
    if check_login_status(page):
        logger.info("已登录，无需发送验证码")
        return False

    # 打开登录页
    page.goto(LOGIN_URL, wait_until="networkidle", timeout=15000)
    time.sleep(2)

    # 点击登录按钮
    login_btn_selectors = [
        '[data-e2e="login-button"]',
        '.login-button',
        'text=登录',
        'xpath=//button[contains(text(), "登录")]',
    ]
    for sel in login_btn_selectors:
        try:
            btn = page.locator(sel).first
            if btn.count() > 0 and btn.is_visible(timeout=3000):
                btn.click()
                logger.info("点击登录按钮: %s", sel)
                time.sleep(2)
                break
        except Exception:
            continue

    # 切换到手机号登录选项卡
    phone_tab_selectors = [
        'text=手机号登录',
        'text=手机登录',
        '[data-e2e="phone-login-tab"]',
        '.tab:has-text("手机")',
    ]
    for sel in phone_tab_selectors:
        try:
            tab = page.locator(sel).first
            if tab.count() > 0 and tab.is_visible(timeout=3000):
                tab.click()
                logger.info("切换到手机号登录: %s", sel)
                time.sleep(1)
                break
        except Exception:
            continue

    # 填写手机号
    phone_input_selectors = [
        '[data-e2e="phone-input"]',
        'input[type="tel"]',
        'input[placeholder*="手机号"]',
        'input[placeholder*="电话"]',
    ]
    phone_filled = False
    for sel in phone_input_selectors:
        try:
            inp = page.locator(sel).first
            if inp.count() > 0 and inp.is_visible(timeout=3000):
                inp.fill(phone)
                logger.info("填写手机号: %s", sel)
                phone_filled = True
                time.sleep(1)
                break
        except Exception as e:
            logger.debug("填写手机号失败 %s: %s", sel, e)
            continue

    if not phone_filled:
        logger.error("未找到手机号输入框")
        return False

    # 点击发送验证码按钮
    send_btn_selectors = [
        'text=获取验证码',
        'text=发送验证码',
        '[data-e2e="send-code-btn"]',
        'button:has-text("验证码")',
    ]
    for sel in send_btn_selectors:
        try:
            btn = page.locator(sel).first
            if btn.count() > 0 and btn.is_visible(timeout=3000):
                btn.click()
                logger.info("点击发送验证码: %s", sel)
                time.sleep(2)
                return True
        except Exception as e:
            logger.debug("点击发送验证码失败 %s: %s", sel, e)
            continue

    logger.error("未找到发送验证码按钮")
    return False


def submit_phone_code(page: Page, code: str) -> bool:
    """
    提交手机验证码完成登录。
    """
    # 填写验证码
    code_input_selectors = [
        '[data-e2e="code-input"]',
        'input[type="number"]',
        'input[placeholder*="验证码"]',
        'input[maxlength="6"]',
    ]
    code_filled = False
    for sel in code_input_selectors:
        try:
            inp = page.locator(sel).first
            if inp.count() > 0 and inp.is_visible(timeout=5000):
                inp.fill(code)
                logger.info("填写验证码: %s", sel)
                code_filled = True
                time.sleep(1)
                break
        except Exception as e:
            logger.debug("填写验证码失败 %s: %s", sel, e)
            continue

    if not code_filled:
        logger.error("未找到验证码输入框")
        return False

    # 点击登录/提交按钮
    submit_btn_selectors = [
        'text=登录',
        'text=确认',
        '[data-e2e="login-submit"]',
        'button[type="submit"]',
    ]
    for sel in submit_btn_selectors:
        try:
            btn = page.locator(sel).first
            if btn.count() > 0 and btn.is_visible(timeout=3000):
                btn.click()
                logger.info("点击登录按钮: %s", sel)
                time.sleep(3)
                break
        except Exception:
            continue

    # 检查是否登录成功
    return check_login_status(page)
