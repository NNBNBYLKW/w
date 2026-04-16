# Windows 本地资产管理工作台 后端脚手架初始化建议 v1

## 1. 文档目的

本文件用于把《技术架构初稿》《数据库 Schema 与 API 草案 v1》《开发任务拆解文档 v1》继续下沉到**本地应用服务脚手架层**。

当前目标不是写完整业务实现，而是先明确：
- 后端项目初始化时应先创建哪些目录
- 应先落哪些 router / service / repository / task 壳文件
- 数据库、模型、schema、任务运行时应先建哪些骨架
- 哪些文件适合先放占位实现，保证主链能尽快串起来
- 第一批后端代码骨架应该按什么顺序搭建

本文件的核心目标是：

> **把后端架构文档翻译成第一批真实目录、文件与模块壳。**

这样你后面无论自己写、交给开发者，还是交给代码模型执行，都可以从一个清晰且克制的骨架开始，而不是从空服务反复讨论结构。

---

## 2. 初始化总原则

### 2.1 总体原则
1. **先搭运行底座，再搭数据模型，再搭扫描/查询主链**
2. **先建目录与占位文件，再逐步填业务实现**
3. **先服务第一阶段主链，不为未来功能过度设计**
4. **扫描源、文件索引、查询、标签、详情、任务状态必须尽早有壳**
5. **router / service / repository / task 边界从第一天开始就要清楚**

### 2.2 当前不建议的初始化方式
不建议：
- 一上来把未来所有垂类库模块都建齐
- 一上来做非常重的插件系统 / 命令总线 / 事件总线
- 一上来把 repository 写成全能业务层
- 一上来做复杂调度器 / worker 集群 / 消息队列
- 一上来把 AI、在线抓取、复杂自动化都塞进服务骨架

初始化的目标不是“像企业大平台”，而是：

> **保证本地资产管理主链的应用服务骨架足够稳。**

---

## 3. 后端目录结构总览（建议）

以下是一套适合第一阶段本地应用服务的目录结构建议：

```text
app/
  api/
    routes/
    deps/
    schemas/
  core/
    config/
    logging/
    errors/
    runtime/
  db/
    models/
    session/
    migrations/
  services/
    source_management/
    scanning/
    querying/
    tagging/
    details/
    media/
    library_mapping/
    tasks/
    system/
  repositories/
    source/
    file/
    tag/
    library_item/
    thumbnail/
    task/
  workers/
    scanning/
    thumbnails/
    metadata/
  utils/
  main.py
```

### 3.1 为什么采用这套分层
因为第一阶段后端真正需要解决的是：
- 本地服务启动
- 数据库初始化
- 扫描源管理
- 文件索引
- 搜索查询
- 标签写入
- 详情读取
- 缩略图 / 元数据后台任务

这套结构能在不过度设计的前提下，把：
- API 层
- 业务层
- 数据层
- 后台任务层

分开。

---

## 4. 各层职责说明

## 4.1 api/

### 作用
承载 HTTP / IPC 入口层，不放具体业务规则。

### 建议子目录

#### api/routes/
存放按资源或领域划分的路由文件，例如：
- `sources.py`
- `search.py`
- `files.py`
- `media.py`
- `tags.py`
- `recent.py`
- `tasks.py`
- `system.py`

#### api/deps/
存放：
- DB session 依赖
- 配置依赖
- 可能的分页依赖

#### api/schemas/
存放 API 层请求/响应 schema，例如：
- `common.py`
- `source.py`
- `file.py`
- `tag.py`
- `media.py`
- `task.py`

### api/ 层不应放的东西
- 扫描业务逻辑
- 标签写入业务逻辑
- 查询 SQL 细节
- 任务调度逻辑

API 层原则上只做：
- 参数接收
- 调用 service
- 返回 response schema

---

## 4.2 core/

### 作用
承载应用级公共底座，不承载具体业务域逻辑。

### 建议子目录

#### core/config/
- 配置读取
- 环境变量
- 路径配置
- 数据库路径、缓存路径、缩略图路径等

#### core/logging/
- logger 初始化
- 日志格式
- 文件日志 / 控制台日志策略

#### core/errors/
- 自定义异常
- 错误码定义
- API 错误转换

#### core/runtime/
- 应用启动钩子
- 运行状态摘要
- 轻量 runtime registry（如需要）

### 说明
core/ 必须克制，只放全局公共能力。
不要把具体领域服务偷偷放进 core/。

---

## 4.3 db/

### 作用
承载数据库连接、会话、模型、迁移骨架。

