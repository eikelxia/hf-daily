"""
hf-daily 核心脚本 — 每日提醒扫描
由 GitHub Actions 定时触发，数据存 JSON 文件持久化。
"""
import json
import os
import sys
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BJT = timezone(timedelta(hours=8))
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "projects.json")

# ═══════════════════════════════════════════
# 模板引擎（从原项目迁移）
# ═══════════════════════════════════════════

import math

HOLIDAYS_2025 = {
    date(2025, 1, 1), date(2025, 1, 28), date(2025, 1, 29), date(2025, 1, 30),
    date(2025, 1, 31), date(2025, 2, 1), date(2025, 2, 2), date(2025, 2, 3),
    date(2025, 2, 4), date(2025, 4, 4), date(2025, 4, 5), date(2025, 4, 6),
    date(2025, 5, 1), date(2025, 5, 2), date(2025, 5, 3), date(2025, 5, 4),
    date(2025, 5, 5), date(2025, 5, 31), date(2025, 6, 1), date(2025, 6, 2),
    date(2025, 10, 1), date(2025, 10, 2), date(2025, 10, 3), date(2025, 10, 4),
    date(2025, 10, 5), date(2025, 10, 6), date(2025, 10, 7), date(2025, 10, 8),
}

def is_workday(d: date) -> bool:
    if d.weekday() >= 5: return False
    if d in HOLIDAYS_2025: return False
    return True

def add_workdays(start: date, days: int) -> date:
    current, count = start, 0
    while count < days:
        current += timedelta(days=1)
        if is_workday(current): count += 1
    return current

def add_natural_days(start: date, days: int) -> date:
    return start + timedelta(days=days)

def sub_natural_days(end: date, days: int) -> date:
    return end - timedelta(days=days)

def calc_water_electricity(area: float) -> int:
    if area <= 60: return 1
    elif area <= 100: return 2
    else: return 3

def calc_tile(area: float) -> int:
    return math.ceil(area / 50)

def calc_paint(area: float) -> int:
    if area <= 100: return 5
    else: return math.ceil(area / 100) * 5

def calc_cabinet(area: float) -> int:
    return 7 if area <= 60 else 14

MANUAL_TRIGGER_NODES = {
    "合同签约", "平面图确认", "效果图确认", "施工图确认",
    "空调确认", "消防改造",
}

NODE_TEMPLATES = [
    ("前期资料搜集", "milestone", "startup", lambda a: 2, None, "我", False, False),
    ("催促基础资料提交", "milestone", "startup", lambda a: 1, "前期资料搜集", "我", False, False),
    ("提供门店完全尺寸(CAD)", "milestone", "startup", lambda a: 2, None, "加盟商", False, False),
    ("平面图出图", "milestone", "startup", lambda a: 2, "提供门店完全尺寸(CAD)", "我", False, True),
    ("平面图确认", "milestone", "startup", lambda a: 1, "平面图出图", "加盟商", False, False),
    ("效果图出图", "milestone", "startup", lambda a: 3, "平面图确认", "我", False, True),
    ("效果图确认", "milestone", "startup", lambda a: 1, "效果图出图", "加盟商", False, False),
    ("施工图出图", "milestone", "startup", lambda a: 3, "效果图确认", "我", False, True),
    ("施工图确认", "milestone", "startup", lambda a: 1, "施工图出图", "加盟商", False, False),
    ("合同签约", "milestone", "startup", lambda a: 2, None, "加盟商", False, False),
    ("营业执照办理", "milestone", "startup", lambda a: 7, "合同签约", "加盟商", True, False),
    ("预定柜体", "construction", "construction", calc_cabinet, "施工图确认", "加盟商", False, False),
    ("空调确认", "construction", "construction", lambda a: 2, None, "加盟商", False, False),
    ("办理进场资料", "construction", "construction", lambda a: 1, "施工图确认", "加盟商/施工负责人", False, False),
    ("人员招聘", "milestone", "construction", lambda a: 1, "办理进场资料", "加盟商+小朱", False, False),
    ("砖块隔墙", "construction", "construction", lambda a: 2, "办理进场资料", "加盟商/施工负责人", False, False),
    ("水电改造", "construction", "construction", calc_water_electricity, "砖块隔墙", "加盟商/施工负责人", False, False),
    ("地砖铺贴", "construction", "construction", calc_tile, "水电改造", "加盟商/施工负责人", False, False),
    ("消防改造", "construction", "construction", lambda a: 3, None, "加盟商+二消", False, False),
    ("木工", "construction", "construction", lambda a: 2, "地砖铺贴", "加盟商/施工负责人", False, False),
    ("广告字预订", "construction", "construction", lambda a: 5, "木工", "加盟商/施工负责人", False, False),
    ("漆工", "construction", "construction", calc_paint, "木工", "加盟商/施工负责人", False, False),
    ("柜体安装", "construction", "construction", lambda a: 2, "漆工", "加盟商/施工负责人", False, False),
    ("灯具安装", "construction", "construction", lambda a: 2, "漆工", "加盟商/施工负责人", False, False),
    ("广告字安装", "construction", "construction", lambda a: 1, "漆工", "加盟商/施工负责人", False, False),
    ("美缝保洁", "construction", "construction", lambda a: 1, "柜体安装", "加盟商/施工负责人", False, False),
    ("家具物料进场", "construction", "construction", lambda a: 2, "美缝保洁", "加盟商/施工负责人", False, False),
    ("装修验收", "milestone", "construction", lambda a: 1, "家具物料进场", "加盟商/施工负责人", True, False),
    ("货品货单确认", "countdown", "countdown", lambda a: 14, None, "王雅", False, False),
    ("设计物料确认", "countdown", "countdown", lambda a: 7, None, "陈哇塞", False, False),
    ("开业活动确认", "countdown", "countdown", lambda a: 7, None, "陈哇塞", False, False),
    ("线上培训", "countdown", "countdown", lambda a: 4, None, "小朱", False, False),
    ("培训时间确认", "countdown", "countdown", lambda a: 7, None, "我", False, False),
    ("开业活动物料到场", "countdown", "countdown", lambda a: 3, None, "加盟商", False, False),
    ("美团/抖音/银豹搭建", "countdown", "countdown", lambda a: 3, None, "陈哇塞", False, False),
    ("线下到店培训", "countdown", "countdown", lambda a: 2, None, "我", False, False),
    ("开业验收", "countdown", "countdown", lambda a: 1, None, "我", False, False),
]

