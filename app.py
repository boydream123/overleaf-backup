#!/usr/bin/env python3
from flask import Flask, request, jsonify, send_from_directory
import json
import os
import subprocess
from pathlib import Path
import threading
import schedule
import time
from datetime import datetime

app = Flask(__name__, static_folder='static')
CONFIG_FILE = 'config.json'

def get_default_config():
    """获取默认配置"""
    return {
        'server': {
            'host': '0.0.0.0',
            'port': 5000,
            'debug': False
        },
        'backup': {
            'overleaf_url': 'https://www.overleaf.com',
            'backup_dir': './Backup',
            'cookie': '',
            'keep_last': 5,
            'auto_backup': False,
            'backup_interval': 15,
            'timeout': 300
        },
        'projects': []
    }

def load_config():
    """加载配置文件"""
    if not os.path.exists(CONFIG_FILE):
        config = get_default_config()
        save_config(config)
        return config
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # 合并默认配置，确保所有字段都存在
            default = get_default_config()
            for key in default:
                if key not in config:
                    config[key] = default[key]
                elif isinstance(default[key], dict):
                    for subkey in default[key]:
                        if subkey not in config[key]:
                            config[key][subkey] = default[key][subkey]
            return config
    except json.JSONDecodeError:
        print("警告: 配置文件格式错误，使用默认配置")
        return get_default_config()

def save_config(config):
    """保存配置文件"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

# API 路由

@app.route('/')
def index():
    """主页"""
    return send_from_directory('static', 'index.html')

@app.route('/api/config', methods=['GET'])
def get_config():
    """获取配置"""
    config = load_config()
    # 创建安全的配置副本，隐藏敏感信息
    safe_config = json.loads(json.dumps(config))
    safe_config['backup']['cookie_set'] = bool(config['backup'].get('cookie'))
    if config['backup'].get('cookie'):
        safe_config['backup']['cookie'] = '***HIDDEN***'
    return jsonify(safe_config)

@app.route('/api/config/full', methods=['GET'])
def get_full_config():
    """获取完整配置（包括敏感信息）"""
    config = load_config()
    return jsonify(config)

@app.route('/api/config/server', methods=['POST'])
def update_server_config():
    """更新服务器配置"""
    config = load_config()
    data = request.json
    
    if 'host' in data:
        config['server']['host'] = data['host']
    if 'port' in data:
        config['server']['port'] = int(data['port'])
    if 'debug' in data:
        config['server']['debug'] = bool(data['debug'])
    
    save_config(config)
    return jsonify({'success': True, 'message': '服务器配置已更新，需要重启服务生效'})

@app.route('/api/config/backup', methods=['POST'])
def update_backup_config():
    """更新备份配置"""
    config = load_config()
    data = request.json
    
    if 'overleaf_url' in data:
        config['backup']['overleaf_url'] = data['overleaf_url']
    if 'backup_dir' in data:
        config['backup']['backup_dir'] = data['backup_dir']
    if 'cookie' in data and data['cookie'] not in ['', '***HIDDEN***']:
        config['backup']['cookie'] = data['cookie']
    if 'keep_last' in data:
        config['backup']['keep_last'] = int(data['keep_last'])
    if 'auto_backup' in data:
        config['backup']['auto_backup'] = bool(data['auto_backup'])
    if 'backup_interval' in data:
        config['backup']['backup_interval'] = int(data['backup_interval'])
    if 'timeout' in data:
        config['backup']['timeout'] = int(data['timeout'])
    
    save_config(config)
    
    # 重新设置定时任务
    if config['backup']['auto_backup']:
        setup_scheduler(config)
    
    return jsonify({'success': True, 'message': '备份配置已更新'})

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """获取项目列表"""
    config = load_config()
    return jsonify(config.get('projects', []))

@app.route('/api/projects', methods=['POST'])
def add_project():
    """添加项目"""
    config = load_config()
    data = request.json
    
    # 检查项目是否已存在
    for project in config.get('projects', []):
        if project['id'] == data['id']:
            return jsonify({'success': False, 'error': '项目 ID 已存在'}), 400
    
    new_project = {
        'id': data['id'],
        'name': data['name'],
        'enabled': data.get('enabled', True)
    }
    
    if 'projects' not in config:
        config['projects'] = []
    
    config['projects'].append(new_project)
    save_config(config)
    
    return jsonify({'success': True, 'message': '项目添加成功'})

@app.route('/api/projects/<int:index>', methods=['PUT'])
def update_project(index):
    """更新项目"""
    config = load_config()
    
    if index < 0 or index >= len(config.get('projects', [])):
        return jsonify({'success': False, 'error': '项目不存在'}), 404
    
    data = request.json
    if 'name' in data:
        config['projects'][index]['name'] = data['name']
    if 'id' in data:
        config['projects'][index]['id'] = data['id']
    if 'enabled' in data:
        config['projects'][index]['enabled'] = data['enabled']
    
    save_config(config)
    return jsonify({'success': True, 'message': '项目更新成功'})

@app.route('/api/projects/<int:index>/toggle', methods=['POST'])
def toggle_project(index):
    """切换项目启用状态"""
    config = load_config()
    
    if index < 0 or index >= len(config.get('projects', [])):
        return jsonify({'success': False, 'error': '项目不存在'}), 404
    
    config['projects'][index]['enabled'] = not config['projects'][index].get('enabled', True)
    save_config(config)
    
    return jsonify({'success': True, 'message': '状态切换成功'})

@app.route('/api/projects/<int:index>', methods=['DELETE'])
def delete_project(index):
    """删除项目"""
    config = load_config()
    
    if index < 0 or index >= len(config.get('projects', [])):
        return jsonify({'success': False, 'error': '项目不存在'}), 404
    
    deleted_project = config['projects'].pop(index)
    save_config(config)
    
    return jsonify({'success': True, 'message': f'项目 "{deleted_project["name"]}" 已删除'})

@app.route('/api/backup', methods=['POST'])
def run_backup():
    """手动执行备份"""
    try:
        result = subprocess.run(
            ['python3', 'backup.py'],
            capture_output=True,
            text=True,
            timeout=600  # 10 分钟超时
        )
        
        return jsonify({
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr,
            'timestamp': datetime.now().isoformat()
        })
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False, 
            'error': '备份超时（超过 10 分钟）',
            'output': '',
            'timestamp': datetime.now().isoformat()
        }), 500
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': str(e),
            'output': '',
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/backups/<project_id>', methods=['GET'])
def get_project_backups(project_id):
    """获取项目的备份文件列表"""
    config = load_config()
    backup_dir = Path(config['backup']['backup_dir']) / project_id
    
    if not backup_dir.exists():
        return jsonify([])
    
    backups = []
    for backup_file in sorted(backup_dir.glob('backup_*.zip'), key=lambda x: x.stat().st_mtime, reverse=True):
        backups.append({
            'filename': backup_file.name,
            'size': backup_file.stat().st_size,
            'size_human': format_size(backup_file.stat().st_size),
            'created': backup_file.stat().st_mtime,
            'created_date': datetime.fromtimestamp(backup_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify(backups)

@app.route('/api/status', methods=['GET'])
def get_status():
    """获取系统状态"""
    config = load_config()
    backup_dir = Path(config['backup']['backup_dir'])
    
    total_projects = len(config.get('projects', []))
    enabled_projects = len([p for p in config.get('projects', []) if p.get('enabled', True)])
    
    total_size = 0
    total_files = 0
    if backup_dir.exists():
        for file in backup_dir.rglob('backup_*.zip'):
            total_size += file.stat().st_size
            total_files += 1
    
    return jsonify({
        'total_projects': total_projects,
        'enabled_projects': enabled_projects,
        'total_backup_files': total_files,
        'total_backup_size': total_size,
        'total_backup_size_human': format_size(total_size),
        'auto_backup_enabled': config['backup'].get('auto_backup', False),
        'backup_interval': config['backup'].get('backup_interval', 15)
    })

def format_size(size_bytes):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

# 定时备份任务

def backup_job():
    """定时备份任务"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n[{timestamp}] 执行定时备份...")
    try:
        subprocess.run(['python3', 'backup.py'], timeout=600)
    except Exception as e:
        print(f"定时备份失败: {e}")