### 建议子目录

#### db/models/
存放 ORM 模型：
- `source.py`
- `file.py`
- `file_metadata.py`
- `tag.py`
- `file_tag.py`
- `file_user_meta.py`
- `library_item.py`
- `thumbnail.py`
- `task.py`

#### db/session/
存放：
- engine 初始化
- session factory
- session dependency

#### db/migrations/
存放：
- migration 初始化逻辑
- 第一阶段 schema baseline

### 原则
- 模型层只定义数据结构与关系
- 不在 ORM model 里塞复杂业务方法

---

## 4.4 services/

### 作用
作为应用服务层，是第一阶段后端真正的业务中心。

### 建议子目录

#### services/source_management/
职责：
- 添加 / 删除 / 启用 / 禁用扫描源
- 调用扫描任务

#### services/scanning/
职责：
- 目录扫描编排
- 批量发现文件
- 重扫逻辑
- 同步 files 表

#### services/querying/
职责：
- 全局搜索
- 全部文件列表
- 最近导入
- 通用分页 / 排序 / 过滤协同

#### services/tagging/
职责：
- 创建标签
- 给文件加标签 / 移除标签
- 设置颜色标签
- 标签查询

#### services/details/
职责：
- 详情读取
- 详情 view model 组装

#### services/media/
职责：
- 媒体元数据提取协调
- 素材库查询
- 缩略图状态消费

#### services/library_mapping/
职责：
- File → LibraryItem 的映射规则
- 第一阶段重点支持 media

#### services/tasks/
职责：
- 任务创建
- 状态更新
- 简单任务查询

#### services/system/
职责：
- 健康检查
- 系统状态摘要

### 原则
Service 层必须拥有：
- 业务规则
- 状态变更
- 事务边界
- 多 repository 协调

---

## 4.5 repositories/

### 作用
承载数据访问，保持克制，不接管业务规则。

### 建议子目录

#### repositories/source/
#### repositories/file/
#### repositories/tag/
#### repositories/library_item/
#### repositories/thumbnail/
#### repositories/task/

### repository 层允许做的事
- 查询
- add
- update
- flush
- 常见条件封装

### repository 层不应做的事
- commit / rollback 决策
- 复杂业务状态切换
- 跨多个领域对象的完整流程编排

---

## 4.6 workers/

### 作用
承载后台任务执行实现。

### 建议子目录

#### workers/scanning/
- 实际目录遍历
- 扫描结果产出

#### workers/thumbnails/
- 图片缩略图生成
- 视频封面提取（基础版）

#### workers/metadata/
- 宽高 / 时长等扩展元数据提取

### 说明
workers/ 应偏“执行器”，不应自己决定业务语义。
它们应由 service 或 task runtime 调用。

---

## 5. 第一批应创建的目录

建议第一天先创建：

```text
app/
  api/routes/
  api/schemas/
  core/config/
  core/errors/
  core/logging/
  db/models/
  db/session/
  repositories/source/
  repositories/file/
  repositories/tag/
  repositories/task/
  services/source_management/
  services/scanning/
  services/querying/
  services/tagging/
  services/details/
  services/tasks/
  services/system/
  workers/scanning/
  workers/metadata/
  workers/thumbnails/
```

### 5.1 为什么先不建太多
第一天不必先建：
- library_mapping/ 下全部细分文件
- media/ 的复杂扩展目录
- library_item / thumbnail repository 全量文件
- migrations 的复杂历史链

第一阶段先把主链骨架搭起来即可。

---

## 6. 第一批必须创建的文件清单

## 6.1 入口与运行底座

### `app/main.py`
职责：
- 应用入口
- 初始化 app
- 注册 routes
- 注册 startup / shutdown

### `app/core/config/settings.py`
职责：
- 读取数据库路径、缓存路径、缩略图路径、日志级别等配置

### `app/core/logging/setup.py`
职责：
- 初始化 logger

### `app/core/errors/exceptions.py`
职责：
- 自定义异常类型

### `app/core/errors/handlers.py`
职责：
- API 层统一错误处理

### `app/db/session/engine.py`
职责：
- 初始化数据库 engine

### `app/db/session/session.py`
职责：
- Session factory
- get_db 依赖

### `app/db/models/base.py`
职责：
- ORM Base

---

## 6.2 第一批 ORM 模型文件

建议先建：

### `app/db/models/source.py`
### `app/db/models/file.py`
### `app/db/models/file_metadata.py`
### `app/db/models/tag.py`
### `app/db/models/file_tag.py`
### `app/db/models/file_user_meta.py`
### `app/db/models/task.py`