def full_schedule(opening_date: date, store_area: float, project_start_date: Optional[date] = None) -> list[dict]:
    """完整排期"""
    if project_start_date is None:
        project_start_date = date.today()

    nodes = []
    for i, (name, ntype, stage, duration_fn, depends_on, assignee, is_critical, use_workdays) in enumerate(NODE_TEMPLATES):
        duration = duration_fn(store_area)
        if name in MANUAL_TRIGGER_NODES:
            planned_start, planned_end = None, None
        elif stage == "countdown":
            planned_end = sub_natural_days(opening_date, duration)
            planned_start = planned_end
        else:
            planned_start, planned_end = None, None

        nodes.append({
            "name": name, "node_type": ntype, "stage": stage,
            "planned_start": planned_start, "planned_end": planned_end,
            "assignee": assignee, "depends_on": depends_on,
            "is_critical": is_critical, "use_workdays": use_workdays,
            "duration": duration, "sort_order": i, "status": "pending",
        })

    node_map = {n["name"]: n for n in nodes}

    # 启动阶段
    startup_order = [
        "前期资料搜集", "催促基础资料提交", "提供门店完全尺寸(CAD)",
        "平面图出图", "平面图确认", "效果图出图", "效果图确认",
        "施工图出图", "施工图确认",
    ]
    current_date = project_start_date
    for name in startup_order:
        node = node_map.get(name)
        if not node or node["stage"] != "startup": continue
        if name in MANUAL_TRIGGER_NODES:
            node["planned_start"] = None
            node["planned_end"] = None
            continue
        dep = node.get("depends_on")
        if dep and dep in node_map and node_map[dep].get("planned_end"):
            current_date = node_map[dep]["planned_end"]
        duration = node["duration"]
        node["planned_start"] = current_date
        node["planned_end"] = add_workdays(current_date, duration) if node["use_workdays"] else add_natural_days(current_date, duration)
        current_date = node["planned_end"]

    # 施工起点
    construction_start = (
        node_map.get("施工图确认", {}).get("planned_end")
        or node_map.get("施工图出图", {}).get("planned_end")
        or project_start_date
    )

    # 装修阶段
    construction_order = [
        "预定柜体", "办理进场资料", "人员招聘", "砖块隔墙",
        "水电改造", "地砖铺贴", "木工", "漆工", "广告字预订",
        "柜体安装", "灯具安装", "广告字安装",
        "美缝保洁", "家具物料进场", "装修验收",
    ]
    current_date = construction_start
    for name in construction_order:
        node = node_map.get(name)
        if not node or node["stage"] != "construction": continue
        if name in MANUAL_TRIGGER_NODES: continue
        dep = node.get("depends_on")
        if dep and dep in node_map and node_map[dep].get("planned_end"):
            current_date = node_map[dep]["planned_end"]
        duration = node["duration"]
        node["planned_start"] = current_date
        node["planned_end"] = add_workdays(current_date, duration) if node["use_workdays"] else add_natural_days(current_date, duration)
        current_date = node["planned_end"]

    # 漆工和广告字预订并行从木工结束
    wood_end = node_map.get("木工", {}).get("planned_end")
    if wood_end:
        for pn in ["漆工", "广告字预订"]:
            n = node_map.get(pn)
            if n and n.get("planned_start") is None:
                n["planned_start"] = wood_end
                n["planned_end"] = add_natural_days(wood_end, n["duration"])

    paint_end = node_map.get("漆工", {}).get("planned_end")
    if paint_end:
        for pn in ["柜体安装", "灯具安装", "广告字安装"]:
            n = node_map.get(pn)
            if n and n.get("planned_start") is None:
                n["planned_start"] = paint_end
                n["planned_end"] = add_natural_days(paint_end, n["duration"])

    cabinet_end = node_map.get("柜体安装", {}).get("planned_end")
    if cabinet_end:
        clean = node_map.get("美缝保洁")
        if clean:
            clean["planned_start"] = cabinet_end
            clean["planned_end"] = add_natural_days(cabinet_end, clean["duration"])

    return nodes


