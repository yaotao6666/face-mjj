# 门禁人脸打卡系统 PRD 方案

## Summary

- 目标：建设一套仅运行于内网环境的门禁扫脸打卡系统，包含 `Android Java 原生门禁机 APK`、`Java 管理服务`、`Python 人脸向量比对服务` 三部分，首期聚焦“内部员工扫脸打卡”闭环。
- 适用对象：企业内部员工、考勤管理员、系统管理员、实施运维人员。
- 成功标准：
  - 门禁机完成实时人脸采集、活体检测、服务端比对、结果回显与打卡事件上报。
  - 首期支持 `500-5000` 员工人脸库规模。
  - 打卡链路必须实时在线，活体和识别双通过后立即生成一条打卡事件。
  - 管理端具备员工管理、人脸底库管理、打卡记录查询、设备基础管理能力。
  - 架构支持基础活体检测，并为更强活体、考勤规则、报表统计、合规安全扩展预留接口。

## Current State Analysis

- 当前工作区 `e:\other\local-rl` 为空，未发现现成代码、接口文档、设备 SDK 或历史架构资料。
- 当前没有可确认的门禁机品牌、CPU、内存、Android 版本、摄像头能力、厂商接口协议，因此方案需按“通用老款安卓门禁机”设计，并把硬件前置条件写入文档。
- 已明确的业务与技术决策：
  - 首期仅做人脸打卡，不包含排班、考勤规则、报表、薪资联动。
  - 在线比对采用 `Python 独立服务`。
  - 服务端管理能力采用 `Java` 开发。
  - 门禁机客户端采用 `Java 原生 Android` 开发。
  - 首期必须包含 `基础活体检测`，交互策略采用“静默活体优先，失败后降级动作活体”。
  - 打卡链路要求实时在线，不接受离线补传作为有效主链路。
  - 打卡规则采用“进出即打卡”，每次活体和识别双通过都生成一条事件。
  - 活体检测失败时直接拒绝，不生成有效打卡事件。
  - 安全目标为“首期基础可用 + 后续等保扩展预留”。

## PRD

### 1. 产品定位

- 产品名称：内网门禁人脸打卡系统。
- 产品目标：在老款安卓门禁机上实现稳定、低依赖、可控部署的企业员工扫脸打卡能力。
- 核心价值：
  - 替代传统刷卡或密码打卡，减少代打卡风险。
  - 通过内网闭环运行，满足内部部署诉求。
  - 通过 Java + Python 分层实现业务稳定性与算法可替换性。

### 2. 范围定义

#### 2.1 首期范围 In Scope

- 门禁机 APK：
  - 摄像头预览与抓拍。
  - 人脸检测触发。
  - 静默活体检测与动作活体降级引导。
  - 调用服务端识别接口。
  - 展示识别结果、员工姓名、工号、时间、结果状态。
  - 设备鉴权、心跳、基础参数拉取。
- Java 管理服务：
  - 员工档案管理。
  - 人脸底库管理。
  - 门禁设备管理。
  - 打卡事件接收、存储、查询。
  - 与 Python 比对服务的编排调用。
- Python 比对服务：
  - 活体检测。
  - 人脸图片特征提取。
  - 向量入库与更新。
  - TopK 检索与阈值判断。
  - 返回活体结果、候选员工和相似度。
- 管理后台最小能力：
  - 员工新增/导入/禁用。
  - 员工人脸注册与更新。
  - 打卡记录查询。
  - 设备在线状态查看。

#### 2.2 非首期范围 Out of Scope

- 高强度活体检测。
- 3D 深度活体或专用红外硬件改造。
- 自动开门控制联动。
- 班次、迟到早退、加班、请假、薪资等复杂考勤。
- 多园区多租户。
- 外网访问、小程序、公众端。
- 复杂 BI 报表。

### 3. 用户角色

- 普通员工：在门禁机前扫脸，完成打卡。
- 考勤管理员：维护员工信息、查看打卡记录。
- 系统管理员：维护设备、权限、系统参数。

### 4. 业务流程

#### 4.1 员工注册流程

1. 管理员创建员工档案。
2. 上传员工人脸照片或现场采集人脸。
3. Java 管理服务调用 Python 服务校验注册照片质量并提取特征向量。
4. Python 服务将向量写入向量索引，并返回 `faceId` / `embeddingVersion`。
5. Java 服务保存员工与人脸模板映射关系。

