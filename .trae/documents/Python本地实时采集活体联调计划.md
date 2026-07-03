# Python 本地实时采集活体联调计划

## Summary

- 目标：不依赖浏览器或门禁机 App，先在现有 `python-face-demo` 基础上落地一个 `Python 本地实时采集工具`，直接读取 PC 摄像头，按固定频率抽帧，并调用现有 Python 服务完成活体检测与识别联调。
- 本轮定位：
  - 作为局域网和算法联调工具
  - 不作为最终交付端
  - 不接 Android 门禁机
  - 不接 Java 服务编排
- 成功标准：
  - 可以从本地 USB 摄像头读取实时视频
  - 可以按固定频率抓帧并调用现有 `/api/face/recognize`
  - 可以在本地界面或终端中展示活体结果、识别结果、耗时
  - 可以控制抽帧频率、目标服务地址、摄像头编号

## Current State Analysis

- 当前项目已有可复用工程：`e:\other\local-rl\python-face-demo\`
- 已确认现有服务能力：
  - `POST /api/face/liveness-check`
  - `POST /api/face/liveness-batch-test`
  - `POST /api/face/recognize`
  - `GET /api/settings`
  - `POST /api/settings`
- 已确认 `recognize` 链路现状：
  - 已接入“先活体，再识别”
  - 返回中已包含：
    - `livenessResult`
    - `livenessScore`
    - `livenessThreshold`
    - `matched`
    - `employeeNo`
    - `employeeName`
    - `similarity`
- 已确认可复用目录与文件：
  - `e:\other\local-rl\python-face-demo\app\api\face.py`
  - `e:\other\local-rl\python-face-demo\app\model\schemas.py`
  - `e:\other\local-rl\python-face-demo\README.md`
  - `e:\other\local-rl\python-face-demo\scripts\`
- 已确认现有实时视频方案文档：
  - `e:\other\local-rl\docs\prd\实时视频流活体实施方案.md`
- 已确认当前未具备能力：
  - 没有本地摄像头采集程序
  - 没有多帧抽样联调脚本
  - 没有实时预览窗口或命令行测试工具

## Proposed Changes

### 1. 新增本地实时采集脚本

- 新建文件：`e:\other\local-rl\python-face-demo\scripts\live_camera_demo.py`
  - 作用：本地读取摄像头，定时抓帧并调用现有识别接口
  - 建议能力：
    - 支持摄像头编号，例如 `--camera 0`
    - 支持服务地址，例如 `--server http://127.0.0.1:8003`
    - 支持抽帧间隔，例如 `--interval-ms 500`
    - 支持窗口预览
    - 支持按键退出
  - 输出内容：
    - 活体结果
    - 活体分值
    - 识别结果
    - 员工编号
    - 员工姓名
    - 相似度
    - 单次请求耗时

### 2. 为本地采集脚本补充 HTTP 调用封装

- 新建文件：`e:\other\local-rl\python-face-demo\scripts\live_client.py`
  - 作用：封装对 `/api/face/recognize` 的请求调用
  - 设计原因：
    - 将摄像头采集逻辑和接口调用逻辑分开
    - 便于后续复用到视频文件抽帧测试或 Java 对接参考
  - 建议行为：
    - 接收单帧 `numpy` 图像
    - 编码为 `jpg`
    - 以 `multipart/form-data` 调用识别接口
    - 统一解析响应结构和错误信息

### 3. 依赖补充

- 更新文件：`e:\other\local-rl\python-face-demo\requirements.txt`
  - 可能新增：
    - `requests`
  - 说明：
    - OpenCV 已存在，可直接用于摄像头采集和 JPEG 编码
    - 若仅用标准库也可行，但 `requests` 更适合快速联调

### 4. 文档补充

- 更新文件：`e:\other\local-rl\python-face-demo\README.md`
  - 增加章节：
    - 本地实时采集工具说明
    - 启动命令
    - 参数说明
    - 常见问题
  - 重点说明：
    - 本工具不依赖浏览器
    - 适合作为局域网联调工具
    - 与 H5 相比不受 HTTPS 和浏览器权限限制

### 5. 测试文档补充

- 新建文件：`e:\other\local-rl\docs\prd\Python本地实时采集测试清单.md`
  - 作用：给当前阶段的联调用例一份可执行清单
  - 建议覆盖：
    - 摄像头打开成功
    - 抽帧频率控制
    - 活体通过
    - 活体拒绝
    - 识别命中
    - 网络异常
    - 服务未启动
    - 摄像头被占用

## Assumptions & Decisions

- 决策：放弃本轮 H5 作为优先方案
  - 原因：浏览器摄像头权限依赖安全上下文，局域网测试复杂度更高
- 决策：优先做 `Python 本地采集工具`
  - 原因：与现有 Python 服务最贴近，开发最快，调试最稳
- 决策：先调用现有 `/api/face/recognize`
  - 原因：该接口已集成活体 + 识别，最适合快速闭环
- 决策：工具定位为“联调工具”，不是正式交付前端
  - 原因：当前目标是验证实时采集链路，而不是替代门禁机 APK
- 假设：本机或测试机存在可用 USB 摄像头
- 假设：当前服务继续运行在局域网可访问地址，例如 `http://127.0.0.1:8003`

## Verification Steps

1. 启动 `python-face-demo` 服务，确认 `/api/face/recognize` 可访问。
2. 运行 `live_camera_demo.py`，确认可以正常打开本地摄像头。
3. 确认界面或终端中能持续看到抽帧调用结果。
4. 用真人站到镜头前，确认返回活体通过和识别命中。
5. 用攻击样本对镜头翻拍，确认能观察到活体结果变化。
6. 修改抽帧间隔和服务地址，确认脚本参数生效。
7. 在服务关闭或网络异常时，确认脚本能清晰提示错误。

## Implementation Steps

1. 在 `scripts/` 下新增 `live_client.py`，封装识别接口调用。
2. 在 `scripts/` 下新增 `live_camera_demo.py`，实现摄像头采集、抽帧、调用接口和结果展示。
3. 在 `requirements.txt` 中补齐调用脚本所需依赖。
4. 在 `README.md` 中补充本地实时采集工具的使用说明。
5. 在 `docs/prd/` 中新增 `Python本地实时采集测试清单.md`。
6. 使用本机摄像头完成一次真实联调验证，并确认工具适合后续局域网测试。
