import os
import uuid
import base64
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify, url_for, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from PIL import Image
from openai import OpenAI

load_dotenv()

app = Flask(__name__)

# 配置
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['RESULT_FOLDER'] = 'static/results'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

# 获取 API Key
QIANFAN_API_KEY = os.getenv("QIANFAN_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
QIANFAN_SHITU_API_KEY = os.getenv("QIANFAN_SHITU_API_KEY")
print("QIANFAN API Key loaded:", QIANFAN_API_KEY[:15] + "..." if QIANFAN_API_KEY else "None")
print("DEEPSEEK API Key loaded:", DEEPSEEK_API_KEY[:15] + "..." if DEEPSEEK_API_KEY else "None")
print("QIANFAN SHITU API Key loaded:", QIANFAN_SHITU_API_KEY[:15] + "..." if QIANFAN_SHITU_API_KEY else "None")
if not QIANFAN_API_KEY:
    raise ValueError("请在 .env 文件中设置 QIANFAN_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("请在 .env 文件中设置 DEEPSEEK_API_KEY")
if not QIANFAN_SHITU_API_KEY:
    raise ValueError("请在 .env 文件中设置 QIANFAN_SHITU_API_KEY")

# 初始化 OpenAI 客户端
client = OpenAI(base_url='https://qianfan.baidubce.com/v2', api_key=QIANFAN_API_KEY)

# 风格库
STYLES = {
    '和玺彩画': '故宫和玺彩画，以金龙纹为主，色彩金碧辉煌，寓意皇权尊贵',
    '旋子彩画': '旋子彩画，以旋花纹为主，色彩青绿相间，常用于宫殿建筑',
    '苏式彩画': '苏式彩画，以山水人物为主，色彩清新雅致，源于江南园林',
    '敦煌壁画': '敦煌壁画风格，以飞天、莲花为特色，色彩浓郁，充满宗教艺术感',
    '藏族彩绘': '藏族彩绘，以八宝吉祥图案为主，色彩鲜艳，寓意吉祥如意'
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def compress_image(image_path, max_size=(1024, 1024)):
    try:
        img = Image.open(image_path)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        img.save(image_path, optimize=True, quality=85)
        return True
    except Exception as e:
        print(f"压缩失败: {e}")
        return False

def analyze_image(image_path):
    try:
        # 读取图片并转换为base64
        with open(image_path, 'rb') as f:
            image_data = f.read()
        image_b64 = base64.b64encode(image_data).decode('utf-8')
        
        # 调用百度千帆图片分析API
        url = "https://qianfan.baidubce.com/v2/tools/image_general"
        headers = {
            "Authorization": f"Bearer {QIANFAN_SHITU_API_KEY}",
            "HOST": "qianfan.baidubce.com",
            "Content-Type": "application/json"
        }
        data = {
            "image_b64": image_b64
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        # 解析响应
        if result.get('code') == '0':
            data = result.get('data', {})
            query_context = data.get('query_context', {})
            
            # 提取主要内容
            main_content = "图片内容"
            
            # 检查guesswords字段
            guesswords = query_context.get('guesswords', [])
            
            # 处理guesswords可能是数组的情况
            if isinstance(guesswords, list) and guesswords:
                # 取第一个guessword
                first_guess = guesswords[0]
                if isinstance(first_guess, dict):
                    # 优先使用word字段
                    if 'word' in first_guess:
                        main_content = first_guess.get('word', '图片内容')
                    # 检查extend_brief
                    elif 'extend_brief' in first_guess:
                        extend_brief = first_guess['extend_brief']
                        if isinstance(extend_brief, dict):
                            # 检查各种摘要字段
                            for abstract_key in ['mlm_abstract', 'animal_abstract', 'plant_abstract', 'product_abstract']:
                                if abstract_key in extend_brief:
                                    abstract = extend_brief[abstract_key]
                                    if isinstance(abstract, dict) and 'content' in abstract:
                                        main_content = abstract['content']
                                        break
                                    elif isinstance(abstract, str):
                                        main_content = abstract
                                        break
            
            # 处理guesswords是对象的情况
            elif isinstance(guesswords, dict):
                if 'word' in guesswords:
                    main_content = guesswords.get('word', '图片内容')
                elif 'extend_brief' in guesswords:
                    extend_brief = guesswords['extend_brief']
                    if isinstance(extend_brief, dict):
                        for abstract_key in ['mlm_abstract', 'animal_abstract', 'plant_abstract', 'product_abstract']:
                            if abstract_key in extend_brief:
                                abstract = extend_brief[abstract_key]
                                if isinstance(abstract, dict) and 'content' in abstract:
                                    main_content = abstract['content']
                                    break
                                elif isinstance(abstract, str):
                                    main_content = abstract
                                    break
            
            # 确保内容简洁
            main_content = main_content[:100]  # 限制长度
            
            return main_content
        else:
            print(f"图片分析失败: {result.get('message', 'Unknown error')}")
            return "图片内容"
    except Exception as e:
        print(f"图片分析异常: {e}")
        return "图片内容"

def generate_image(prompt, save_path, size="1024x1024"):
    try:
        response = client.images.generate(
            model="qwen-image",
            prompt=prompt,
            size=size,
            n=1
        )
        if response.data[0].b64_json:
            image_data = base64.b64decode(response.data[0].b64_json)
            with open(save_path, "wb") as f:
                f.write(image_data)
            return save_path
        elif response.data[0].url:
            img_data = requests.get(response.data[0].url).content
            with open(save_path, "wb") as f:
                f.write(img_data)
            return save_path
        else:
            return None
    except Exception as e:
        print(f"图像生成失败: {e}")
        return None

def generate_poetry(style, building):
    try:
        # 构建 prompt
        prompt = f"为{building}的{style}创作一首七言绝句，要求意境优美，符合古建筑和彩绘风格的特点，格式为：\n《标题》\n第一句\n第二句\n第三句\n第四句，注意你只需要给出诗词内容，不需要注释等"
        
        # 调用 DeepSeek API
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 200
        }
        
        response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        poetry_content = result['choices'][0]['message']['content']
        
        # 解析诗词内容
        lines = poetry_content.strip().split('\n')
        title = lines[0].strip('《》') if lines else "无题"
        content = '\n'.join(lines[1:]) if len(lines) > 1 else ""
        
        return title, content
    except Exception as e:
        print(f"诗词生成失败: {e}")
        return None, str(e)

@app.route('/')
def index():
    return render_template('index.html', styles=STYLES.keys())

@app.route('/poetry')
def poetry():
    return render_template('poetry.html')

@app.route('/gallery')
def gallery():
    return render_template('gallery.html')

@app.route('/author/<author>')
def author_page(author):
    return render_template('author.html')

@app.route('/model')
def model_page():
    return render_template('model_lhw.html')

@app.route('/api/generate-poetry', methods=['POST'])
def generate_poetry_api():
    try:
        data = request.get_json()
        style = data.get('style', '和玺彩画')
        building = data.get('building', '故宫')
        
        title, content = generate_poetry(style, building)
        
        if title and content:
            return jsonify({
                'success': True,
                'title': title,
                'content': content
            })
        else:
            return jsonify({
                'success': False,
                'error': '诗词生成失败'
            }), 500
    except Exception as e:
        print(f"API 错误: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/painted_reference/<path:filename>')
def serve_painted_reference(filename):
    return send_from_directory('painted_reference', filename)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    # 1. 文件检查
    if 'file' not in request.files:
        return jsonify({'error': '没有上传文件'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': '不支持的文件格式'}), 400

    style = request.form.get('style', '和玺彩画')
    if style not in STYLES:
        style = '和玺彩画'
    
    # 获取比例参数
    aspect_ratio = request.form.get('aspect_ratio', '1024x1024')
    # 验证比例值
    valid_ratios = ['1024x1024', '1024x1536', '1536x1024']
    if aspect_ratio not in valid_ratios:
        aspect_ratio = '1024x1024'

    # 2. 保存原图
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    original_filename = secure_filename(file.filename)
    unique_filename = f"{timestamp}_{uuid.uuid4().hex[:8]}_{original_filename}"
    original_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(original_path)
    compress_image(original_path)

    # 3. 分析图片内容
    description = analyze_image(original_path)
    print(f"图片分析结果: {description}")

    # 4. 构造 prompt
    style_desc = STYLES[style]
    prompt = f"将以下内容转换成{style}风格的古建筑彩绘画作。图片内容：{description}。风格要求：{style_desc}，色彩鲜艳，线条流畅，中国传统风格。"

    # 5. 生成图片
    result_filename = f"result_{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
    result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
    result = generate_image(prompt, result_path, aspect_ratio)
    if not result:
        return jsonify({'error': 'AI生成失败，请重试'}), 500

    local_url = url_for('static', filename=f'results/{result_filename}')
    return jsonify({
        'success': True,
        'result_url': local_url,
        'style': style,
        'message': f'已生成{style}风格作品'
    })

# 班级长廊相关API
import json

GALLERY_JSON = 'templates/gallery.json'

def load_gallery():
    try:
        if os.path.exists(GALLERY_JSON):
            with open(GALLERY_JSON, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"加载画廊失败: {e}")
        return []

def save_gallery(data):
    try:
        with open(GALLERY_JSON, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"保存画廊失败: {e}")
        return False

@app.route('/api/gallery')
def get_gallery():
    gallery_data = load_gallery()
    return jsonify(gallery_data)

@app.route('/api/save-to-gallery', methods=['POST'])
def save_to_gallery():
    try:
        data = request.get_json()
        author = data.get('author')
        image_url = data.get('image_url')
        poetry = data.get('poetry')
        
        if not author or not image_url:
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400
        
        gallery_data = load_gallery()
        
        # 生成新的ID
        new_id = 1
        if gallery_data:
            new_id = max(item.get('id', 0) for item in gallery_data) + 1
        
        # 提取图片文件名
        image_filename = image_url.split('/')[-1]
        
        # 创建新作品
        new_item = {
            'id': new_id,
            'author': author,
            'image_url': image_filename,
            'poetry': poetry,
            'created_at': datetime.now().isoformat()
        }
        
        gallery_data.append(new_item)
        
        if save_gallery(gallery_data):
            return jsonify({'success': True, 'message': '作品保存成功'})
        else:
            return jsonify({'success': False, 'error': '保存失败'}), 500
            
    except Exception as e:
        print(f"保存到画廊失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000,debug=False)