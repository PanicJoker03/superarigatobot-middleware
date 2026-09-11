# maya consulting agent for ramos lab
# fast api example middleware to link watson assistant x to knowledge base
import uuid
from fastapi.responses import FileResponse
from fastapi import FastAPI, Request
import anthropic
from anthropic import Anthropic
import pandas as pd
from sqlalchemy import create_engine
from numpy.f2py.auxfuncs import throw_error
from agent import Agent
import json
import redis
import os
from pathlib import Path
from fastapi import FastAPI, Form, Request, Response, BackgroundTasks
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

# this is made to integrate WA to conversation
from fastapi import FastAPI, Request, Query
from fastapi.responses import PlainTextResponse

from generador_cotizacion_pdf import GeneradorCotizacionPDF
from utility import extract_and_parse_json, generar_numero_10

PDF_QUOTATION_DIR = os.environ.get("PDF_QUOTATION_DIR")

RENDER_API_URL = os.environ.get("RENDER_API_URL")

REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PORT = os.environ.get("REDIS_PORT")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD")

# sql database
DB_SQL_ENGINE = os.environ.get("DB_SQL_ENGINE")
DB_SQL_USER = os.environ.get("DB_SQL_USER")
DB_SQL_PASSWORD = os.environ.get("DB_SQL_PASSWORD")
DB_SQL_DB = os.environ.get("DB_SQL_DB")
DB_SQL_HOST = os.environ.get("DB_SQL_HOST")
DB_SQL_PORT = os.environ.get("DB_SQL_PORT")

WEBHOOK_VERIFY_TOKEN = os.environ.get("WEBHOOK_VERIFY_TOKEN") # pick any string

# Twilio Env Credentials
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = f"whatsapp:+52{os.environ.get("TWILIO_WHATSAPP_NUMBER")}"  # Your Twilio WhatsApp Sender

# This only covers POSTGRE SQL CASE

app = FastAPI()

r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
    username="default",
    password=REDIS_PASSWORD,
)

# todo: make environment
AGENT_PROMPT = 'Eres el agente (humano, en realidad existes) de atención a pacientes y clientes de "Laboratorio Ramos", una clínica de análisis clínicos ubicada en México. Tu labor es atender de forma cálida, profesional y clara, en español, resolviendo dudas sobre estudios de laboratorio, precios, tiempos de entrega de resultados, horarios y ubicación de sucursales. OFRECE LOS PRECIOS SI LO PIDEN. NO AGENDADO DE CITAS. Verifica siempre la identidad básica del paciente (nombre completo) antes de compartir información sensible, y jamás reveles resultados médicos por este medio si involucran datos delicados sin la debida validación; en su lugar, orienta. Sé empático ante preocupaciones de salud, DECLINA diagnósticos o interpretación médica de resultados — eso corresponde al médico tratante. Si la solicitud excede tu alcance, deriva a un representante humano o al área correspondiente.'

@app.get("/assistant")
async def get_assistant(action: str, watson_session_id: str, message: str):
    # Query laboratorios ramos here
    agent = Agent(r, AGENT_PROMPT)
    claude_ai_reply = "..."
    user_id = watson_session_id
    try:
        # retrieve past turns from redis
        chat_history = agent.get_chat_history(user_id)
        if action in ["no_match", '', None]:
            # normal case
            claude_ai_reply = agent.do_conversation(user_id, action, message, chat_history)
        elif action == "contact":
            # retrieve contact case
            # load csv file for sucursales
            sucursales_df = pd.read_csv("sucursales.csv")
            sucursales_txt = sucursales_df.to_csv(index=False)
            ciudad = message
            claude_ai_reply = agent.do_conversation(user_id, action, f"información de la sucursal de {ciudad}?",
                                                    chat_history, sucursales_txt)
        elif action == "prices":
            # check prices on db
            db_engine = create_engine(
                f"postgresql://{DB_SQL_USER}:{DB_SQL_PASSWORD}@{DB_SQL_HOST}:{DB_SQL_PORT}/{DB_SQL_DB}")
            servicios_df = pd.read_sql("SELECT * FROM servicio;", db_engine)
            servicios_txt = servicios_df.to_csv(index=False)
            claude_ai_reply = agent.do_conversation(user_id, action, f"precios: '{message}'?", chat_history,
                                                    servicios_txt)
        elif action == "payment_method":
            # metodos de pago
            payment_methods = "efectivo, transferencia, debito, credito, cheque"
            claude_ai_reply = agent.do_conversation(user_id, action, f"métodos de pago: '{message}'?", chat_history,
                                                    payment_methods)

        # store turn on redis
        agent.add_message_to_history(user_id, "user", message)
        agent.add_message_to_history(user_id, "assistant", claude_ai_reply)
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        print(err)
        # todo remove
        return {"response": err}

    return {"response": claude_ai_reply}

