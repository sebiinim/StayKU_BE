from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
import openai
from datetime import datetime, timedelta

app = Flask(__name__)

# ------------------ MySQL 설정 ------------------
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'tjduswl123!'  # ← 비밀번호는 본인 환경에 맞게!
app.config['MYSQL_DB'] = 'laundry_db'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'  # 커서 결과를 딕셔너리로 받게 설정

mysql = MySQL(app)

# ------------------ OpenAI API 키 ------------------
openai.api_key = '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'  # ← 너의 실제 키로 교체할 것

# ------------------ 기본 라우트 ------------------
@app.route('/')
def home():
    return "Hello from Flask!"

# ------------------ 회원가입 API 추가 -----------------
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    user_id = data.get('user_id')
    password = data.get('password')

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    existing = cur.fetchone()

    if existing:
        return jsonify({"status": "fail", "message": "이미 존재하는 아이디입니다."})

    cur.execute("INSERT INTO users (user_id, password) VALUES (%s, %s)", (user_id, password))
    mysql.connection.commit()
    cur.close()

    return jsonify({"status": "success"})

# -----------------------로그인-----------
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user_id = data.get('user_id')
    password = data.get('password')

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = %s AND password = %s", (user_id, password))
    result = cur.fetchone()
    cur.close()

    if result:
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "fail", "message": "아이디 또는 비밀번호가 일치하지 않습니다"}), 401

# ------------------ 1. 세탁기 현황 보기 ------------------
@app.route('/washer_status', methods=['GET'])
def washer_status():
    # 더미 데이터 (실제 MySQL 연동 가능)
    data = [
        {"id": 1, "status": "in use", "remaining_time": 20},
        {"id": 2, "status": "available"},
        {"id": 3, "status": "in use", "remaining_time": 10}
    ]
    return jsonify(data)

# ------------------ 1-3. 세탁기 예약 ------------------
@app.route('/reserve', methods=['POST'])
def reserve():
    data = request.json
    washer_type = data.get('washer_type')
    user_id = data.get('user_id')

    now = datetime.now()
    expire = now + timedelta(minutes=10)

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO reservations (washer_type, user_id, reserved_at, expire_at)
        VALUES (%s, %s, %s, %s)
    """, (washer_type, user_id, now, expire))
    mysql.connection.commit()
    cur.close()

    return jsonify({'status': 'reserved'})

# ------------------ GPT-4 대화용 API ------------------
@app.route('/chatgpt', methods=['POST'])
def chatgpt():
    user_message = request.json.get('message')

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": user_message}]
    )

    reply = response['choices'][0]['message']['content']
    return jsonify({'reply': reply})

# ------------------ 2-1. 룸메이트 성향 등록 ------------------
@app.route('/profile', methods=['POST'])
def register_profile():
    data = request.get_json()
    cur = mysql.connection.cursor()

    # 1. 프로필 저장
    cur.execute("""
        REPLACE INTO roommate_profiles 
        (user_id, is_morning_person, is_smoker, snore_level, hygiene_level, hall_type)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        data['user_id'],
        data['is_morning_person'],
        data['is_smoker'],
        data['snore_level'],
        data['hygiene_level'],
        data['hall_type']
    ))

    # 2. 기존 자동 태그 제거 (한 번만!)
    cur.execute("DELETE FROM user_tags WHERE user_id = %s AND tag LIKE %s", (data['user_id'], '#%'))

    # 3. 프로필 기반 자동 태그 생성
    auto_tags = []

    if data['is_morning_person']:
        auto_tags.append('#아침형')
    else:
        auto_tags.append('#저녁형')

    if not data['is_smoker']:
        auto_tags.append('#비흡연')
    else:
        auto_tags.append('#흡연자')

    if data['hygiene_level'] >= 4:
        auto_tags.append('#깔끔한편')
    elif data['hygiene_level'] <= 2:
        auto_tags.append('#청소귀찮음')

    for tag in auto_tags:
        cur.execute("INSERT INTO user_tags (user_id, tag) VALUES (%s, %s)", (data['user_id'], tag))

    mysql.connection.commit()
    cur.close()
    return jsonify({"status": "profile_saved"})



