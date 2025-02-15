from flask import Flask, request, jsonify, render_template, session as flask_session
from flask_sqlalchemy import SQLAlchemy
import requests
import uuid
import datetime

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'  # Altere para uma chave segura em produção

# Configuração do SQLAlchemy utilizando o PyMySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:sFEauJWKcRiVetD1RLyYG2q5AUEcG9Cn8nhQiu9Os8tYJOq8u60AghpALieq0qxS@147.79.111.200:3307/bd_acordo_garantido'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Modelo que representa a tabela sessions_mensagens
class SessionMensagem(db.Model):
    __tablename__ = 'sessions_mensagens'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session = db.Column(db.String(255), nullable=False)
    mensagem = db.Column(db.String(1000), nullable=False)
    cpf = db.Column(db.String(14), nullable=True)  # Para mensagens do usuário ficará como NULL; usamos "bot" para identificar as do bot
    datahora = db.Column(db.String(50), nullable=True)

@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    user_message = data.get('message')
    if not user_message:
        return jsonify({'status': 'error', 'message': 'Mensagem não informada'}), 400

    # Cria ou recupera a sessão do usuário
    if 'chat_session' not in flask_session:
        flask_session['chat_session'] = str(uuid.uuid4())
    chat_session_id = flask_session['chat_session']

    # Salva a mensagem do usuário no BD
    new_msg = SessionMensagem(
        session=chat_session_id,
        mensagem=user_message,
        cpf=None,  # Sem login por enquanto; CPF ficará nulo
        datahora=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    db.session.add(new_msg)
    db.session.commit()

    # Envia a mensagem para o webhook externo, incluindo o ID da sessão
    payload = {
        'message': user_message,
        'session': chat_session_id
    }
    try:
        response = requests.post(
            'http://n8n.brs12.com.br/webhook/recebeMensagemChat', 
            #'http://n8n.brs12.com.br/webhook-test/recebeMensagemChat',
            json=payload,
            timeout=5  # Timeout opcional
        )
    except Exception as e:
        print("Erro ao enviar mensagem para o webhook:", e)
    
    return jsonify({'status': 'ok'})

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Endpoint para receber a resposta do webhook externo.
    Espera um JSON no formato: {"message": "Resposta do bot", "session": "ID_da_sessão"}
    """
    data = request.get_json()
    reply_message = data.get('message')
    chat_session_id = data.get('session')
    if not reply_message:
        return jsonify({'status': 'error', 'message': 'Mensagem não informada no payload'}), 400
    if not chat_session_id:
        chat_session_id = 'unknown'

    # Salva a mensagem do bot no BD; usamos "bot" no campo cpf para identificá-la
    new_msg = SessionMensagem(
        session=chat_session_id,
        mensagem=reply_message,
        cpf="bot",
        datahora=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    db.session.add(new_msg)
    db.session.commit()
    return jsonify({'status': 'received'}), 200

@app.route('/get_messages', methods=['GET'])
def get_messages():
    # Recupera o ID da sessão atual
    chat_session_id = flask_session.get('chat_session')
    if not chat_session_id:
        return jsonify([])  # Sem sessão, não há mensagens

    # Busca as mensagens da sessão atual, ordenadas pela inserção
    mensagens = SessionMensagem.query.filter_by(session=chat_session_id).order_by(SessionMensagem.id.asc()).all()
    messages_list = []
    for msg in mensagens:
        # Se o campo cpf for "bot", consideramos que a mensagem é do bot; caso contrário, é do usuário
        sender = 'Bot' if msg.cpf == "bot" else 'Você'
        messages_list.append({
            'sender': sender,
            'text': msg.mensagem,
            'datahora': msg.datahora
        })
    return jsonify(messages_list)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
