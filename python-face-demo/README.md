# Python Face Demo

## 目标

这是一个最小可运行的人脸识别 Demo，用于验证以下链路：

- 从本地图片目录初始化人脸底库
- 通过 HTTP API 上传测试图片
- 返回匹配员工和相似度结果

当前版本已支持基础静默活体检测，但仍然不接 Java 或 Android。
向量检索优先使用 `FAISS`，若本机未成功安装 `faiss-cpu`，代码会自动回退到 `NumPy` 检索模式。
识别引擎使用 `OpenCV YuNet + SFace`，模型文件首次运行时会自动下载到 `models/` 目录。

## 环境要求

- Windows
- Python 3.10+
- CPU 环境

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动服务

在 `python-face-demo` 目录下运行：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 底库目录规范

将员工样本图片放到 `data/gallery/` 下，目录命名建议为：

```text
data/gallery/
  EMP001_ZhangSan/
    1.jpg
    2.jpg
  EMP002_LiSi/
    1.jpg
```

- 目录名格式建议：`员工编号_姓名`
- 每个员工目录可放多张图片
- 图片格式支持：`.jpg` `.jpeg` `.png` `.bmp` `.webp`

## 配置文件

配置文件位置：

```text
config/settings.yaml
```

当前支持字段：

- `detection_score_threshold`：人脸检测阈值
- `recognition_threshold`：人脸识别匹配阈值
- `liveness_enabled`：是否启用活体检测
- `liveness_threshold`：活体检测阈值
- `liveness_model_path`：活体 ONNX 模型相对路径

通过接口修改后会立即生效，不需要重启服务。

## 接口

### 1. 健康检查

```http
GET /health
```

### 2. 重建底库

```http
POST /api/gallery/rebuild
```

返回内容包含：

- 成功/失败状态
- 底库员工数、图片数、入库数、失败数
- 失败文件列表 `failedFiles`
- 每个失败文件的具体原因，例如 `No face detected in image.`

### 3. 预检查底库

```http
POST /api/gallery/precheck
```

返回内容包含：

- 成功/失败状态
- 底库员工数、图片数、通过数、失败数
- 失败文件列表 `failedFiles`
- 每个失败文件的具体原因

### 4. 获取当前阈值配置

```http
GET /api/settings
```

### 5. 设置阈值配置

```http
POST /api/settings
Content-Type: application/json

{
  "detectionScoreThreshold": 0.7,
  "recognitionThreshold": 0.82
}
```

### 6. 单图识别

```http
POST /api/face/recognize
Content-Type: multipart/form-data
file=<image>
```

- 当前链路已改为：`先活体，再识别`
- 默认使用配置文件中的 `recognition_threshold`
- 若传 `?threshold=0.8`，则以当前请求参数优先
- 返回中会附带：
  - `livenessResult`
  - `livenessScore`
  - `livenessThreshold`
- 当活体失败时，接口会直接返回 `matched=false`，不继续做人脸识别

### 7. 单图活体检测

```http
POST /api/face/liveness-check
Content-Type: multipart/form-data
file=<image>
```

返回内容包含：

- `livenessResult`：`PASS` 或 `REJECT`
- `livenessScore`：活体分值
- `threshold`：当前活体阈值
- `elapsedMs`：本次检测耗时

### 8. 活体批量测试

```http
POST /api/face/liveness-batch-test
```

该接口会扫描：

```text
data/liveness/
  real/
  photo_spoof/
  screen_spoof/
```

返回内容包含：

- 真人样本数量
- 纸质照片翻拍样本数量
- 屏幕翻拍样本数量
- 总体准确率
- 各类样本通过/拒绝比率
- 每张样本的检测结果明细

## 活体样本目录规范

推荐准备以下样本：

- `data/liveness/real/`
  - 真人正脸图片
- `data/liveness/photo_spoof/`
  - 打印照片后再翻拍的图片
- `data/liveness/screen_spoof/`
  - 手机、平板、显示器展示照片后再翻拍的图片

建议每类至少准备 `3-5` 张图片，先完成静态样本测试，再进入后续实时视频流测试。

## 最小演示步骤

1. 准备 2-3 个员工样本目录和图片
2. 启动服务
3. 调用 `POST /api/gallery/precheck`
4. 确认失败图片列表无误后，再调用 `POST /api/gallery/rebuild`
5. 先调 `POST /api/face/liveness-check` 验证活体结果
6. 若需要，调 `POST /api/face/liveness-batch-test` 查看样本集统计
7. 再上传一张测试图到 `POST /api/face/recognize`
8. 查看返回的员工编号、姓名和相似度

## 本地实时采集联调

当不使用浏览器打开摄像头时，可以直接用本地 Python 脚本读取 USB 摄像头，再调用现有识别接口完成实时联调。

### 适用场景

- 局域网内快速验证“摄像头采集 -> 活体 -> 识别”链路
- 临时替代 H5 或门禁机 App 做算法调试
- 调试服务地址、阈值和抽帧频率

### 启动前提

- `python-face-demo` 服务已启动
- 已执行过底库预检查和重建
- 本机存在可用摄像头
- 已安装 `requirements.txt` 中新增的 `requests`

### 启动命令

在 `python-face-demo` 目录下运行：

```bash
python scripts/live_camera_demo.py --server http://127.0.0.1:8002 --camera 0 --interval-ms 500
```

可选参数：

- `--server`：服务地址
- `--camera`：摄像头编号
- `--interval-ms`：抽帧请求间隔，单位毫秒
- `--threshold`：可选识别阈值覆盖
- `--width`：可选采集宽度
- `--height`：可选采集高度
- `--timeout`：接口请求超时时间，单位秒

### 运行说明

- 脚本会持续打开本地摄像头
- 每隔一段时间抓取一帧并调用 `POST /api/face/recognize`
- 窗口中会显示：
  - `livenessResult`
  - `livenessScore`
  - `matched`
  - `employeeNo`
  - `employeeName`
  - `similarity`
  - `elapsedMs`
- 按 `q` 可退出脚本

### 常见问题

- 打不开摄像头：
  - 先检查摄像头是否被其他程序占用
  - 更换 `--camera` 编号重试
- 服务请求失败：
  - 确认 `--server` 地址是否正确
  - 先访问 `GET /health` 确认服务可用
- 不能弹出预览窗口：
  - 当前依赖使用的是 `opencv-contrib-python-headless`
  - 若环境不支持 GUI，脚本会自动退化为控制台模式，但仍可继续发请求联调

## 说明

- 首次运行识别模型时，会自动下载 YuNet 和 SFace 的 ONNX 模型文件
- 首次运行活体检测时，会自动下载量化版静默活体 ONNX 模型文件
- 当前识别结果依赖样本质量和图片清晰度
- 活体检测当前先以静态样本测试为主，实时视频流不在本轮范围内
- 若后续接入 Java 或 Android，可直接复用当前 HTTP 接口
