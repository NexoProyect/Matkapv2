# Matkap Enhanced v2.1

Herramienta avanzada para análisis, captura y procesamiento de mensajes de bots de Telegram con interfaz gráfica forkeada de https://github.com/0x6rss/matkap.

## Características Principales

### Captura de mensajes
- Forward automático de mensajes desde chats objetivo
- Soporte para rango personalizado de Message IDs
- Opción de evitar mensajes ya vistos
- Auto-guardado de datos capturados

### Análisis inteligente con APIs externas
- Detección de patrones sospechosos:
  - Phishing
  - Credenciales
  - Criptomonedas
  - URLs maliciosas
- Extracción de URLs
- Cálculo de riesgo por mensaje
- Generación de reportes

### Gestión de perfiles recurrentes
- Guardado/carga de configuraciones
- Encriptación de tokens (si cryptography está disponible)
- Sistema de perfiles reutilizables

### Batch Processing
- Procesamiento de múltiples tokens
- Importación desde archivos
- Validación automática

### Extras
- Exportación de logs
- Exportación de IOCs
- Interfaz gráfica completa (Tkinter)
- Soporte para Telethon

---

## 🖥️ Instalación

```bash
git clone https://github.com/tuusuario/matkap-enhanced.git
cd matkap-enhanced
pip install -r requirements.txt
```

### Configuración

Crea un archivo .env en la raíz con el siguiente formato:
```env
TELEGRAM_API_ID=tu_api_id
TELEGRAM_API_HASH=tu_api_hash
TELEGRAM_PHONE=tu_numero
```

### Uso
```
python matkap2.py
```

***Flujo básico:**
- Introducir Bot Token
- Ejecutar Start Attack
- Introducir Chat ID objetivo
- Forward Messages
- Analizar resultados en pestaña "Analysis"

### Exportación
- Reportes en JSON
- Indicadores de Compromiso (IOCs)
- Logs de actividad

### Advertencia
Esta herramienta está destinada exclusivamente para investigación de seguridad y uso ético.
El uso indebido puede violar leyes locales e internacionales.

❤️ Contribuciones
Pull requests y mejoras son bienvenidas.

***Me dejas una star?***