# ═══════════════════════════════════════════
# 状态机
# ═══════════════════════════════════════════

def get_remindable_nodes(nodes: list[dict], today: date) -> dict:
    result = {"start_confirm": [], "completion_check": [], "daily_chase": []}
    for node in nodes:
        status = node.get("status", "pending")
        if status == "completed": continue
        if node["name"] == "合同签约": continue

        if node.get("node_type") == "countdown":
            planned_end = node.get("planned_end")
            if planned_end and planned_end <= today and status != "completed":
                result["daily_chase"].append(node)
            continue

        if node.get("name") == "人员招聘" and status != "completed":
            result["daily_chase"].append(node)
            continue

        planned_start = node.get("planned_start")
        if planned_start:
            day_before = planned_start - timedelta(days=1)
            if day_before == today and status in ["pending", "delayed"]:
                result["start_confirm"].append(node)

        planned_end = node.get("planned_end")
        if planned_end and planned_end <= today and status in ["in_progress", "upcoming"]:
            result["completion_check"].append(node)

    return result


# ═══════════════════════════════════════════
# 数据持久化
# ═══════════════════════════════════════════

def load_projects() -> list[dict]:
    """从 JSON 文件加载项目数据"""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 反序列化日期
    for p in data:
        if p.get("opening_date"):
            p["opening_date"] = date.fromisoformat(p["opening_date"])
        for n in p.get("nodes", []):
            if n.get("planned_start"):
                n["planned_start"] = date.fromisoformat(n["planned_start"])
            if n.get("planned_end"):
                n["planned_end"] = date.fromisoformat(n["planned_end"])
            if n.get("actual_start"):
                n["actual_start"] = date.fromisoformat(n["actual_start"])
            if n.get("actual_end"):
                n["actual_end"] = date.fromisoformat(n["actual_end"])
    return data


def save_projects(projects: list[dict]):
    """保存项目数据到 JSON 文件"""
    def serialize(obj):
        if isinstance(obj, date):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(projects, f, ensure_ascii=False, indent=2, default=serialize)


# ═══════════════════════════════════════════
# 企业微信消息
# ═══════════════════════════════════════════

def send_wecom(webhook_url: str, msgtype: str, content: str) -> bool:
    """发送企业微信消息"""
    import requests
    if msgtype == "markdown":
        payload = {"msgtype": "markdown", "markdown": {"content": content}}
    else:
        payload = {"msgtype": "text", "text": {"content": content}}

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        data = resp.json()
        if data.get("errcode") != 0:
            logger.error(f"消息发送失败: {data}")
            return False
        return True
    except Exception as e:
        logger.error(f"消息发送异常: {e}")
        return False