def run_scheduler():
    """运行定时任务调度器"""
    while True:
        schedule.run_pending()
        time.sleep(60)

def setup_scheduler(config=None):
    """设置定时任务"""
    # 清除现有任务
    schedule.clear()
    
    if config is None:
        config = load_config()
    
    if config['backup'].get('auto_backup'):
        interval = config['backup'].get('backup_interval', 15)
        schedule.every(interval).minutes.do(backup_job)
        print(f"✓ 已启用自动备份，间隔: {interval} 分钟")
        return True
    return False

# 全局调度器线程
scheduler_thread = None

def start_scheduler():
    """启动调度器线程"""
    global scheduler_thread
    if scheduler_thread is None or not scheduler_thread.is_alive():
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()

if __name__ == '__main__':
    # 创建 static 目录
    os.makedirs('static', exist_ok=True)
    
    # 加载配置
    config = load_config()
    server_config = config.get('server', {})
    
    # 设置定时任务
    if setup_scheduler(config):
        start_scheduler()
    
    print("="*60)
    print("          Overleaf 备份管理系统 v1.0")
    print("="*60)
    print(f"✓ 服务器地址: http://{server_config.get('host', '0.0.0.0')}:{server_config.get('port', 5000)}")
    if server_config.get('host') == '0.0.0.0':
        print(f"✓ 本地访问: http://localhost:{server_config.get('port', 5000)}")
    print(f"✓ 备份目录: {Path(config['backup']['backup_dir']).absolute()}")
    print(f"✓ 配置文件: {Path(CONFIG_FILE).absolute()}")
    print("="*60)
    
    app.run(
        host=server_config.get('host', '0.0.0.0'),
        port=server_config.get('port', 5000),
        debug=server_config.get('debug', False)
    )