#### 4.2 扫脸打卡流程

1. 门禁机检测到人脸并进入静默活体检测。
2. 若静默活体置信度不足，APK 提示用户执行眨眼或轻微摇头等动作活体。
3. APK 将抓拍图、活体帧、设备编号、抓拍时间发送到 Java 管理服务。
4. Java 管理服务完成设备鉴权、请求校验、审计记录后调用 Python 比对服务。
5. Python 比对服务先执行活体检测，活体通过后再进行特征提取和向量检索，返回活体结果、最佳候选与相似度。
6. Java 管理服务结合活体结果、员工状态、阈值策略、黑名单或禁用状态做业务判定。
7. 活体或识别任一失败则直接拒绝，不生成有效打卡事件。
8. 双通过则写入一条打卡事件，并将姓名、工号、时间、结果返回设备。
9. 门禁机展示“识别成功/失败”，必要时给出活体失败提示。

#### 4.3 设备管理流程

1. 设备首次登记并分配唯一 `deviceCode` 与密钥。
2. 设备启动后先鉴权，再拉取参数。
3. 设备定时发送心跳，服务端更新在线状态。

### 5. 功能需求

#### 5.1 Android 门禁机 APK

- 基础要求：
  - Java 原生 Android 开发。
  - 兼容老款安卓设备，避免重量级依赖。
  - 支持横屏或竖屏单页打卡模式。
- 功能项：
  - 开机自启与前台常驻。
  - 摄像头预览。
  - 人脸进入框后自动抓拍。
  - 静默活体检测。
  - 静默失败后切换动作活体提示。
  - 并发保护，防止重复提交。
  - 与服务端 HTTPS/HTTP 内网通信。
  - 识别结果展示与语音播报预留。
  - 网络异常、服务不可用、超时提示。
  - 本地仅缓存运行配置，不落长期敏感人脸图片。
- 关键限制：
  - 实时在线模式下，服务端未返回成功前，不记为有效打卡。
  - 活体检测以服务端为主，设备端只做轻量交互编排和必要质量判断，避免在端侧做大模型推理。

#### 5.2 Java 管理服务

- 组织基础：
  - 部门、员工、设备、角色权限。
- 人脸底库：
  - 上传人脸。
  - 触发向量提取。
  - 查看人脸注册状态。
  - 更新/删除人脸模板。
- 打卡事件：
  - 查询员工打卡事件。
  - 按时间、设备、员工筛选。
  - 导出预留。
- 风险控制：
  - 活体结果记录。
  - 失败原因分类。
  - 阈值策略配置预留。
- 设备管理：
  - 设备注册。
  - 在线状态。
  - 参数配置。
  - 识别阈值和活体策略下发预留。
- 系统管理：
  - 操作日志。
  - 接口审计。
  - 参数中心。

#### 5.3 Python 活体与向量比对服务

- 人脸图片预处理。
- 静默活体检测。
- 动作活体验证。
- 向量提取。
- 向量索引构建与增删改。
- 相似度检索。
- 阈值比对。
- 模型版本管理。
- 返回统一活体与识别结果结构。

### 6. 非功能需求

- 性能：
  - 单次“活体 + 识别”端到端目标响应时间：`1.5s - 2.5s`，上限不超过 `4.0s`。
  - 首期支持 `500-5000` 人规模单库检索。
- 可用性：
  - Java 服务与 Python 服务支持局域网单机部署，后续可水平扩展。
  - 设备活体失败、识别失败需有可追溯日志。
- 安全：
  - 设备与服务端双向鉴权或签名鉴权。
  - 人脸原图、模板、向量分层存储。
  - 预留数据库加密与脱敏能力。
- 兼容性：
  - Android 端优先兼容 `Android 5-9`。
  - 尽量避免必须依赖 Google 服务。

### 7. 技术架构建议

#### 7.1 总体架构

- `Android APK`：负责采集、活体交互、设备态控制。
- `Java 管理服务`：作为统一业务中台，承接设备接入、人员管理、打卡落库、权限与审计。
- `Python 比对服务`：作为算法服务，承接活体检测、向量化与检索。
- `MySQL`：存储员工、设备、打卡事件、操作日志。
- `对象存储/文件存储`：存储注册人脸原图，可先使用本地 NAS 或内网文件服务。
- `向量索引组件`：建议使用 Python 生态成熟方案，例如 `FAISS` 或 `Milvus Lite / Qdrant`。

