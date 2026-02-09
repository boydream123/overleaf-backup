# Overleaf 备份管理系统

这个是我利用大模型制作一个overleaf的备份方案，支持overleaf，overleaf社区版，overleaf-cep等。这是一个完整的 Overleaf 项目备份解决方案，支持多项目管理、自动定时备份和 Web 可视化配置。

## 功能特性

- ✅ 多项目管理：支持同时管理多个 Overleaf 项目
- ✅ 自动备份：可配置定时自动备份（分钟级精度）
- ✅ 版本控制：每个项目独立保存，自动清理旧备份
- ✅ Web 界面：友好的可视化配置界面
- ✅ 完整配置：所有参数可通过 config.json 配置
- ✅ 实时监控：显示备份统计和系统状态

## 安装步骤

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置系统

编辑 `config.json` 文件：

```json
{
  "server": {
    "host": "0.0.0.0",      # 监听地址，0.0.0.0 允许外部访问
    "port": 5000,            # Web 服务端口
    "debug": false           # 调试模式
  },
  "backup": {
    "overleaf_url": "https://overleaf.boydream.work",  # Overleaf 服务器地址
    "backup_dir": "./Backup",                          # 备份存储目录
    "cookie": "",                                      # 身份验证 Cookie
    "keep_last": 5,                                    # 每个项目保留备份数
    "auto_backup": false,                              # 是否启用自动备份
    "backup_interval": 15,                             # 自动备份间隔（分钟）
    "timeout": 300                                     # 下载超时时间（秒）
  },
  "projects": []                                       # 项目列表
}
```

### 3. 获取 Cookie

1. 在浏览器中登录你的 Overleaf
2. 按 F12 打开开发者工具
3. 进入 Network (网络) 标签
4. 刷新页面
5. 点击任意请求，在 Request Headers 中找到 Cookie
6. 复制完整的 Cookie 值到配置文件

### 4. 启动服务

```bash
python3 app.py
```

### 5. 访问 Web 界面

在浏览器中打开: `http://localhost:5000`

## 使用说明

### Web 界面操作

1. **项目管理**：添加、启用/禁用、删除项目
2. **手动备份**：点击按钮立即执行备份
3. **配置设置**：修改所有系统参数

### 命令行备份

```bash
python3 backup.py
```

### 自动备份

在 config.json 中设置：

```json
{
  "backup": {
    "auto_backup": true,
    "backup_interval": 15
  }
}
```

重启服务后自动生效。

### 后台运行

使用 nohup:

```bash
nohup python3 app.py > app.log 2>&1 &
```

使用 systemd (推荐):

```bash
sudo nano /etc/systemd/system/overleaf-backup.service
```

内容：

```ini
[Unit]
Description=Overleaf Backup Service
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/overleaf-backup
ExecStart=/usr/bin/python3 /path/to/overleaf-backup/app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable overleaf-backup
sudo systemctl start overleaf-backup
```

## 配置文件说明

### 服务器配置 (server)

- `host`: 监听地址
  - `0.0.0.0`: 允许所有 IP 访问
  - `127.0.0.1`: 仅本机访问
- `port`: Web 服务端口 (1-65535)
- `debug`: 调试模式，开发时使用

### 备份配置 (backup)

- `overleaf_url`: Overleaf 服务器地址
- `backup_dir`: 备份文件存储路径
- `cookie`: 身份验证 Cookie（从浏览器获取）
- `keep_last`: 每个项目保留的备份数量
- `auto_backup`: 是否启用自动定时备份
- `backup_interval`: 自动备份间隔（分钟）
- `timeout`: 单个项目下载超时时间（秒）

### 项目配置 (projects)

每个项目包含：

```json
{
  "id": "697f752d1b7f3f586b45ed5e",  # 项目 ID
  "name": "我的论文",                 # 项目名称
  "enabled": true                     # 是否启用备份
}
```

## 目录结构

```
overleaf-backup/
├── app.py              # Flask Web 服务器
├── backup.py           # 备份脚本
├── config.json         # 配置文件
├── requirements.txt    # Python 依赖
├── static/
│   └── index.html      # Web 前端界面
└── Backup/             # 备份存储目录
    └── {project_id}/
        ├── backup_20260209_120000.zip
        ├── backup_20260209_121500.zip
        └── ...
```

## 常见问题

### 1. Cookie 失效

症状：备份失败，提示不是 ZIP 文件
解决：重新从浏览器获取 Cookie 并更新配置

### 2. 端口被占用

症状：启动失败，提示端口已被使用
解决：在 config.json 中修改 `server.port` 为其他端口

### 3. 自动备份不工作

症状：设置了自动备份但没有执行
解决：

- 确保 `auto_backup` 设置为 `true`
- 重启服务使配置生效
- 检查日志确认定时任务是否启动

### 4. 备份文件过大

症状：磁盘空间不足
解决：减少 `keep_last` 的值，保留更少的备份

## License

MIT
