# 核心人脸识别 Demo 实施计划

## Summary

- 目标：先落地一个最小可运行的 `Python 单服务人脸识别 Demo`，用于验证“本地图片目录建底库 + HTTP API 识别返回结果”的核心链路。
- 范围：本次只做 `识别 Demo`，不接入 `Java 管理服务`、`Android 门禁机 APK`，也不实现 `活体检测`。
- 运行方式：默认 `Windows + CPU 单机` 环境，本地启动服务即可演示。
- 验收标准：
  - 能从本地图片目录初始化员工人脸底库。
  - 能通过 HTTP 接口上传测试图片并返回匹配员工与相似度。
  - 能完成“能注册/能识别”的最小闭环演示。

## Current State Analysis

- 当前工作区 `e:\other\local-rl` 仅有文档，没有任何代码工程。
- 已存在的业务文档：
  - `e:\other\local-rl\docs\prd\门禁人脸打卡系统PRD.md`
  - `e:\other\local-rl\docs\prd\门禁人脸打卡系统ER图.md`
- 从现有文档可确认的事实：
  - 长期目标是 `Android Java + Java 服务 + Python 识别服务` 的三层方案。
  - Python 服务负责 `人脸特征提取 + 向量检索`，首期推荐 `FastAPI/Flask + FAISS`。
  - 当前用户明确要求的下一步是先做“最核心 Demo”。
- 经过确认后的 Demo 边界：
  - 先做 `Python 单服务`。
  - 先做 `仅识别`，不做活体。
  - 通过 `HTTP API` 演示。
  - 通过 `本地图片目录` 初始化底库。
  - 使用 `轻量现成库` 实现识别能力。
  - 默认 `CPU 单机` 运行。
  - 首先达到“能注册 + 能识别”的验收目标。

## Proposed Changes

### 1. 新建 Python Demo 工程