# test case quotation price
@app.get("/quotation")
async def get_quotation(action: str, watson_session_id: str, message: str):
    # Query laboratorios ramos here
    agent = Agent(r, AGENT_PROMPT)
    claude_ai_reply = "..."
    user_id = watson_session_id
    try:
        # retrieve past turns from redis
        chat_history = agent.get_chat_history(user_id)
        #todo: store on database
        quotation_id = generar_numero_10()

        json_template = ""
        with open("spec_cotizacion.json", "r", encoding="utf-8") as f:
            json_template = f.read()

        # check prices on db
        db_engine = create_engine(
            f"postgresql://{DB_SQL_USER}:{DB_SQL_PASSWORD}@{DB_SQL_HOST}:{DB_SQL_PORT}/{DB_SQL_DB}")
        servicios_df = pd.read_sql("SELECT * FROM servicio;", db_engine)
        servicios_txt = servicios_df.to_csv(index=False)

        message = f"En base al historial de nuestra conversacion, realiza una cotizacion. retorna formato json en funcion de esta plantilla {json_template}. Este es el catalogo de precios {servicios_txt}"
        quotation_reply_json = agent.do_quotation_json(user_id, quotation_id, chat_history, json_template, servicios_txt)

        # scape answer
        # 1. Assuming 'data' is the dictionary returned by extract_and_parse_json()
        quotation_dict = extract_and_parse_json(quotation_reply_json)

        # 2. Convert dictionary to an explicit JSON string
        # explicit_json_string = json.dumps(quotation_dict, indent=2, ensure_ascii=False)

        #/ scape answer

        # store turn on redis
        agent.add_message_to_history(user_id, "user", "cotizacion por favor")
        agent.add_message_to_history(user_id, "assistant", "aqui esta tu cotizacion")

        filepath = f"{PDF_QUOTATION_DIR}/{quotation_id}.pdf"

        # ... your PDF generation logic here, save to filepath ...
        folder = Path(PDF_QUOTATION_DIR)
        folder.mkdir(parents=True, exist_ok=True)

        #TODO: replace with PDF generation
        quotation_generator = GeneradorCotizacionPDF()
        quotation_generator.generate_pdf(quotation_dict, filepath)

        #with open(filepath, "w") as f:
        #    f.write("Hello world!")

        # pdf_url = f"https://tu-servicio.onrender.com/cotizacion/{pdf_id}"
        pdf_url = f"{RENDER_API_URL}/cotizacion/{quotation_id}"

        return { "response":  f"[COTIZACIÓN]({pdf_url})" }
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        print(err)
        return {"response": err}
    #return {"pdf_url": pdf_url}
    #return "hola"

# download pdf
@app.get("/cotizacion/{pdf_id}")
def descargar_cotizacion(pdf_id: str):
    filepath = f"{PDF_QUOTATION_DIR}/{pdf_id}.pdf"
    return FileResponse(filepath, media_type="application/pdf", filename=f"{pdf_id}.pdf")

# -------------------------------------------------------------------
# 1. INBOUND WEBHOOK INTERCEPTOR
# -------------------------------------------------------------------
@app.post("/webhook")
async def whatsapp_webhook(
        From: str = Form(...),  # Customer's number (e.g., 'whatsapp:+528110284627')
        Body: str = Form(...),  # Text sent by the customer
        ProfileName: str = Form(None)  # Customer's WhatsApp display name
):
    """
    Intercepts incoming WhatsApp messages from Twilio.
    """
    clean_number = From.replace("whatsapp:", "")
    print(f"\n📩 [INBOUND MESSAGE] From: {ProfileName or 'User'} ({clean_number})")
    print(f"💬 Content: \"{Body}\"")

    # Custom incoming logic
    user_msg = Body.strip().lower()

    # Query laboratorios ramos here
    agent = Agent(r, AGENT_PROMPT)
    claude_ai_reply = "..."
    user_id = clean_number
    try:
        # retrieve past turns from redis
        chat_history = agent.get_chat_history(user_id)
        if "contacto" in user_msg:
            # retrieve contact case
            # load csv file for sucursales
            sucursales_df = pd.read_csv("sucursales.csv")
            sucursales_txt = sucursales_df.to_csv(index=False)
            ciudad = user_msg
            claude_ai_reply = agent.do_conversation(user_id, 'contact', f"información de la sucursal de {ciudad}?",
                                                    chat_history, sucursales_txt)
        elif "precios" in user_msg:
            # check prices on db
            db_engine = create_engine(
                f"postgresql://{DB_SQL_USER}:{DB_SQL_PASSWORD}@{DB_SQL_HOST}:{DB_SQL_PORT}/{DB_SQL_DB}")
            servicios_df = pd.read_sql("SELECT * FROM servicio;", db_engine)
            servicios_txt = servicios_df.to_csv(index=False)
            claude_ai_reply = agent.do_conversation(user_id, 'prices', f"precios: '{user_msg}'?", chat_history,
                                                    servicios_txt)
        elif "metodo pago" in user_msg:
            # metodos de pago
            payment_methods = "efectivo, transferencia, debito, credito, cheque"
            claude_ai_reply = agent.do_conversation(user_id, 'payment_method', f"métodos de pago: '{user_msg}'?", chat_history,
                                                    payment_methods)
        else:
            # normal case
            claude_ai_reply = agent.do_conversation(user_id, '', user_msg, chat_history)

        # store turn on redis
        agent.add_message_to_history(user_id, "user", user_msg)
        agent.add_message_to_history(user_id, "assistant", claude_ai_reply)
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        print(err)
        # todo remove
        return Response(content=str(err), media_type="application/xml")

    #if "horario" in user_msg:
    #    reply_text = "Nuestro horario de atención es de Lunes a Domingo de 8:00 AM a 10:00 PM."
    #elif "ubicacion" in user_msg:
    #    reply_text = "Nos encontramos en Av. Principal #123, Col. Centro."
    #else:
    #    reply_text = f"¡Hola {ProfileName or ''}! Recibimos tu mensaje: '{Body}'. Un agente de Farmacias Ramos te atenderá en breve."

    # Build an immediate TwiML XML response (free-form reply inside 24h window)
    twiml_resp = MessagingResponse()
    twiml_resp.message(claude_ai_reply)

    # Return valid TwiML HTTP 200 XML response to Twilio
    return Response(content=str(twiml_resp), media_type="application/xml")