### 第二批再建
### `app/db/models/library_item.py`
### `app/db/models/thumbnail.py`

虽然它们第一阶段很重要，但可在 scanning / media 进入时补齐，不必抢第一天。

---

## 6.3 第一批 API 路由文件

建议先建：

### `app/api/routes/system.py`
- 健康检查
- 系统状态摘要占位

### `app/api/routes/sources.py`
- 扫描源 CRUD
- 触发扫描

### `app/api/routes/search.py`
- 全局搜索

### `app/api/routes/files.py`
- 文件详情
- 全部文件页查询
- 颜色标签设置
- 标签增删

### 第二批补：
### `app/api/routes/media.py`
### `app/api/routes/tags.py`
### `app/api/routes/recent.py`
### `app/api/routes/tasks.py`

---

## 6.4 第一批 API schema 文件

建议先建：

### `app/api/schemas/common.py`
包含：
- 分页响应
- 通用错误响应
- 简单 message response

### `app/api/schemas/source.py`
包含：
- SourceCreateRequest
- SourceUpdateRequest
- SourceResponse
- TriggerScanResponse

### `app/api/schemas/file.py`
包含：
- FileListItemResponse
- FileDetailResponse
- SetColorTagRequest
- AddFileTagRequest

### 第二批补：
### `tag.py`
### `media.py`
### `recent.py`
### `task.py`

---

## 6.5 第一批 repository 文件

建议先建：

### `app/repositories/source/repository.py`
职责：
- get_sources
- get_source_by_id
- get_source_by_path
- add_source
- update_source

### `app/repositories/file/repository.py`
职责：
- add_or_update_file_batch
- get_file_by_id
- search_files
- list_files_by_parent
- list_recent_files

### `app/repositories/tag/repository.py`
职责：
- get_tag_by_name
- create_tag
- attach_tag_to_file
- remove_tag_from_file
- list_tags

### `app/repositories/task/repository.py`
职责：
- create_task
- update_task_status
- get_task_by_id
- list_tasks

### 第二批补：
### `library_item/repository.py`
### `thumbnail/repository.py`

---

## 6.6 第一批 service 文件

建议先建：

### `app/services/system/service.py`
职责：
- health/status 逻辑

### `app/services/source_management/service.py`
职责：
- 扫描源增删改查
- 触发扫描任务

### `app/services/scanning/service.py`
职责：
- 扫描编排
- 调用 scanning worker
- 批量写入 files

### `app/services/querying/service.py`
职责：
- 搜索页查询
- 全部文件页查询
- 最近导入查询（可先占位）

### `app/services/details/service.py`
职责：
- 文件详情 view model 组装

### `app/services/tagging/service.py`
职责：
- 标签创建
- 文件标签增删
- 颜色标签设置

### `app/services/tasks/service.py`
职责：
- task 创建与状态更新

### 第二批补：
### `app/services/media/service.py`
### `app/services/library_mapping/service.py`

---

## 6.7 第一批 worker 文件

建议先建：

### `app/workers/scanning/scanner.py`
职责：
- 遍历目录
- 产出基础文件记录数据

### `app/workers/metadata/extractor.py`
职责：
- 提取基础扩展元数据（初期可先只定义接口）

### `app/workers/thumbnails/generator.py`
职责：
- 图片缩略图 / 视频封面生成（初期可先只定义接口）

### 原则
workers 第一批可以先是占位壳，但接口方向要先稳定。

---

## 7. 第一批工具与常量文件建议

### `app/utils/file_types.py`
定义文件类型识别常量

### `app/utils/path_ops.py`
路径标准化、父目录提取等

### `app/utils/pagination.py`
分页参数处理

### `app/utils/time_utils.py`
时间辅助函数

### `app/utils/task_status.py`
任务状态常量

---

## 8. 第一批文件内容建议：哪些先放占位

### 8.1 可以先放占位实现的文件
- `media/service.py`
- `library_mapping/service.py`
- `workers/metadata/extractor.py`
- `workers/thumbnails/generator.py`
- `api/routes/recent.py`
- `api/routes/media.py`
- `api/routes/tags.py`
- `api/routes/tasks.py`

### 8.2 占位文件不应只是空文件
至少应包含：
- 明确 module 职责注释
- 预留函数签名
- TODO / NotImplemented 说明

这样后续不会因为“文件虽然建了，但谁也不知道怎么接”而返工。

---

## 9. 推荐初始化顺序（文件级）