# ═══════════════════════════════════════════
# 主逻辑
# ═══════════════════════════════════════════

def run_daily_scan():
    """每日扫描，发送提醒"""
    webhook_url = os.getenv("WECOM_WEBHOOK_URL", "")
    if not webhook_url:
        logger.error("WECOM_WEBHOOK_URL 未配置")
        return {"error": "WECOM_WEBHOOK_URL 未配置"}

    today = datetime.now(BJT).date()
    now = datetime.now(BJT)
    current_hour = now.hour

    projects = load_projects()
    sent_count = 0

    for proj in projects:
        proj_name = proj["name"]
        nodes = proj.get("nodes", [])

        remindable = get_remindable_nodes(nodes, today)
        in_window = 12 <= current_hour < 14

        if not in_window:
            for node in remindable.get("start_confirm", []):
                assignee_names = node["assignee"].replace("+", "、")
                msg = (
                    f"【{proj_name}】\n"
                    f"节点「{node['name']}」将于 **{node.get('planned_start', '')}** 开始\n"
                    f"负责人：{assignee_names}\n\n"
                    f"请确认是否按时启动？"
                )
                send_wecom(webhook_url, "markdown", msg)
                sent_count += 1

        for node in remindable.get("completion_check", []):
            assignee_names = node["assignee"].replace("+", "、")
            msg = (
                f"【{proj_name}】\n"
                f"节点「{node['name']}」计划于 **{node.get('planned_end', '')}** 完成\n"
                f"负责人：{assignee_names}\n\n"
                f"请确认是否已完成？"
            )
            send_wecom(webhook_url, "markdown", msg)
            sent_count += 1

        for node in remindable.get("daily_chase", []):
            assignee_names = node["assignee"].replace("+", "、")
            msg = (
                f"【{proj_name}】\n"
                f"节点「{node['name']}」已超期！截止：**{node.get('planned_end', '')}**\n"
                f"负责人：{assignee_names}\n\n"
                f"请尽快完成！"
            )
            send_wecom(webhook_url, "markdown", msg)
            sent_count += 1

    save_projects(projects)

    # 同步到智能表格
    smartsheet_webhook = os.getenv("SMARTSHEET_WEBHOOK", "")
    if smartsheet_webhook and projects:
        try:
            sync_to_smartsheet(smartsheet_webhook, projects)
        except Exception as e:
            logger.error(f"Smartsheet sync error: {e}")

    logger.info(f"扫描完成: 发送 {sent_count} 条消息, {len(projects)} 个项目")
    return {"sent": sent_count, "projects": len(projects), "time": str(now)}


def sync_to_smartsheet(webhook_url: str, projects: list[dict]):
    """同步状态到智能表格 webhook"""
    import requests

    stage_names = {"startup": "启动", "construction": "装修", "countdown": "倒计时"}
    status_map = {"pending": "待开始", "in_progress": "进行中", "completed": "已完成", "delayed": "已延期"}

    def to_ts(d):
        if d is None: return ""
        if isinstance(d, str): d = date.fromisoformat(d)
        dt = datetime.combine(d, datetime.min.time()).replace(tzinfo=BJT)
        return str(int(dt.timestamp() * 1000))

    records = []
    for proj in projects:
        for n in proj.get("nodes", []):
            start_ts = to_ts(n.get("planned_start"))
            end_ts = to_ts(n.get("planned_end"))
            if not start_ts: continue

            records.append({"values": {
                "f04Gwj": [{"type": "text", "text": proj["name"]}],
                "ftQMc5": [{"type": "text", "text": stage_names.get(n.get("stage", ""), n.get("stage", ""))}],
                "ftk5Tx": [{"type": "text", "text": n.get("name", "")}],
                "ffFwIh": [{"type": "text", "text": str(n.get("duration", 1))}],
                "fn8TJd": [{"type": "text", "text": start_ts}],
                "fH3jwM": [{"type": "text", "text": end_ts or start_ts}],
                "fABnGQ": [{"type": "text", "text": n.get("assignee", "")}],
                "fib5xt": [{"type": "text", "text": status_map.get(n.get("status", "pending"), "待开始")}],
            }})

    if not records: return
    for i in range(0, len(records), 100):
        batch = records[i:i+100]
        requests.post(webhook_url, json={"add_records": batch}, timeout=30)


if __name__ == "__main__":
    result = run_daily_scan()
    print(json.dumps(result, default=str, ensure_ascii=False))
