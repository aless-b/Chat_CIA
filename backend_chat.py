"""
backend_chat.py
============================
Requiere:
    pip install fastapi "uvicorn[standard]" httpx mysql-connector-python
"""

import asyncio
import httpx
import mysql.connector
from mysql.connector import pooling
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ===========================================================================
# Configuración y Pool de Base de Datos
# ===========================================================================
CIA_API_URL = "http://127.0.0.1:8000"

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "password",
    "database": "chat_seguro",
}

# Pool de conexiones para evitar abrir/cerrar conexiones constantemente
db_pool = pooling.MySQLConnectionPool(
    pool_name="chat_pool",
    pool_size=5,
    **DB_CONFIG
)

app = FastAPI(title="Chat Seguro - Backend")

# Activar soporte para CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Aceptar peticiones provenientes de cualquier origen
    allow_methods=["GET", "POST", "OPTIONS"], # Permitir únicamente los métodos HTTP indicados
    allow_headers=["Content-Type"], # Permitir únicamente el envío de este tipo de cabecera
)

def get_connection():
    return db_pool.get_connection()

# ===========================================================================
# Modelos
# ===========================================================================
class MensajeEntrante(BaseModel):
    remitente_id: int
    destinatario_id: int
    texto: str

# ===========================================================================
# Endpoints
# ===========================================================================

# Consultar la base de datos y devolver al navegador la lista de usuarios para llenar desplegables
@app.get("/chat/usuarios")
def listar_usuarios():
    with get_connection() as conn:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT id, nombre FROM usuarios ORDER BY id")
            return cursor.fetchall()

# Toma mensaje del Frontend, llama a cifrar y firmar, y hace el INSERT en la base de datos
@app.post("/chat/enviar")
async def enviar_mensaje(msg: MensajeEntrante):
    if not msg.texto.strip():
        raise HTTPException(400, "El mensaje no puede estar vacío")

    async with httpx.AsyncClient() as client:
        # 1) CIFRADO
        r_encrypt = await client.post(f"{CIA_API_URL}/confidentiality/encrypt", json={"message": msg.texto})
        if r_encrypt.status_code != 200:
            raise HTTPException(502, "Error cifrando el mensaje en CIA API")
        ciphertext = r_encrypt.json()["ciphertext"]

        # 2) FIRMA
        r_sign = await client.post(f"{CIA_API_URL}/integrity/sign", json={"message": ciphertext})
        if r_sign.status_code != 200:
            raise HTTPException(502, "Error firmando el mensaje en CIA API")
        firma = r_sign.json()["signature"]

    # 3) GUARDADO EN BD
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO mensajes (remitente_id, destinatario_id, mensaje_cifrado, firma)
                   VALUES (%s, %s, %s, %s)""",
                (msg.remitente_id, msg.destinatario_id, ciphertext, firma),
            )
            conn.commit()

    return {"status": "ok"}

# Auxiliar para procesar un mensaje individual de forma asíncrona
async def procesar_mensaje(client: httpx.AsyncClient, fila: dict) -> dict:
    # Lanzar descifrado y verificación en paralelo para este mensaje
    task_decrypt = client.post(f"{CIA_API_URL}/confidentiality/decrypt", json={"ciphertext": fila["mensaje_cifrado"]})
    task_verify = client.post(f"{CIA_API_URL}/integrity/verify", json={"message": fila["mensaje_cifrado"], "signature": fila["firma"]})

    res_decrypt, res_verify = await asyncio.gather(task_decrypt, task_verify)

    texto = res_decrypt.json().get("plaintext", "[Error al descifrar]") if res_decrypt.status_code == 200 else "[Error al descifrar]"
    verificado = res_verify.json().get("valid", False) if res_verify.status_code == 200 else False

    return {
        "id": fila["id"],
        "remitente_id": fila["remitente_id"],
        "remitente_nombre": fila["remitente_nombre"],
        "texto": texto,
        "verificado": verificado,
        "timestamp": fila["timestamp"].isoformat(),
    }

# Lee los mensajes cifrados de la BD, consulta CIA API para descifrar texto y verificar su firma,
# y devuelve el chat legible con su estado de verificación
@app.get("/chat/mensajes/{usuario_a}/{usuario_b}")
async def obtener_mensajes(usuario_a: int, usuario_b: int):
    # LECTURA DE BD
    with get_connection() as conn:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(
                """SELECT m.id, m.remitente_id, m.mensaje_cifrado, m.firma,
                          m.timestamp, u.nombre AS remitente_nombre
                   FROM mensajes m
                   JOIN usuarios u ON u.id = m.remitente_id
                   WHERE (m.remitente_id = %s AND m.destinatario_id = %s)
                      OR (m.remitente_id = %s AND m.destinatario_id = %s)
                   ORDER BY m.timestamp ASC""",
                (usuario_a, usuario_b, usuario_b, usuario_a),
            )
            filas = cursor.fetchall()

    # DESCIFRADO Y VERIFICACIÓN EN PARALELO DE TODOS LOS MENSAJES
    async with httpx.AsyncClient() as client:
        tasks = [procesar_mensaje(client, fila) for fila in filas]
        resultado = await asyncio.gather(*tasks)

    return resultado

# Servir interfaz web 
app.mount("/", StaticFiles(directory=".", html=True), name="static")