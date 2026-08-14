# Chat Seguro — CIA API + MySQL + HTML/JS

Aplicación de chat que cifra, firma y verifica la integridad de cada
mensaje usando `cia_api.py`, guardando todo en MySQL.

## Arquitectura

```
┌─────────────────────────┐
│        NAVEGADOR        │
│  http://127.0.0.1:8001  │
└────────────┬────────────┘
             │
             │ 1. Pide la interfaz gráfica (GET /)
             │ 2. Sirve index.html estático (app.mount)
             ▼
┌──────────────────────────────────────────────────────────┐
│              BACKEND CHAT (puerto 8001)                  │
│                   backend_chat.py                        │
└────────────┬─────────────────────────────────┬───────────┘
             │                                 │
             │ 3. Llama a endpoints            │ 4. Guarda / Lee datos
             │    (/encrypt, /decrypt,         │    (mensajes cifrados
             │     /sign, /verify)             │     y firmas HMAC)
             ▼                                 ▼
┌──────────────────────────┐     ┌──────────────────────────┐
│   CIA API (puerto 8000)  │     │       BASE DE DATOS      │
│        cia_api.py        │     │          MySQL           │
└──────────────────────────┘     └──────────────────────────┘
```

`backend_chat.py` cumple **dos roles a la vez**:
1. Es la API intermedia que cifra/firma/guarda/descifra/verifica.
2. Sirve el propio `index.html` (vía `app.mount("/", StaticFiles(...))`),
   todo vive en el mismo origen
   (`http://127.0.0.1:8001/`).

## Archivos del proyecto

```
Chat_CIA/
├── cia_api.py         ← API (cifrado/firma), corre en el puerto 8000
├── backend_chat.py     ← Backend del chat + sirve el frontend, puerto 8001
├── index.html            ← Interfaz visual (servida por backend_chat.py)
├── schema.sql              ← Script para crear la BD en MySQL
```

## 1. Preparar la base de datos

Con MySQL corriendo, ejecuta el script (desde PowerShell, con `mysql` en el PATH):

```powershell
mysql -u root -p < schema.sql
```

O ábrelo y ejecútalo desde **MySQL Workbench** si prefieres no usar la
terminal. Esto crea la base `chat_seguro`, las tablas `usuarios` y
`mensajes`, y tres usuarios de ejemplo: **Alice**, **Bob** y **Paul**.

## 2. Instalar dependencias de Python

Usa `python -m pip` para asegurarte de instalar en la versión correcta
de Python que vas a usar para correr los servidores:

```powershell
python -m pip install fastapi "uvicorn[standard]" cryptography httpx mysql-connector-python
```

> Nota: esta versión de `backend_chat.py` usa **`httpx`** (asíncrono) en
> vez de `requests`, y un **pool de conexiones** MySQL en vez de abrir
> una conexión nueva por cada petición. Asegúrate de instalar `httpx`,
> no `requests`.

## 3. Configurar la contraseña de MySQL

Abre `backend_chat.py` y ajusta `DB_CONFIG` con tus credenciales reales:

```python
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "password",   # <-- pon aquí tu password real de MySQL
    "database": "chat_seguro",
}
```

## 4. Levantar los dos servidores (necesitas 2 ventanas de terminal)

**Ventana 1 — la CIA API:**
```powershell
python -m uvicorn cia_api:app --reload --port 8000
```

**Ventana 2 — el backend del chat (también sirve el frontend):**
```powershell
python -m uvicorn backend_chat:app --reload --port 8001
```

Si `uvicorn` no se reconoce como comando en tu PowerShell, usa siempre
`python -m uvicorn ...` como arriba — es la forma más confiable en
Windows.

## 5. Abrir el chat

Entra desde el navegador a:

```
http://127.0.0.1:8001/
```

Esto carga `index.html` servido por `backend_chat.py`.

## Cómo probarlo

1. En el selector "Yo soy" elige **Alice**; en "Hablando con" verás a
   **Bob** y **Paul** (el selector se filtra automáticamente para no
   mostrarte a ti mismo).
2. Escribe un mensaje y presiona Enter o "Enviar".
3. El mensaje aparece con la etiqueta **"Mensaje verificado"** una vez que el backend confirma la
   firma (así se ve el flujo completo: cifrar → firmar → guardar → leer
   → descifrar → verificar).
4. Cambia "Yo soy" a **Bob** o **Paul** para ver la conversación desde
   otro punto de vista.

> Nota: el auto-refresco automático (polling) está desactivado en esta
> versión del frontend — los mensajes se actualizan al enviar o al
> cambiar de usuario/conversación, no cada pocos segundos.

## Dónde está cada parte del flujo

| Paso | Archivo | Función |
|---|---|---|
| Cifrado | `backend_chat.py` | `enviar_mensaje()` — llamada a `/confidentiality/encrypt` |
| Firma | `backend_chat.py` | `enviar_mensaje()` — llamada a `/integrity/sign` |
| Guardado en BD | `backend_chat.py` | `enviar_mensaje()` — `INSERT INTO mensajes` |
| Lectura desde BD | `backend_chat.py` | `obtener_mensajes()` — `SELECT ... FROM mensajes` |
| Descifrado | `backend_chat.py` | `procesar_mensaje()` — llamada a `/confidentiality/decrypt` |
| Verificación | `backend_chat.py` | `procesar_mensaje()` — llamada a `/integrity/verify` |
| Servir el frontend | `backend_chat.py` | `app.mount("/", StaticFiles(...))` al final del archivo |
| Etiqueta "No verificado" / "Mensaje verificado" | `index.html` | `pintarMensajes()` |

## Problemas comunes en Windows

| Problema | Causa probable | Solución |
|---|---|---|
| `'uvicorn' no se reconoce como comando` | No está en el PATH | Usa `python -m uvicorn ...` |
| `ModuleNotFoundError: No module named 'httpx'` (u otro módulo) | Se instaló en otra versión de Python | Reinstala con `python -m pip install ...` |
| `Access denied for user 'root'` | Contraseña incorrecta en `DB_CONFIG` | Revisa la contraseña de tu MySQL |
| Puerto 8000 u 8001 ocupado | Otro proceso lo está usando | Cambia `--port` y actualiza `CIA_API_URL` en `backend_chat.py` o `BACKEND_URL` en `index.html` |

## Nota importante

Si reinicias `cia_api.py`, sus llaves de cifrado y firma se regeneran
(están en memoria, no en disco). Los mensajes guardados en MySQL antes
del reinicio ya no se podrán descifrar ni verificar correctamente —
esto es una limitación esperada del ejercicio, no un error tuyo.
