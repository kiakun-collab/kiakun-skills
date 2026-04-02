"""统一 CLI 入口。输出 JSON（ensure_ascii=False）。"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

_script_dir = os.path.dirname(os.path.abspath(__file__))
if _script_dir not in sys.path:
    sys.path.insert(0, _script_dir)

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("dy-research-cli")


def _output(data: dict, exit_code: int = 0) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


def _load_meta_dict(value: str | None) -> dict | None:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        _output({"success": False, "error": f"meta 参数不是有效 JSON: {e}"}, exit_code=2)


# ========== 子命令 ==========


def cmd_session_create(args: argparse.Namespace) -> None:
    from session_manager import create_session

    meta = _load_meta_dict(args.meta)
    session_id = create_session(name=args.name, game=args.game, meta=meta)
    import session_manager as sm
    data_dir = sm.get_session_dir(session_id)
    _output({
        "success": True,
        "session_id": session_id,
        "data_dir": str(data_dir.resolve()),
    })


def cmd_session_list(_args: argparse.Namespace) -> None:
    from session_manager import list_sessions
    sessions = list_sessions()
    _output({"sessions": sessions, "count": len(sessions)})


def cmd_session_show(args: argparse.Namespace) -> None:
    from session_manager import load_meta, load_records, get_session_dir
    try:
        meta = load_meta(args.session_id)
        records = load_records(args.session_id)
        _output({
            "session_id": args.session_id,
            "meta": meta,
            "records_count": len(records),
            "data_dir": str(get_session_dir(args.session_id).resolve()),
        })
    except FileNotFoundError as e:
        _output({"success": False, "error": str(e)}, exit_code=2)


def cmd_explore(args: argparse.Namespace) -> None:
    from session_manager import get_session_dir, next_screenshot_path, append_record
    from dy.browser import DouyinBrowser

    session_dir = get_session_dir(args.session_id)
    if not session_dir.exists():
        _output({"success": False, "error": f"Session {args.session_id} not found"}, exit_code=2)

    screenshot_path = next_screenshot_path(args.session_id, "search")
    browser = DouyinBrowser(
        headless=args.headless,
        connect_cdp=args.cdp,
    )
    try:
        browser.connect()
        result = browser.search(args.keyword, str(screenshot_path))

        # 保存记录
        record = {
            "type": "explore",
            "keyword": args.keyword,
            "screenshots": result.screenshots,
            "creators": [c.model_dump() for c in result.creators[:args.max_results]],
        }
        append_record(args.session_id, record)

        _output({
            "success": True,
            "session_id": args.session_id,
            "keyword": args.keyword,
            "screenshots": result.screenshots,
            "creators": [c.model_dump() for c in result.creators[:args.max_results]],
        })
    except Exception as e:
        logger.exception("explore 失败")
        _output({"success": False, "error": str(e)}, exit_code=2)
    finally:
        browser.close()


def cmd_research(args: argparse.Namespace) -> None:
    from session_manager import get_session_dir, append_record
    from dy.browser import DouyinBrowser

    session_dir = get_session_dir(args.session_id)
    if not session_dir.exists():
        _output({"success": False, "error": f"Session {args.session_id} not found"}, exit_code=2)

    import session_manager as sm
    homepage_shot = sm.next_screenshot_path(args.session_id, f"homepage_{args.session_id}")
    video_prefix = str(session_dir / f"video_{args.session_id}")

    browser = DouyinBrowser(
        headless=args.headless,
        connect_cdp=args.cdp,
    )
    try:
        browser.connect()
        snapshot = browser.open_profile(
            url=args.url,
            homepage_screenshot_path=str(homepage_shot),
            max_videos=args.videos,
            video_screenshot_prefix=video_prefix,
        )

        record = {
            "type": "research",
            "url": args.url,
            "snapshot": snapshot.model_dump(),
        }
        append_record(args.session_id, record)

        _output({
            "success": True,
            "session_id": args.session_id,
            "creator": snapshot.model_dump(),
        })
    except Exception as e:
        logger.exception("research 失败")
        _output({"success": False, "error": str(e)}, exit_code=2)
    finally:
        browser.close()


def cmd_login(args: argparse.Namespace) -> None:
    """获取抖音登录二维码并等待扫码。"""
    from dy.login import fetch_qrcode, save_qrcode_to_file
    from dy.browser import DouyinBrowser

    browser = DouyinBrowser(headless=args.headless)
    try:
        browser.connect()
        
        # 获取二维码或登录弹窗截图
        src, already, screenshot_path = fetch_qrcode(browser.page)
        if already:
            _output({"success": True, "logged_in": True, "message": "已登录"})
            return

        qrcode_path = args.output or "/tmp/douyin_qrcode.png"
        
        if src:
            # 保存二维码图片
            save_qrcode_to_file(src, qrcode_path)
            _output({
                "success": True,
                "logged_in": False,
                "qrcode_path": qrcode_path,
                "qrcode_type": "image",
                "message": "请使用抖音APP扫码登录，二维码有效期约3分钟",
            })
        elif screenshot_path:
            # 返回登录弹窗截图
            _output({
                "success": True,
                "logged_in": False,
                "qrcode_path": screenshot_path,
                "qrcode_type": "screenshot",
                "message": "请查看截图中的二维码，使用抖音APP扫码登录",
            })
        else:
            _output({"success": False, "error": "未找到登录二维码或弹窗"}, exit_code=2)
    except Exception as e:
        logger.exception("获取二维码失败")
        _output({"success": False, "error": str(e)}, exit_code=2)
    finally:
        browser.close()


def cmd_check_login(args: argparse.Namespace) -> None:
    """检查抖音登录状态。"""
    from dy.login import check_login_status
    from dy.browser import DouyinBrowser

    browser = DouyinBrowser(headless=args.headless)
    try:
        browser.connect()
        logged_in = check_login_status(browser.page)
        _output({"success": True, "logged_in": logged_in})
    except Exception as e:
        logger.exception("检查登录状态失败")
        _output({"success": False, "error": str(e)}, exit_code=2)
    finally:
        browser.close()


def cmd_send_code(args: argparse.Namespace) -> None:
    """发送手机验证码。"""
    from dy.login import send_phone_code
    from dy.browser import DouyinBrowser

    browser = DouyinBrowser(headless=args.headless)
    try:
        browser.connect()
        sent = send_phone_code(browser.page, args.phone)
        if sent:
            _output({
                "success": True,
                "phone": args.phone,
                "message": f"验证码已发送至 {args.phone[:3]}****{args.phone[-4:]}",
                "next_step": "请使用 verify-code --code <验证码> 提交验证码",
            })
        else:
            _output({
                "success": False,
                "error": "发送验证码失败，可能已登录或页面结构变化",
            }, exit_code=2)
    except Exception as e:
        logger.exception("发送验证码失败")
        _output({"success": False, "error": str(e)}, exit_code=2)
    finally:
        browser.close()


def cmd_verify_code(args: argparse.Namespace) -> None:
    """提交手机验证码完成登录。"""
    from dy.login import submit_phone_code
    from dy.browser import DouyinBrowser

    browser = DouyinBrowser(headless=args.headless)
    try:
        browser.connect()
        success = submit_phone_code(browser.page, args.code)
        if success:
            _output({
                "success": True,
                "logged_in": True,
                "message": "登录成功",
            })
        else:
            _output({
                "success": False,
                "error": "登录失败，验证码错误或已过期",
            }, exit_code=2)
    except Exception as e:
        logger.exception("验证验证码失败")
        _output({"success": False, "error": str(e)}, exit_code=2)
    finally:
        browser.close()


def cmd_start_chrome(args: argparse.Namespace) -> None:
    """启动带远程调试的 Chrome（供 VNC 环境使用）。"""
    import subprocess
    import os
    
    # 确保 DISPLAY 环境变量设置
    env = os.environ.copy()
    env["DISPLAY"] = args.display
    
    # Chrome 启动参数
    chrome_cmd = [
        "/usr/bin/google-chrome",
        f"--remote-debugging-port={args.port}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-features=TranslateUI",
        "--disable-features=IsolateOrigins,site-per-process",
    ]
    
    try:
        # 后台启动 Chrome
        subprocess.Popen(
            chrome_cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _output({
            "success": True,
            "message": f"Chrome 已启动，远程调试端口: {args.port}",
            "cdp_url": f"http://localhost:{args.port}",
            "instructions": [
                "1. 在 VNC 中完成滑块验证并登录抖音",
                "2. 保持 Chrome 打开",
                "3. 运行自动化命令时添加 --cdp 参数",
            ],
        })
    except Exception as e:
        _output({"success": False, "error": str(e)}, exit_code=2)


def cmd_report(args: argparse.Namespace) -> None:
    # 最小闭环先不实现 report，返回占位信息
    _output({
        "success": True,
        "message": "report 命令在最小闭环中尚未实现，请先使用 explore + research",
        "session_id": args.session_id,
    })


# ========== 参数解析 ==========


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dy-research-cli", description="抖音达人研究 CLI")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # session create
    sub = subparsers.add_parser("session-create", help="创建研究会话")
    sub.add_argument("--name", required=True, help="研究名称")
    sub.add_argument("--game", required=True, help="游戏/项目名称")
    sub.add_argument("--meta", default="", help="附加元数据 JSON 字符串")
    sub.set_defaults(func=cmd_session_create)

    # session list
    sub = subparsers.add_parser("session-list", help="列出现有会话")
    sub.set_defaults(func=cmd_session_list)

    # session show
    sub = subparsers.add_parser("session-show", help="查看会话详情")
    sub.add_argument("--session-id", required=True, help="会话 ID")
    sub.set_defaults(func=cmd_session_show)

    # explore
    sub = subparsers.add_parser("explore", help="搜索达人")
    sub.add_argument("--keyword", required=True, help="搜索关键词")
    sub.add_argument("--session-id", required=True, help="会话 ID")
    sub.add_argument("--max-results", type=int, default=10, help="最大结果数")
    sub.add_argument("--headless", action="store_true", help="无头模式")
    sub.add_argument("--cdp", default="http://localhost:9222", help="CDP 连接地址 (默认: http://localhost:9222)")
    sub.set_defaults(func=cmd_explore)

    # research
    sub = subparsers.add_parser("research", help="分析达人主页")
    sub.add_argument("--url", required=True, help="达人主页 URL")
    sub.add_argument("--session-id", required=True, help="会话 ID")
    sub.add_argument("--videos", type=int, default=3, help="截取最近视频数")
    sub.add_argument("--headless", action="store_true", help="无头模式")
    sub.add_argument("--cdp", default="http://localhost:9222", help="CDP 连接地址 (默认: http://localhost:9222)")
    sub.set_defaults(func=cmd_research)

    # login
    sub = subparsers.add_parser("login", help="获取抖音登录二维码")
    sub.add_argument("--output", help="二维码保存路径 (默认: /tmp/douyin_qrcode.png)")
    sub.add_argument("--headless", action="store_true", help="无头模式")
    sub.set_defaults(func=cmd_login)

    # check-login
    sub = subparsers.add_parser("check-login", help="检查抖音登录状态")
    sub.add_argument("--headless", action="store_true", help="无头模式")
    sub.set_defaults(func=cmd_check_login)

    # send-code
    sub = subparsers.add_parser("send-code", help="发送手机验证码")
    sub.add_argument("--phone", required=True, help="手机号")
    sub.add_argument("--headless", action="store_true", help="无头模式")
    sub.set_defaults(func=cmd_send_code)

    # verify-code
    sub = subparsers.add_parser("verify-code", help="提交手机验证码完成登录")
    sub.add_argument("--code", required=True, help="收到的验证码")
    sub.add_argument("--headless", action="store_true", help="无头模式")
    sub.set_defaults(func=cmd_verify_code)

    # start-chrome
    sub = subparsers.add_parser("start-chrome", help="启动带远程调试的 Chrome（VNC 环境）")
    sub.add_argument("--port", type=int, default=9222, help="远程调试端口 (默认: 9222)")
    sub.add_argument("--display", default=":1", help="X11 Display (默认: :1)")
    sub.set_defaults(func=cmd_start_chrome)

    # report
    sub = subparsers.add_parser("report", help="生成报告")
    sub.add_argument("--session-id", required=True, help="会话 ID")
    sub.add_argument("--output", required=True, help="输出文件路径")
    sub.add_argument("--template", default="strategy_report", help="报告模板")
    sub.set_defaults(func=cmd_report)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as e:
        logger.error("执行失败: %s", e, exc_info=True)
        _output({"success": False, "error": str(e)}, exit_code=2)


if __name__ == "__main__":
    main()
