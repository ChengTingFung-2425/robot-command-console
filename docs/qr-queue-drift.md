## QR 队列 URL 与 WebUI 扫码获取机器人信息 — 规划更新（Drift）

更新时间: 2025-10-30

概述
--
每台机器人在项目中应配有一个“队列 URL”（queue URL），用于项目统一管理与快速访问。该 URL 需要以 QR 码形式提供，让用户通过 WebUI 或移动设备扫码后，快速获取并展示该机器人的信息与管理入口。

目标
--
- 定义队列 URL 的格式与安全契约。
- 在机器人注册/部署流程中生成并展示 QR（用于贴纸、控制台或 UI）。
- 在 WebUI 中提供扫码能力：打开摄像头扫码、解析 URL、调用后端接口获取机器人信息并在 UI 中展示。

简短契约（Inputs / Outputs / Errors）
--
- 输入: QR 中编码的队列 URL，例如: `https://console.example.com/queue/robots/{robot_id}?t={token}`。
- 输出: 机器人信息 JSON（id, name, status, last_seen, capabilities, queue_metadata 等）。
- 错误模式: 无效/过期 token、未知 robot_id、权限不足（401/403）、网络或解析失败（400/500）。

队列 URL 格式（建议）
--
- 基本格式: https://<HOST>/queue/robots/{robot_id}?t=<queue_token>
- 说明:
  - `robot_id`：UUID 或数据库主键，唯一标识机器人。
  - `t`：一次性或短期有效的队列访问 token（短期签名字符串），用于防止公开的永久链接导致未授权访问。

QR 编码策略
--
- 将完整队列 URL 以 UTF-8 文本编码为 QR。QR 内容仅包含 URL（不再额外封装 JSON）。
- 在生产环境中，token 推荐有效期短（例如 1 小时），并可在需要时重新生成。

后端设计（API / 数据）
--
1) 新字段/迁移：
   - 在 robots 表添加 `queue_token` 或 `queue_token_version`（如果短期 token 存储/管理需要）。
   - 或仅在创建时生成队列 URL 并不长期保存 token（使用签名 URL 或 JWT 签发）。

2) 推荐端点:
   - GET /api/robots/{robot_id}?queue_token={t}
     - 功能: 根据 robot_id + token 返回机器人摘要信息。
     - 认证: 如果存在会话（已登录），可以选择忽略 token 或额外校验 token 权限。
   - POST /api/robots/{robot_id}/queue/regenerate
     - 功能: 管理员重置/生成新的 queue token（返回新的队列 URL）。

3) 验证与安全:
   - token 应包含到期时间并通过 HMAC 或 JWT 签名验证。
   - 不要在 QR 中携带敏感长期凭证。
   - 后端需记录 token 使用/解析的审计日志（避免滥用）。

前端 WebUI 设计
--
1) 扫码入口：
   - 在 WebUI 加入“扫描 QR 获取机器人”按钮（可放在机器人列表页或主导航）。
   - 点击后打开一个模态框，询问摄像头访问权限并开始实时识别 QR（使用 `getUserMedia` + JS QR 库，如 `jsQR` 或 `zxing-js/library`）。

2) 扫码流程：
   - 解析到 URL 后，做快速校验：确认 URL host 与 path 模式 `/queue/robots/{id}`，并安全提取 `robot_id` 与 `t`。
   - 调用后端 API（如 `GET /api/robots/{robot_id}?queue_token={t}`）获取机器人信息。
   - 成功后在模态中展示信息摘要（名称、状态、最后在线、能力、管理链接），并提供跳转到机器人管理界面或添加到监控队列的操作。

3) UX 与降级:
   - 若用户拒绝摄像头权限，允许手动粘贴队列 URL 的输入框。
   - 扫码结果若包含非本域 URL，展示警告并询问用户是否继续（防止钓鱼）。

边界条件与常见用例
--
- 场景: 线下贴纸 QR（部署现场）— 用户用手机浏览器或 WebUI 扫码打开并快速查看机器人状态。
- 场景: 运维在控制台需要快速加入机器人到管理队列。

潜在问题与对策
--
- 摄像头权限被拒绝：提供手工粘贴 URL 的备用路径。
- QR 被篡改或 URL 格式错误：在前端做最大程度的校验，并在后端做严格验证与日志记录。
- Token 被截获：使用短期签名 token，必要时要求登录二次校验或 MFA。

验收标准（可测试项）
--
1) 生成与展示：机器人注册流程能为机器人生成符合格式的队列 URL，并能把该 URL 渲染为 QR（可打印/下载）。
2) 扫码并获取信息（WebUI）：在桌面 Chrome/Firefox 中打开 WebUI，点击“扫描 QR”，允许摄像头后，扫码能立刻展示机器人摘要并提供管理跳转（成功率 >= 95%）。
3) 错误处理：
   - 无效或过期 token 返回 401/403 并在 UI 展示明确提示。
   - 非预期 URL 展示警告并阻止自动跳转。
4) 自动化测试覆盖：后端对 token 验证的单元测试与集成测试，前端对解析流程的单元/集成测试或手动 QA 测试说明文件。

实施里程碑（建议短期计划）
--
Week 0 (规划)：完成本 drift 文档并评审（现在）。
Week 1：后端签名 URL 方案实现 + 生成 QR 的 API（含单元测试）。
Week 2：前端扫码组件（modal）实现 + 基础 UX（含手工粘贴备用）。
Week 3：集成测试与安全评审、上线灰度。

小的实现细节/代码片段（示例）
--
- Token 签名（伪代码）:
  - payload = { robot_id, exp: now + 3600 }
  - token = base64url( HMAC_SIGN(secret, payload) + '.' + payload )

风险与假设
--
- 假设当前系统可以在机器人注册时触发生成队列 URL 的逻辑（若没有，需要在后端新增迁移与写入点）。
- 假设 WebUI 有权限使用摄像头（浏览器支持 getUserMedia）。

下一步 / 建议任务分配
--
1) 后端工程师：实现签名队列 URL 的生成与验证端点，添加必要数据库迁移。
2) 前端工程师：实现扫码模态、解析与调用后端接口，并实现可用的错误提示与手动粘贴路径。
3) QA/测试：编写集成测试与手动测试脚本，覆盖常见相机与手机浏览器场景。

