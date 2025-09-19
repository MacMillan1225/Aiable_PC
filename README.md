# Aiable PC Service

一个基于 Flask 的轻量级 PC 服务程序，支持通过 HTTP API 远程执行文件操作、进程管理和命令执行。

## 功能特性

- 🔐 **安全认证**: 基于 Token 的身份验证
- 📁 **文件操作**: 启动应用程序和文件
- ⚡ **进程管理**: 终止指定进程
- 💻 **命令执行**: 执行系统命令
- 🔄 **自动路由**: 根据配置自动注册 API 路由
- 📊 **详细日志**: 完整的操作日志记录

## 快速开始

### 安装依赖

```bash
pip install flask pyyaml psutil
```

### 运行服务

```bash
python service.py
```

服务将在配置的端口启动（默认：11220）

## 配置说明

### config.yaml 文件结构

```yaml
token: "your-secret-token"  # 认证令牌
host: "0.0.0.0"           # 监听地址（0.0.0.0 允许外网访问）
port: 11220               # 服务端口

items:
  # handleprogram 类型（自动展开为 openfile + killprocess）
  - type: handleprogram
    id: wechat            # 唯一标识符
    process_name: "Weixin.exe"  # 进程名（用于终止）
    path: "C:/path/to/Weixin.exe"  # 程序路径（用于启动）
    args: ""              # 启动参数
    remark: "操作微信"     # 备注说明

  # openfile 类型（启动文件/程序）
  - type: openfile
    id: qq
    path: "C:/path/to/QQ.exe"
    args: ""
    remark: "启动QQ"

  # killprocess 类型（终止进程）
  - type: killprocess
    id: qq
    process_name: "QQ.exe"
    remark: "关闭QQ"

  # runcommand 类型（执行命令）
  - type: runcommand
    id: list_files
    command: "dir"
    args: ""
    remark: "列出文件"
```

### 配置项说明

#### 通用字段
- `type`: 操作类型 (`handleprogram`, `openfile`, `killprocess`, `runcommand`)
- `id`: 唯一标识符（同一类型内必须唯一）
- `remark`: 备注说明（可选）

#### 类型特定字段
- **handleprogram**: 
  - `process_name`: 要终止的进程名
  - `path`: 要启动的程序路径
  - `args`: 启动参数

- **openfile**:
  - `path`: 文件/程序路径
  - `args`: 启动参数

- **killprocess**:
  - `process_name`: 要终止的进程名

- **runcommand**:
  - `command`: 要执行的命令
  - `args`: 命令参数

## API 使用

### 认证
所有请求需要在 Header 中包含认证令牌：
```
X-Auth-Token: your-secret-token
```

### 接口调用（示例）

根据配置的 items 自动生成路由：

```bash
# 启动程序
curl -H "X-Auth-Token: your-token" http://localhost:11220/openfile/qq

# 终止进程  
curl -H "X-Auth-Token: your-token" http://localhost:11220/killprocess/qq

# 执行命令
curl -H "X-Auth-Token: your-token" http://localhost:11220/runcommand/list_files

# 传递参数（追加到默认参数后）
curl -H "X-Auth-Token: your-token" "http://localhost:11220/openfile/steam?param1=value1&param2=value2"
```

## 贡献指南

### 代码结构

项目采用模块化设计，核心文件 `service.py` 包含：

1. **配置加载** (`config.yaml` 解析)
2. **路由注册** (自动根据配置生成 API 端点)
3. **命令处理器** (CommandHandler 类)
4. **认证中间件** (require_token 装饰器)

### 扩展新功能

如需添加新的操作类型，请遵循以下步骤：

#### 1. 在 CommandHandler 中添加处理方法

```python
@staticmethod
@require_token
def new_handler_type(param1, param2=""):
    try:
        # 实现你的功能逻辑
        logger.info(f"Executed new handler with {param1}")
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
```

#### 2. 在 register_routes 中添加路由注册

```python
elif item_type == "newtype":
    param1 = item.get("param1")
    param2 = item.get("param2", "")
    bound_handler = lambda p1=param1, p2=param2: CommandHandler.new_handler_type(p1, p2)
    app_instance.add_url_rule(f"/{item_type}/{item_id}", endpoint_name, bound_handler, methods=["GET"])
```

#### 3. 更新配置验证（如需要）

确保新类型在 `validate_unique_type_id` 和 `expand_items` 函数中得到正确处理。

### 提交要求

- 保持与现有代码风格一致
- 添加适当的错误处理和日志记录
- 更新配置文件示例
- 确保类型+ID 的唯一性验证
- 提供清晰的备注说明

### 配置驱动开发

当前实现采用配置驱动的方式：

1. **YAML 配置**: 所有操作通过 `config.yaml` 定义
2. **函数引用**: 处理器方法通过闭包绑定配置参数
3. **自动路由**: 根据配置项自动注册 Flask 路由

这种设计使得添加新功能只需：
- 在 YAML 中定义新的类型和参数
- 实现对应的处理器方法
- 添加路由注册逻辑

## 故障排除

### 常见问题

1. **端口占用**: 修改 `config.yaml` 中的端口号
2. **权限不足**: 以管理员权限运行
3. **文件不存在**: 检查配置中的路径是否正确
4. **进程找不到**: 确认进程名称准确

### 日志查看

日志文件位于：
- `./logs/log.txt` (主日志)
- 临时目录下的 `AiablePCService_log.txt` (备用日志)