#### 7.2 推荐方案

- 首期推荐：
  - Java 管理服务：`Spring Boot`。
  - Android 客户端：Java + Camera2 或兼容旧设备的 Camera API。
  - Python 比对服务：`FastAPI` 或 `Flask` + 基础活体模型 + 人脸特征模型封装。
  - 向量索引：优先 `FAISS`。
- 推荐原因：
  - `FAISS` 对 `500-5000` 规模足够轻量，便于私有部署。
  - Python 负责活体与识别算法链路，可降低 Java 侧集成模型复杂度。
  - Java 服务保留业务主控，更适合员工、设备、权限和审计管理。

#### 7.3 不推荐方案

- 不建议在老款门禁机端直接做完整向量比对：
  - 设备性能与兼容性不可控。
  - 模型升级与人脸库更新维护成本高。
  - 容易导致 APK 体积与内存压力过大。

### 8. 关键接口设计

#### 8.1 Android -> Java 管理服务

- `POST /api/device/auth/login`
  - 设备鉴权登录。
- `POST /api/device/face/recognize`
  - 上传抓拍图和活体帧，触发活体与识别。
- `POST /api/device/heartbeat`
  - 设备心跳。
- `GET /api/device/config`
  - 拉取设备配置。

#### 8.2 Java 管理服务 -> Python 比对服务

- `POST /internal/face/register`
  - 注册员工人脸向量。
- `POST /internal/face/search`
  - 完成活体检测并检索人脸候选。
- `POST /internal/face/delete`
  - 删除向量模板。
- `GET /internal/model/version`
  - 查询模型版本。

#### 8.3 核心返回结构

```json
{
  "success": true,
  "employeeId": "E1024",
  "employeeName": "张三",
  "livenessResult": "PASS",
  "livenessMode": "SILENT",
  "livenessScore": 0.97,
  "similarity": 0.93,
  "threshold": 0.88,
  "recognizeResult": "MATCH",
  "traceId": "20260702XXXX"
}
```

### 9. 数据模型建议

#### 9.1 业务库表

- `employee`
  - `id`
  - `employee_no`
  - `name`
  - `status`
  - `department_id`
- `employee_face`
  - `id`
  - `employee_id`
  - `face_image_url`
  - `face_token`
  - `embedding_version`
  - `status`
- `device`
  - `id`
  - `device_code`
  - `device_name`
  - `secret_key`
  - `status`
  - `last_heartbeat_time`
- `attendance_event`
  - `id`
  - `employee_id`
  - `device_id`
  - `event_time`
  - `liveness_result`
  - `liveness_mode`
  - `liveness_score`
  - `similarity`
  - `result`
  - `capture_image_url`
  - `trace_id`
- `operation_log`
  - `id`
  - `operator_id`
  - `module`
  - `action`
  - `content`
  - `created_at`

#### 9.2 向量索引元数据

- `vector_id`
- `employee_id`
- `face_token`
- `embedding_version`
- `enabled`

### 10. 风险与约束

- 设备能力未知：
  - 需在立项前确认 CPU 架构、RAM、摄像头像素、是否支持 Camera2、系统版本、厂商限制。
- 网络依赖强：
  - 因要求实时在线，局域网稳定性会直接影响打卡体验。
- 基础活体能力有限：
  - 对高仿面具、复杂视频攻击的防护能力有限，需在二期评估更强活体策略。
- 算法效果依赖采集质量：
  - 光照、逆光、摄像头角度、人员姿态会影响识别率。

### 11. 验收标准

- 员工人脸注册成功后，可在门禁机完成扫脸识别。
- 活体和识别双通过时，后台生成一条打卡事件，包含员工、设备、时间、活体结果、相似度、追踪号。
- 禁用员工、人脸模板缺失、活体失败、低于阈值时，均返回失败且不生成有效打卡记录。
- 管理员可通过后台查询指定时间范围的打卡记录。
- 设备断开心跳后，后台可识别其离线状态。

## Proposed Changes

### 文档与工程初始化建议

- 新建 `e:\other\local-rl\docs\prd\门禁人脸打卡系统PRD.md`
  - 沉淀正式 PRD，对外作为产品和研发统一基线。
