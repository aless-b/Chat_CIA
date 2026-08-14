CREATE DATABASE IF NOT EXISTS chat_seguro;
USE chat_seguro;

-- Tabla de Usuarios que participan en el chat
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE
);

-- Mensajes: se guarda el mensaje CIFRADO + su FIRMA, el texto plano no se guarda en la base de datos
CREATE TABLE IF NOT EXISTS mensajes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    remitente_id INT NOT NULL,
    destinatario_id INT NOT NULL,
    mensaje_cifrado TEXT NOT NULL,      -- salida de /confidentiality/encrypt
    firma TEXT NOT NULL,                -- salida de /integrity/sign
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (remitente_id) REFERENCES usuarios(id),
    FOREIGN KEY (destinatario_id) REFERENCES usuarios(id)
);

-- Datos de ejemplo para usuarios
INSERT INTO usuarios (nombre) VALUES ('Alice'), ('Bob'), ('Paul');

