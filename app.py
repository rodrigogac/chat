from flask import Flask, request, jsonify, render_template
import requests

app = Flask(__name__)

# Lista global para armazenar as mensagens (apenas para demonstração)
messages = []

@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    user_message = data.get('message')
    if not user_message:
        return jsonify({'status': 'error', 'message': 'Mensagem não informada'}), 400

    # Registra a mensagem do usuário
    messages.append({'sender': 'user', 'text': user_message})

    # Envia a mensagem para o webhook externo
    payload = {'message': user_message}
    try:
        response = requests.post(
            'http://n8n.brs12.com.br/webhook-test/recebeMensagemChat', 
            json=payload,
            timeout=5  # timeout opcional
        )
        # Aqui podemos tratar a resposta se necessário
    except Exception as e:
        print("Erro ao enviar mensagem para o webhook:", e)
    
    return jsonify({'status': 'ok'})

@app.route('/webhook', methods=['POST'])
def webhook():
    """
    Endpoint para receber as mensagens do webhook externo.
    Exemplo: o serviço externo envia um JSON no formato {"message": "Resposta do bot"}
    """
    data = request.get_json()
    reply_message = data.get('message')
    if not reply_message:
        return jsonify({'status': 'error', 'message': 'Mensagem não informada no payload'}), 400

    # Registra a mensagem recebida (de "bot")
    messages.append({'sender': 'bot', 'text': reply_message})
    return jsonify({'status': 'received'}), 200

@app.route('/get_messages', methods=['GET'])
def get_messages():
    return jsonify(messages)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

