"""
创建新项目脚本 — 本地运行或通过 GitHub Actions workflow_dispatch 触发
"""
import json
import os
import sys
from datetime import date

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "projects.json")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from daily_scan import full_schedule, load_projects, save_projects


def create_project(name: str, store_name: str, opening_date_str: str, store_area: float):
    """创建新项目"""
    opening_date = date.fromisoformat(opening_date_str)
    nodes = full_schedule(opening_date, store_area)

    project = {
        "id": str(len(load_projects()) + 1),
        "name": name,
        "store_name": store_name,
        "opening_date": opening_date.isoformat(),
        "store_area": store_area,
        "status": "active",
        "created_at": date.today().isoformat(),
        "nodes": []
    }

    for n in nodes:
        project["nodes"].append({
            "name": n["name"],
            "node_type": n["node_type"],
            "stage": n["stage"],
            "status": n.get("status", "pending"),
            "planned_start": n["planned_start"].isoformat() if n["planned_start"] else None,
            "planned_end": n["planned_end"].isoformat() if n["planned_end"] else None,
            "actual_start": None,
            "actual_end": None,
            "assignee": n["assignee"],
            "depends_on": n["depends_on"],
            "is_critical": n["is_critical"],
            "duration": n["duration"],
            "sort_order": n["sort_order"],
        })

    projects = load_projects()
    projects.append(project)
    save_projects(projects)

    print(f"✅ 项目「{name}」创建成功！")
    print(f"   开业日期: {opening_date}")
    print(f"   门店面积: {store_area}㎡")
    print(f"   节点数量: {len(nodes)}")
    return project


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="创建开店项目")
    parser.add_argument("--name", required=True, help="项目名称")
    parser.add_argument("--store", required=True, help="门店名称")
    parser.add_argument("--date", required=True, help="目标开业日期 YYYY-MM-DD")
    parser.add_argument("--area", type=float, required=True, help="门店面积（㎡）")
    args = parser.parse_args()

    create_project(args.name, args.store, args.date, args.area)