# ------------------ 2-2. 룸메이트 채팅 저장 (정식 POST /chat) ------------------
@app.route('/chat', methods=['POST'])
def save_chat():
    data = request.json
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO roommate_chats (from_user, to_user, message)
        VALUES (%s, %s, %s)
    """, (
        data['from_user'],
        data['to_user'],
        data['message']
    ))
    mysql.connection.commit()
    cur.close()
    return jsonify({"status": "message_saved"})


# ------------------ 2-2. 룸메이트 채팅 내역 조회 ------------------
@app.route('/chat/<from_user>/<to_user>', methods=['GET'])
def get_chat(from_user, to_user):
    cur = mysql.connection.cursor()
    query = """
    SELECT * FROM roommate_chats
    WHERE (from_user = %s AND to_user = %s)
       OR (from_user = %s AND to_user = %s)
    ORDER BY sent_at ASC
    """
    cur.execute(query, (from_user, to_user, to_user, from_user))
    messages = cur.fetchall()
    cur.close()
    return jsonify(messages)

# ------------------- 채팅 상대 불러오기 -------------------
@app.route('/chat/partners/<user_id>', methods=['GET'])
def get_chat_partners(user_id):
    try:
        cursor = mysql.connection.cursor()
        
        # from_user 또는 to_user에 user_id가 포함된 경우, 상대방 ID만 추출
        query = """
            SELECT DISTINCT 
                CASE 
                    WHEN from_user = %s THEN to_user 
                    ELSE from_user 
                END AS partner
            FROM roommate_chats
            WHERE from_user = %s OR to_user = %s
        """
        cursor.execute(query, (user_id, user_id, user_id))
        result = cursor.fetchall()
        cursor.close()
        
        partners = [row[0] for row in result]
        return jsonify(partners), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ 2-3. 룸메이트 팀 구성 ------------------
@app.route('/team', methods=['POST'])
def create_team():
    data = request.json
    members = data['members']
    hall_type = data['hall_type']

    if hall_type == '신관' and len(members) != 2:
        return jsonify({"error": "신관은 2인만 가능합니다."}), 400
    if hall_type == '구관' and len(members) != 3:
        return jsonify({"error": "구관은 3인만 가능합니다."}), 400

    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO roommate_teams (hall_type) VALUES (%s)", (hall_type,))
    team_id = cur.lastrowid

    for user_id in members:
        cur.execute("INSERT INTO roommate_team_members (team_id, user_id) VALUES (%s, %s)", (team_id, user_id))

    mysql.connection.commit()
    cur.close()

    return jsonify({"team_id": team_id, "status": "team_created"})

# ------------------ 태그 저장하기 --------------
@app.route('/tags', methods=['POST'])
def save_tags():
    try:
        data = request.get_json()
        user_id = data['user_id']
        tags = data['tags']

        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM user_tags WHERE user_id = %s", (user_id,))
        for tag in tags:
            cursor.execute("INSERT INTO user_tags (user_id, tag) VALUES (%s, %s)", (user_id, tag))
        mysql.connection.commit()
        cursor.close()

        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------태그 가져오기--------------
@app.route('/tags/<user_id>', methods=['GET'])
def get_user_tags(user_id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT tag FROM user_tags WHERE user_id = %s", (user_id,))
        result = cursor.fetchall()
        cursor.close()

        tags = [row['tag'] for row in result]
        return jsonify(tags), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# ------------------태그 기반으로 매칭 추천 ---------------
@app.route('/match/<user_id>', methods=['GET'])
def match_users(user_id):
    try:
        exclude = request.args.getlist('exclude')  # /match/tae?exclude=a&exclude=b

        cur = mysql.connection.cursor()

        # 1. 현재 유저 태그 및 hall_type 조회
        cur.execute("SELECT tag FROM user_tags WHERE user_id = %s", (user_id,))
        user_tags = set(row[0] for row in cur.fetchall())

        cur.execute("SELECT hall_type FROM roommate_profiles WHERE user_id = %s", (user_id,))
        result = cur.fetchone()
        if not result:
            return jsonify([]), 200
        my_hall = result[0]

        # 2. 다른 유저들 조회 (같은 건물, 자기 자신 제외, exclude 제외)
        cur.execute("""
            SELECT u.user_id, p.is_morning_person, p.is_smoker, p.snore_level, 
                   p.hygiene_level, p.hall_type
            FROM users u
            JOIN roommate_profiles p ON u.user_id = p.user_id
            WHERE u.user_id != %s AND p.hall_type = %s
        """, (user_id, my_hall))

        candidates = []
        for row in cur.fetchall():
            other_id = row[0]
            if other_id in exclude:
                continue

            cur.execute("SELECT tag FROM user_tags WHERE user_id = %s", (other_id,))
            other_tags = set(tag[0] for tag in cur.fetchall())

            common_tags = user_tags & other_tags
            if len(common_tags) >= 5:
                candidates.append({
                    "user_id": other_id,
                    "is_morning_person": row[1],
                    "is_smoker": row[2],
                    "snore_level": row[3],
                    "hygiene_level": row[4],
                    "hall_type": row[5],
                    "common_tag_count": len(common_tags),
                    "common_tags": list(common_tags),
                    "all_tags": list(other_tags)
                })

        cur.close()

        # 랜덤으로 3명 추출
        import random
        random.shuffle(candidates)
        return jsonify(candidates[:3]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ Flask 실행 ------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
