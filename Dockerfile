FROM python:3.11-slim-bookworm

# 设置工作目录
WORKDIR /app


# 配置 pip 使用国内镜像源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set install.trusted-host mirrors.aliyun.com

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建备份目录和配置目录
RUN mkdir -p /app/Backup /app/static

# 暴露端口
EXPOSE 5000

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 启动应用
CMD ["python", "app.py"]