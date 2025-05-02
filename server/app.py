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
    data = request.json
    cur = mysql.connection.cursor()
    cur.execute("""
        REPLACE INTO roommate_profiles 
        (user_id, is_morning_person, is_smoker, snores, hygiene_level, hall_type)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        data['user_id'],
        data['is_morning_person'],
        data['is_smoker'],
        data['snores'],
        data['hygiene_level'],
        data['hall_type']
    ))
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

# ------------------ Flask 실행 ------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
