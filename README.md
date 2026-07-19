# 开店助手 (hf-daily)

门店开店项目节点管理系统 — 基于 GitHub Actions 自动化。

## 功能

- 📅 **自动排期**: 输入开业日期和面积，自动生成 37 个节点的时间线
- ⏰ **定时提醒**: 每天 9:00 和 14:00 自动扫描，发送企业微信群消息
- 📊 **可视化看板**: GitHub Pages 展示项目进度
- 🔄 **智能表格同步**: 自动同步到企业微信智能表格

## 架构

```
GitHub Actions (定时触发) → Python 脚本 → 企业微信机器人 → 群消息
                          ↕
                    projects.json (数据持久化)
                          ↓
                  GitHub Pages (看板展示)
```

## 使用方式

### 创建项目
在 GitHub Actions 页面手动触发 "Create Project" workflow，填入项目信息。

### 查看看板
访问 `https://eikelxia.github.io/hf-daily/`