# -------------------------------------------------------------------
# 2. OUTBOUND MESSAGING ENDPOINTS (PROGRAMMATIC SENDER)
# -------------------------------------------------------------------

# Scenario A: Free-form text (Inside active 24h window)
@app.post("/api/send-freeform")
async def send_freeform_message(to_number: str, text: str):
    """
    Sends a custom free-form text message to a user inside the 24-hour window.
    to_number format: +528110284627
    """
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    formatted_to = f"whatsapp:{to_number}" if not to_number.startswith("whatsapp:") else to_number

    message = client.messages.create(
        from_=TWILIO_WHATSAPP_NUMBER,
        to=formatted_to,
        body=text
    )
    return {"status": "success", "message_sid": message.sid}

# Scenario B: Template message (Business-initiated / Outside 24h window)
@app.post("/api/send-template")
async def send_template_message(
        to_number: str,
        template_sid: str,
        var_1: str,
        var_2: str
):
    """
    Sends a Meta-approved template to initiate a conversation outside the 24-hour window.
    """
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    formatted_to = f"whatsapp:{to_number}" if not to_number.startswith("whatsapp:") else to_number

    message = client.messages.create(
        from_=TWILIO_WHATSAPP_NUMBER,
        to=formatted_to,
        content_sid=template_sid,
        content_variables=json.dumps({"1": var_1, "2": var_2})
    )
    return {"status": "success", "message_sid": message.sid}

# initial agent logic
def buscar_disponibilidad_aproximada(handle_recibido: str) -> str:
    file_path = "knowledge_base.txt"

    if not os.path.exists(file_path):
        return "No"

    # 1. Limpiar el handle y extraer palabras clave de más de 3 letras
    # Ejemplo: "tasa-mario-verde" -> ["tasa", "mario", "verde"]
    palabras_handle = [
        p.lower() for p in handle_recibido.replace("-", " ").split()
        if len(p) > 3
    ]

    # Si el handle no tiene palabras significativas, no podemos buscar de forma segura
    if not palabras_handle:
        return "No"

    # 2. Leer e iterar el archivo línea por línea
    with open(file_path, "r", encoding="utf-8") as f:
        lineas = f.readlines()

    for i, linea in enumerate(lineas):
        linea_lower = linea.lower()

        # 3. Filtrar solo las líneas que pregunten por disponibilidad
        if "is" in linea_lower and "available" in linea_lower:
            # Extraer palabras de la línea de más de 3 letras
            palabras_linea = [p for p in linea_lower.split() if len(p) > 3]

            # 4. Verificar si ALGUNA palabra del handle coincide con la línea
            # Ejemplo: Si el handle tiene "mario" y la línea tiene "mario", hay coincidencia
            coincidencia = any(palabra in palabras_linea for palabra in palabras_handle)

            if coincidencia:
                # 5. Si coincide la pregunta (Q:), revisamos la respuesta (A:) que está en la siguiente línea (i + 1)
                if i + 1 < len(lineas):
                    siguiente_linea = lineas[i + 1].lower()
                    # Validamos si la respuesta confirma la compra exitosa
                    if "currently available" in siguiente_linea and "archived" not in siguiente_linea:
                        return "Yes"
                    else:
                        return "No"
    return "No"

@app.get("/product/{handle}")
async def get_product(handle: str):
    # Query Shopify here
    status = buscar_disponibilidad_aproximada(handle)
    return {"product_availability": status}