- 新建 `e:\other\local-rl\android-device-app\`
  - Android Java 原生门禁机 APK 工程。
- 新建 `e:\other\local-rl\java-attendance-server\`
  - Java 管理服务工程，承接业务与设备接入。
- 新建 `e:\other\local-rl\python-face-service\`
  - Python 向量比对服务工程。
- 新建 `e:\other\local-rl\deploy\`
  - 存放内网部署脚本、配置样例、数据库初始化脚本。

### Android 端建议文件

- `android-device-app/app/src/main/java/.../MainActivity.java`
  - 单页面识别主页，承载摄像头预览、结果展示。
- `android-device-app/app/src/main/java/.../camera/`
  - 摄像头采集与帧节流。
- `android-device-app/app/src/main/java/.../liveness/`
  - 活体引导、动作挑战、结果展示。
- `android-device-app/app/src/main/java/.../network/`
  - 服务端接口封装。
- `android-device-app/app/src/main/java/.../device/`
  - 设备注册、心跳、配置管理。

### Java 服务建议文件

- `java-attendance-server/src/main/java/.../device/`
  - 设备接入、鉴权、心跳。
- `java-attendance-server/src/main/java/.../employee/`
  - 员工与人脸业务管理。
- `java-attendance-server/src/main/java/.../attendance/`
  - 打卡事件落库、查询。
- `java-attendance-server/src/main/java/.../risk/`
  - 活体与识别联合判定、失败原因编码。
- `java-attendance-server/src/main/java/.../faceclient/`
  - 对 Python 比对服务的调用封装。
- `java-attendance-server/src/main/resources/db/migration/`
  - MySQL 初始化与版本迁移脚本。

### Python 服务建议文件

- `python-face-service/app/api/face.py`
  - 人脸注册、活体检索、删除接口。
- `python-face-service/app/service/liveness_service.py`
  - 静默活体与动作活体逻辑。
- `python-face-service/app/service/embedding_service.py`
  - 特征提取逻辑。
- `python-face-service/app/service/vector_index_service.py`
  - 向量索引增删查。
- `python-face-service/app/model/`
  - 请求响应模型定义。

## Assumptions & Decisions

- 决策：在线识别链路采用“Java 业务编排 + Python 向量比对”。
  - 原因：满足“服务端 Java 为主”的同时，保留 Python 在活体模型、向量库和模型集成上的优势。
- 决策：首期采用“基础活体 + 混合策略”。
  - 原因：兼顾老款设备性能、交互体验和首期防伪需求。
- 决策：活体失败直接拒绝。
  - 原因：首期以安全优先，不引入人工复核链路复杂度。
- 决策：不在设备端做完整向量检索。
  - 原因：降低设备性能风险和升级复杂度。
- 假设：内网具备稳定低延迟网络，设备到服务端单次请求延迟可控制在 `300ms` 级别。
- 假设：注册阶段可获得质量合格的员工人脸正脸照。
- 假设：后续若确认设备厂商提供稳定 SDK，可在不改变主架构的前提下替换摄像头/人脸检测实现。

## Verification Steps

1. 与业务方确认门禁机硬件参数、厂商能力、摄像头规格、Android 版本。
2. 与业务方确认是否存在“开门联动”或“班次考勤”二期范围。
3. 选择并验证 Python 活体模型、人脸模型与向量库方案，完成 `500-5000` 人规模性能基准测试。
4. 使用照片、翻拍屏幕、正常真人样本做基础活体验证。
5. 输出正式 PRD、接口文档、ER 图和部署拓扑图。
6. 按 `Android APK -> Java 服务 -> Python 比对服务 -> 联调` 的顺序进入实施。

## Implementation Steps

1. 先确认设备硬件与网络前置条件，冻结“活体 + 识别”链路边界。
2. 先产出正式 PRD 与原型，再同步接口契约。
3. 初始化三套工程骨架和公共规范。
4. 先完成员工、人脸、设备、打卡四类核心数据模型。
5. 完成 Python 活体检测、向量注册与检索服务。
6. 完成 Java 管理服务与 Python 服务对接。
7. 完成 Android 端抓拍、活体引导、上传、结果展示链路。
8. 完成联调、活体阈值调优、压测与验收。