- 新建目录：`e:\other\local-rl\python-face-demo\`
  - 原因：当前仓库无任何代码，需独立建立最小 Demo 工程。
  - 目标：承载识别服务、样本目录、说明文档和依赖配置。

### 2. 建议工程结构

- `e:\other\local-rl\python-face-demo\README.md`
  - 写清启动方式、样本目录规范、接口调用方式、验收步骤。
- `e:\other\local-rl\python-face-demo\requirements.txt`
  - 固定 Demo 依赖，建议包含 `fastapi`、`uvicorn`、`faiss-cpu` 以及所选识别库。
- `e:\other\local-rl\python-face-demo\app\main.py`
  - 服务入口，启动 HTTP API。
- `e:\other\local-rl\python-face-demo\app\api\face.py`
  - 暴露底库初始化、单图识别接口。
- `e:\other\local-rl\python-face-demo\app\service\face_engine.py`
  - 封装人脸检测、特征提取、相似度计算与 Top1/TopK 结果。
- `e:\other\local-rl\python-face-demo\app\service\index_service.py`
  - 管理向量索引加载、重建和检索。
- `e:\other\local-rl\python-face-demo\app\service\gallery_service.py`
  - 负责从本地图片目录扫描员工样本并构建底库元数据。
- `e:\other\local-rl\python-face-demo\app\model\schemas.py`
  - 定义请求、响应结构。
- `e:\other\local-rl\python-face-demo\data\gallery\`
  - 人脸底库目录，按员工分目录存放样本图。
- `e:\other\local-rl\python-face-demo\data\index\`
  - 保存向量索引文件和底库元数据缓存。
- `e:\other\local-rl\python-face-demo\scripts\test_api.http`
  - 提供可直接调用的接口示例。

### 3. Demo 功能设计

- 底库初始化接口
  - 作用：扫描 `data/gallery/` 下员工目录，提取特征并构建本地索引。
  - 输入：无或指定目录路径。
  - 输出：员工数量、图片数量、成功入库数量、失败数量。
- 单图识别接口
  - 作用：接收一张上传图片，返回最佳匹配员工和相似度。
  - 输入：图片文件、可选阈值。
  - 输出：是否匹配、员工编号/名称、相似度、阈值、耗时。
- 健康检查接口
  - 作用：快速确认服务可启动、索引是否已加载。
  - 输出：服务状态、索引状态、底库数量。

### 4. 数据与目录约定

- 底库目录建议采用以下结构：
  - `data/gallery/EMP001_张三/1.jpg`
  - `data/gallery/EMP001_张三/2.jpg`
  - `data/gallery/EMP002_李四/1.jpg`
- 解析规则：
  - 目录名作为员工标识来源，格式建议为 `员工编号_姓名`。
  - 同一目录下可放多张样本图，构建时为每张图生成向量。
- 索引产物：
  - `data/index/faiss.index`
  - `data/index/metadata.json`

### 5. 模型与实现决策

- 识别能力：优先采用 `轻量现成库 + 可替换封装` 的方式实现。
- HTTP 框架：采用 `FastAPI`。
- 向量检索：采用 `FAISS CPU`。
- 模型运行：默认按 `CPU 单机` 设计，不依赖 GPU。
- 代码结构上将“模型调用”和“索引管理”拆分，避免后续接入更强模型时重写接口层。

### 6. 接口草案

- `GET /health`
  - 返回服务状态、索引是否存在、底库统计。
- `POST /api/gallery/rebuild`
  - 触发重新扫描本地图片目录并重建索引。
- `POST /api/face/recognize`
  - 上传图片并返回识别结果。

### 7. 识别结果结构建议

```json
{
  "success": true,
  "matched": true,
  "employeeNo": "EMP001",
  "employeeName": "张三",
  "similarity": 0.92,
  "threshold": 0.8,
  "elapsedMs": 143
}
```

### 8. 最小验收样例

- 准备 2-3 个员工目录，每人 2-3 张底库图片。
- 启动服务后先调用重建底库接口。
- 上传某员工测试图，接口返回正确员工信息和相似度。
- 若上传无法匹配的图片，允许先返回 `matched=false` 或低相似度结果，但本轮计划的硬性验收以“能注册 + 能识别”优先。

## Assumptions & Decisions

- 决策：本轮只做 `Python 单服务 Demo`。
  - 原因：当前仓库无代码，先验证最核心识别链路，投入最小、反馈最快。
- 决策：本轮不做活体检测。
  - 原因：用户已明确 Demo 阶段先做“仅识别”，便于缩短交付路径。
- 决策：采用 `HTTP API` 而非命令行作为主要演示方式。
  - 原因：后续更容易接入 Java 服务和 Android 客户端。
- 决策：底库采用 `本地图片目录` 初始化。
  - 原因：最适合当前无后台、无数据库的仓库起步。
- 决策：默认 `CPU 单机`。
  - 原因：符合 Demo 环境和快速验证目标。
- 假设：本地已有可用员工样本图，且能保证至少基础正脸清晰度。
- 假设：Demo 允许使用成熟第三方识别库，不要求当前阶段自行训练模型。

## Verification Steps

1. 在 `python-face-demo` 工程中安装依赖并启动服务。
2. 准备 `data/gallery/` 底库目录并放入员工样本图。
3. 调用 `POST /api/gallery/rebuild`，确认返回底库构建成功。
4. 调用 `POST /api/face/recognize` 上传测试图。
5. 检查接口是否返回匹配员工、相似度、阈值和耗时。
6. 用不同员工样本重复测试，验证基本可识别。
7. 用一张非底库图片测试，观察未匹配或低相似度返回是否合理。

## Implementation Steps

1. 初始化 `python-face-demo` 工程目录和依赖文件。
2. 选择并接入轻量现成的人脸识别库，封装 `face_engine`。
3. 实现本地图片目录扫描和 FAISS 索引重建能力。
4. 实现 `health`、`gallery/rebuild`、`face/recognize` 三个接口。
5. 增加样例目录规范和接口调用示例。
6. 通过本地样本完成“能注册 + 能识别”的最小验收。