## Step 1：先让服务能启动
1. `main.py`
2. `settings.py`
3. `engine.py`
4. `session.py`
5. `base.py`
6. `system.py` route + service

### 结果
- 本地应用服务可启动
- 健康检查可用

---

## Step 2：先让数据库骨架成立
1. source model
2. file model
3. tag model
4. file_tag model
5. file_user_meta model
6. task model
7. migration baseline

### 结果
- 核心表可初始化

---

## Step 3：先搭扫描源主链
1. source schema
2. source repository
3. source_management service
4. sources route

### 结果
- 扫描源可增删改查

---

## Step 4：先搭扫描与任务主链
1. scanner worker
2. scanning service
3. task repository
4. tasks service
5. 触发扫描接口

### 结果
- 可以发起扫描任务
- 可以把文件基础数据写入 files

---

## Step 5：先搭查询与详情主链
1. file repository 查询方法
2. querying service
3. details service
4. search route
5. files route
6. file schema

### 结果
- 搜索与详情接口成立

---

## Step 6：再搭标签主链
1. tag repository
2. tagging service
3. files route 中标签写接口
4. tags route（可随后补）

### 结果
- 可给文件加标签、颜色标签

---

## Step 7：最后补媒体与最近导入骨架
1. metadata extractor
2. thumbnails generator
3. media service
4. recent route/query
5. media route/query

### 结果
- 开始接入素材库与最近导入能力

---

## 10. 推荐最小提交里程碑

### Commit A：服务启动与数据库骨架
应包含：
- app 可启动
- db 初始化
- /health 或 /system/status

### Commit B：扫描源主链
应包含：
- sources model / schema / route / service / repository

### Commit C：扫描与任务主链
应包含：
- scanner worker
- scanning service
- tasks 基础链路

### Commit D：搜索与详情主链
应包含：
- search route
- file detail route
- querying/details service

### Commit E：标签主链
应包含：
- tag repository/service
- add/remove tag
- set color tag

### Commit F：媒体与最近导入骨架
应包含：
- metadata/thumbnails 占位或基础实现
- media/recent route

这样每次提交都能对应文档里的阶段价值，而不是“改了很多但不知道真正完成了什么”。

---

## 11. 第一批最该先跑通的后端主链

当前最推荐先跑通这一组：

### 主链 1
`sources route` → `source_management service` → `source repository`

### 主链 2
`trigger scan` → `tasks service` → `scanner worker` → `file repository`

### 主链 3
`search route` → `querying service` → `file repository`

### 主链 4
`file detail route` → `details service` → `file repository`

### 主链 5
`set tag / color tag` → `tagging service` → `tag/file repository`

只要这五条后端主链骨架先成立，前端就能开始真正对接核心页面。

---

## 12. 当前最应避免的后端脚手架问题

### 12.1 问题：router 直接写业务逻辑
后果：
- API 层迅速变厚
- 事务边界混乱
- 测试与复用困难

### 12.2 问题：repository 变成全能 service
后果：
- 数据访问层与业务层混在一起
- 规则分散，后续难维护

### 12.3 问题：workers 自己决定业务语义
后果：
- 任务执行逻辑和业务规则耦合
- 调用关系难以控制

### 12.4 问题：一上来就做复杂任务调度平台
后果：
- 第一阶段成本失控
- 偏离本地工作台主线

### 12.5 问题：先把未来所有模块全建出来
后果：
- 看起来完整，但真正主链依然不清楚

### 12.6 当前建议
始终围绕：
> **扫描源 → 扫描 → 写入 files → 搜索 / 详情 → 标签 / 颜色标签**
来决定第一批要建哪些模块和文件。

---

## 13. 当前结论

这份后端脚手架初始化建议的核心不是“把目录搭得像企业平台”，而是：

> **先把最关键的 router 壳、service 壳、repository 壳、worker 壳、schema 壳、model 壳搭起来，让整个本地应用服务从第一天开始就朝统一业务中心而不是零散脚本集合发展。**

只要这一点成立，后续再接媒体库、最近导入、任务状态、缩略图策略，都会稳得多。

---

## 14. 下一步建议

在这份文档之后，最适合继续推进的方向有两个：
1. **真正开始生成前后端骨架代码**
2. **项目执行入口文档 / README v1**

如果你还想继续保持“先定执行入口，再开始写代码”的节奏，我更推荐下一步做：

> **项目执行入口文档 / README v1**

因为到这里前后端脚手架都已经有了，再补一份统一入口文档，就能把“先看什么、先跑什么、先做什么、阶段顺序是什么”彻底收口。

