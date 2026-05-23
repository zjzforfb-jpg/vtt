# Subtitle Proofreading API

自动字幕校对系统，支持中英文字幕的智能校对、大小写修正和标点符号添加。

## 项目结构

```
SubtitleProofreading/
├── api/                          # 后端API
│   ├── main.py                   # FastAPI主入口
│   ├── requirements.txt          # Python依赖
│   └── srt_processor/            # 字幕处理核心模块
│       ├── __init__.py
│       ├── srt_parser.py         # SRT文件解析器
│       ├── text_matcher.py       # 文本匹配对齐算法
│       ├── text_corrector.py     # 文本修正（大小写、标点）
│       └── processor.py          # 主处理流程
├── frontend/                     # 前端页面
│   └── index.html                # 网页界面
├── start.sh                      # 启动脚本
├── ep047.srt                     # 示例原字幕
├── 47-字幕.srt                   # 示例识别字幕
└── test_processor.py             # 测试脚本
```

## 功能特性

1. **SRT文件解析**: 支持原字幕（含中文+英文）和识别字幕（纯英文）格式
2. **智能文本对齐**: 基于相似度算法自动匹配原字幕和识别字幕
3. **大小写修正**: 句首大写、专有名词大写、代词"I"大写
4. **标点符号添加**: 自动识别疑问句、感叹句、陈述句并添加对应标点
5. **缩写修正**: 自动修正常见英文缩写（don't, can't, I'm等）
6. **差异检测**: 识别字幕中多余或缺失的内容提示
7. **跨域支持**: 已配置CORS，支持前后端分离部署

## 快速开始

### 1. 安装依赖

```bash
cd api
pip install -r requirements.txt
```

### 2. 启动API服务器

```bash
# 方式1: 使用启动脚本
./start.sh

# 方式2: 直接运行
cd api && python main.py
```

服务器默认运行在 `http://localhost:8000`

### 3. 测试API

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 使用测试脚本
python test_processor.py
```

### 4. 访问前端页面

用浏览器打开 `frontend/index.html`

## API接口文档

### 1. 文件上传方式校对

**POST** `/api/v1/proofread`

请求参数:
- `original_srt`: 原字幕文件 (.srt)
- `recognized_srt`: 识别字幕文件 (.srt)

响应示例:
```json
{
  "success": true,
  "data": {
    "corrected_srt": "1\n00:00:00,100 --> 00:00:01,533\nStella, you have to help me.\n\n...",
    "stats": {
      "total_recognized_entries": 30,
      "total_original_entries": 27,
      "total_corrections": 15,
      "missing_in_recognized": 3,
      "corrections": [...],
      "missing_entries": [...]
    }
  }
}
```

### 2. 文本内容方式校对

**POST** `/api/v1/proofread/text`

请求参数:
- `original_srt`: 原字幕内容 (字符串)
- `recognized_srt`: 识别字幕内容 (字符串)

### 3. 健康检查

**GET** `/api/v1/health`

## 部署说明

### 开发环境

```bash
cd api
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 生产环境

```bash
cd api
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Nginx配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/frontend;
        index index.html;
    }

    # API代理
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 技术栈

- **后端**: FastAPI + Uvicorn
- **文本处理**: Python标准库 (re, difflib)
- **跨域**: CORS中间件
- **前端**: 原生HTML/CSS/JavaScript

## 注意事项

1. 识别字幕中的人名会被完全信任（如Stella、Benjamin）
2. 时间轴以识别字幕为准
3. 原字幕仅作为校对参考
4. 文件编码必须为UTF-8
