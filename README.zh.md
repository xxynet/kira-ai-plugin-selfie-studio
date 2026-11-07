# 自拍工坊

[English](README.md) | 简体中文

为角色自拍服务的衣橱与场景库。在 WebUI 页面上传穿搭单品（上装 / 下装 / 连衣裙 / 鞋履 / 配饰）与场景，角色自拍时会自动把它们作为附加参考图。

![Version](https://img.shields.io/badge/version-1.0.0-blue)

## 功能

- **衣橱** — 按类别管理穿搭单品，支持备注、参与自拍开关、搜索与筛选
- **场景** — 上传地点与环境参考图（室内、街景、自然、出行等）
- **试拍** — 选择穿搭与场景，写下自拍描述，立即用默认图像模型生成预览自拍，同时产出可直接发送的 `<dressup>` 标签
- **目录播报** — 展示每轮对话注入角色系统提示的完整目录内容

页面自动跟随 WebUI 本体的主题（浅色 / 深色）与语言（中文 / 英文），页内不提供切换。

## 工作原理

- **LLM 集成** — 通过 `on.llm_request` 钩子把已启用的衣橱目录（名称、类别、备注）附加到系统提示，并注册 `<dressup>` 消息标签：

  ```xml
  <dressup outfit="白色帆布鞋,牛仔外套" scene="咖啡厅">坐在落地窗边回眸</dressup>
  ```

  标签按名称在库中解析图片，先加载人设参考图（穿搭与场景依次跟随），再走默认图像模型的 img2img 生成——与内置 `<selfie>` 标签同一套契约。目录为空或关闭时，角色自动回退到普通 `<selfie>`。

- **前置条件** — 当前人设需已设置参考图，且已配置默认图像模型。

## 存储

运行时数据保存在插件数据目录（`ctx.get_plugin_data_dir()`）中，绝不与插件源码混放：

```
data/plugin_data/kira-ai-plugin-selfie-studio/uploads/
├── wardrobe/<id>.<ext>   # 穿搭图片
├── scenes/<id>.<ext>     # 场景图片
└── library.json          # 清单（原子写入）
```

因此重装或删除插件不会丢失衣橱数据。
支持格式：PNG / JPEG / WebP，单张不超过 10 MB，上限 200 件。

## 插件设置

- **向角色播报衣橱** — 每轮对话将目录附加到系统提示（默认开启）

## 接口

| 方法 | 路径 | 用途 |
| ---- | ---- | ---- |
| GET | `/api/plugin/kira-ai-plugin-selfie-studio/items` | 列出衣橱与场景 |
| POST | `…/items/upload` | multipart 上传（file, kind, name, category, note） |
| POST | `…/items/update` | 改名 / 改类别 / 备注 / 启停 |
| POST | `…/items/delete` | 删除单品与图片文件 |
| GET | `…/image/{id}` | 读取单品图片 |
| GET | `…/catalog` | 预览注入的目录文本 |
| POST | `…/testshot` | 生成预览自拍 |
