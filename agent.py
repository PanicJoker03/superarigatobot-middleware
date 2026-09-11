from datetime import datetime
import json
import redis
import os
import anthropic
from anthropic import Anthropic
from numpy.f2py.auxfuncs import throw_error

# 24 hours redis store
REDIS_DEFAULT_TTL = os.environ.get("REDIS_DEFAULT_TTL")

class Agent:
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    def __init__(self, redis_obj, system_prompt):
        self.r = redis_obj
        self.system_prompt = system_prompt

    def add_message_to_history(self, user_id: str, role: str, content: str):

        """Appends a new message turn (user or assistant) to the user's Redis list."""
        key = f"chat:{user_id}"

        # Pack role and content into JSON string
        message_payload = json.dumps({"role": role, "content": content})

        # Append to end of list
        self.r.rpush(key, message_payload)

        # Reset/extend the expiration timer on every active turn
        self.r.expire(key, REDIS_DEFAULT_TTL)

    def get_chat_history(self, user_id: str) -> list[dict]:
        """Retrieves full list of message objects for the user."""
        key = f"chat:{user_id}"

        # Fetch all items in list from index 0 to -1 (last item)
        raw_history = self.r.lrange(key, 0, -1)

        # Deserialize stored JSON strings back into Python dictionaries
        return [json.loads(msg) for msg in raw_history]

    def clear_chat_history(self, user_id: str):
        """Deletes conversation memory for a user manually."""
        key = f"chat:{user_id}"
        self.r.delete(key)

    #return claude ai response
    def do_conversation(
        self,
        user_id: str,
        action: str,
        message: str,
        chat_history: list[dict],
        file1 = None,
        file2 = None,
    ) -> str:
        #retrieve message history from redis
        try:
            # validate file, then prepend it to message
            if action in ["contact", 'prices']:
                if file1:
                    message = f"Estos son los datos: {file1}\n\n{message}"
                else:
                    throw_error(ValueError, "No file provided")
            elif action == "payment_method":
                message = f"Estos son los metodos de pago: {file1}\n\n{message}"
            #elif action == "quotation":
            #    message = f"{message}. Esta es la plantilla: {file1}\n\n. Estos son los servicios: {file2}"

            response = Agent.client.messages.create(
                #model="claude-sonnet-5",
                model = "claude-haiku-4-5",
                system=self.system_prompt,
                max_tokens=500,
                messages = chat_history + [{"role": "user", "content": message}]
            )

            # Filter through response blocks to extract only the text response
            for block in response.content:
                if block.type == "text":
                    return block.text
        except anthropic.APIConnectionError as e:
            print(f"Network error: {e}")
        except anthropic.RateLimitError as e:
            print("Rate limit hit, try again later")
        except anthropic.APIStatusError as e:
            print(f"API error {e.status_code}: {e.message}")

        return ""

    #return claude ai response in json format uses explicit system_prompt
    def do_quotation_json(
        self,
        user_id: str,
        quotation_id: str,
        chat_history: list[dict],
        json_template = None,
        services_txt = None,
    ) -> str:
        try:
            today = datetime.now().strftime("%d/%m/%Y")
            system = f"ERES un monotono generador de json, solo puedes responder con formato json. retorna formato json en funcion de esta plantilla {json_template}. Este es el catalogo de precios {services_txt}. Reemplaza folio por este uuid {quotation_id}. Reemplaza fecha por {today}. NO AGREGUES SERVICIOS QUE NO ENCUENTRES EN EL HISTORIAL DE MENSAJES"
            message = f"En base al historial de nuestra conversacion, realiza una cotizacion. "

            response = Agent.client.messages.create(
                #model="claude-sonnet-5",
                model = "claude-haiku-4-5",
                system= system,
                max_tokens=2000,
                messages = chat_history + [{"role": "user", "content": message}]
            )

            # Filter through response blocks to extract only the text response
            for block in response.content:
                if block.type == "text":
                    return block.text
        except anthropic.APIConnectionError as e:
            print(f"Network error: {e}")
        except anthropic.RateLimitError as e:
            print("Rate limit hit, try again later")
        except anthropic.APIStatusError as e:
            print(f"API error {e.status_code}: {e.message}")

        return ""