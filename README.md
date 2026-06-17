# Tutor Inteligente con NLP

Sistema de tutoría inteligente basado en Cohere y Streamlit.  
Diseñado para el curso **Procesamiento de Lenguaje Natural** — UPeU, Escuela de Posgrado.

---

## Configuración inicial (una sola vez)

### 1. Instalar Python

Si aún no tienes Python instalado, descárgalo desde la página oficial:

👉 https://www.python.org/downloads/

Descarga la versión **3.10 o superior** para tu sistema operativo.

**Windows:** ejecuta el instalador `.exe` y marca la opción  
☑ **"Add Python to PATH"** antes de hacer clic en *Install Now*.

**macOS:** ejecuta el instalador `.pkg` y sigue los pasos del asistente.

Para verificar que la instalación fue exitosa, abre una terminal y escribe:

```bash
python3 --version
```

Deberías ver algo como `Python 3.11.x`.

---

### 2. Crear y activar el entorno virtual

```bash
# Crear el entorno (solo la primera vez)
python3 -m venv env
```

```bash
# Activar en macOS / Linux
source env/bin/activate
```

```bash
# Activar en Windows
env\Scripts\activate
```

> Cuando el entorno está activo verás `(env)` al inicio de la línea de tu terminal.  
> Para desactivarlo cuando termines: `deactivate`

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Pegar tu clave API de Cohere

Abre el archivo `.streamlit/secrets.toml` y reemplaza el texto de ejemplo:

```toml
COHERE_API_KEY = "PEGA_AQUI_TU_CLAVE_API"
```

Obtén tu clave gratuita en: https://dashboard.cohere.ai/api-keys

### 3. Ejecutar la aplicación

```bash
streamlit run tutor.py
```

Se abrirá una ventana en el navegador en `http://localhost:8501`.

---

## Cómo usar el tutor

1. Escribe tu **nombre** en la barra lateral.
2. Sube un **PDF** con el material del curso (libro, guía, artículo).
3. Escribe el **tema** del curso.
4. Completa el **diagnóstico inicial** (solo en tu primera sesión).
5. Conversa con el tutor: responderá con retroalimentación pedagógica.

> El tutor recuerda tu perfil entre sesiones (guardado en `data/perfiles.json`).

---

## Estructura del proyecto

```
tutor-inteligente-estudiante/
├── tutor.py              ← aplicación principal
├── requirements.txt      ← dependencias Python
├── .gitignore            ← excluye la clave API y los perfiles
├── .streamlit/
│   └── secrets.toml      ← pon aquí tu clave API
└── data/                 ← se crea automáticamente al primer uso
    └── perfiles.json     ← perfil de cada estudiante
```

> **Seguridad:** nunca compartas ni subas a internet el archivo `secrets.toml`.
