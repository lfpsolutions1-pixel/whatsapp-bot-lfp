from flask import Flask, request, jsonify
import requests
import json
import os

app = Flask(__name__)

VERIFY_TOKEN = "lfpsolutions"
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def enviar_mensaje(numero, mensaje):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": mensaje}
    }
    requests.post(url, headers=headers, json=data)

def preguntar_gemini(mensaje_cliente):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    prompt = f"""Eres un asistente virtual de LFP Solutions. Tu trabajo es atender clientes y agendar citas.

Cuando el cliente quiera agendar, recoge estos datos uno por uno:
1. Nombre completo
2. Servicio que necesita
3. Fecha deseada
4. Hora deseada

Cuando tengas todos los datos confirma la cita y responde EXACTAMENTE así:
CITA_AGENDADA|nombre|servicio|fecha|hora

Si el cliente solo saluda o pregunta algo, responde amablemente en español.

Mensaje del cliente: {mensaje_cliente}"""

    body = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, json=body)
    result = response.json()
    return result["candidates"][0]["content"]["parts"][0]["text"]

def guardar_cita(datos):
    print(f"CITA GUARDADA: {datos}")

@app.route("/webhook", methods=["GET"])
def verificar():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Error", 403

@app.route("/webhook", methods=["POST"])
def recibir_mensaje():
    data = request.get_json()
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        if "messages" in value:
            mensaje = value["messages"][0]
            numero = mensaje["from"]
            texto = mensaje["text"]["body"]
            respuesta = preguntar_gemini(texto)
            if "CITA_AGENDADA" in respuesta:
                partes = respuesta.split("|")
                guardar_cita(partes)
                enviar_mensaje(numero, f"✅ Cita confirmada para {partes[1]} el {partes[3]} a las {partes[4]}. ¡Hasta pronto!")
            else:
                enviar_mensaje(numero, respuesta)
    except Exception as e:
        print(f"Error: {e}")
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
