# app.py
"""
Horisation Flask 应用主入口
CSV/Excel 数据分析与金融建模 Web 应用
"""

import os
from flask import Flask, render_template

# 导入 Blueprint
from Backend.Controller.csvcontroller import bp as csv_bp

# 配置路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'Template')
STATIC_DIR = os.path.join(BASE_DIR, 'Static')
UPLOAD_DIR = os.path.join(BASE_DIR, '_uploads')

# 确保上传目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)

print("=" * 60)
print("🚀 Horisation Application Starting...")
print("=" * 60)
print(f"📂 Template Directory: {TEMPLATE_DIR} (exists: {os.path.exists(TEMPLATE_DIR)})")
print(f"📂 Static Directory: {STATIC_DIR} (exists: {os.path.exists(STATIC_DIR)})")
print(f"📂 Upload Directory: {UPLOAD_DIR} (exists: {os.path.exists(UPLOAD_DIR)})")
print("=" * 60)

# 创建 Flask 应用
app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

# 应用配置
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR

# 注册 Blueprint
app.register_blueprint(csv_bp)
print("✅ Registered Blueprint: csv_api")

# ==================== 路由定义 ====================

@app.route('/')
def home():
    """主页"""
    return render_template('Home.html', active_page='home')


@app.route('/csv')
def csv():
    """CSV 工作区"""
    return render_template('CSV.html', active_page='csv')


@app.route('/hormemo')
def hormemo():
    """备忘录页面"""
    return render_template('hormemo.html', active_page='hormemo')


@app.route('/limit')
def limit():
    """限额跟踪页面"""
    return render_template('limit.html', active_page='limit')


# ==================== 错误处理 ====================

@app.errorhandler(413)
def request_entity_too_large(error):
    """文件过大错误处理"""
    from flask import jsonify
    return jsonify({'ok': False, 'error': 'File too large (max 100MB)'}), 413


@app.errorhandler(404)
def not_found(error):
    """404 错误处理"""
    return render_template('Home.html', active_page='home'), 404


@app.errorhandler(500)
def internal_error(error):
    """500 错误处理"""
    from flask import jsonify
    return jsonify({'ok': False, 'error': 'Internal server error'}), 500


# ==================== 启动应用 ====================

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🌐 Server running at: http://localhost:5000")
    print("📊 CSV Workspace: http://localhost:5000/csv")
    print("=" * 60 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
