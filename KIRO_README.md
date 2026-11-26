# Guía de Contexto y Reglas de Desarrollo para KIRO (AI Assistant)

> **PROPÓSITO DE ESTE ARCHIVO:**  
> Proporcionar a **Kiro** (asistente de Inteligencia Artificial) el contexto técnico completo, rutas de ejecutables, reglas estrictas del stack y buenas prácticas de desarrollo para el proyecto **Queryback** en el **Hackathon NFL Big Data Bowl - UNAM / AWS**.

---

## 1. Identidad y Arquitectura del Proyecto

- **Nombre del proyecto:** `Queryback`
- **Evento:** Hackathon NFL Big Data Bowl UNAM / AWS.
- **Objetivo:** Hoja de Protección para el coordinador ofensivo: tiempo seguro del QB, lado de la presión y 3 claves por partido (ver `README.md` y `.kiro/steering/equipo.md`).
- **Arquitectura:**
  - **Backend:** FastAPI (Python 3.12) sirviendo endpoints analíticos bajo `/api/...`.
  - **Frontend:** Dashboard SPA en React 18, TypeScript, Vite y Tailwind CSS (consumiendo datos con Recharts).
  - **IA (Opcional/Complementaria):** Amazon Bedrock (modelo Amazon Nova Pro) mediante Strands Agents y Boto3.
  - **Hosting / Despliegue:** AWS hospedará la aplicación directamente desde el paquete generado por `setup.cmd --entregar`.

---

## 2. Entorno Aislado y Rutas de Ejecutables (Windows)

Todo el entorno se encuentra **completamente contenido** dentro de la carpeta del proyecto.  
**KIRO: NUNCA asumas comandos globales (`python`, `pip`, `npm`, `node`) del sistema operativo.** Usa siempre las rutas del entorno local del proyecto:

| Componente | Ruta en el Proyecto | Versión Fija |
|---|---|---|
| **Python** | `.\.venv\Scripts\python.exe` | **3.12.12** |
| **Uvicorn** | `.\.venv\Scripts\uvicorn.exe` | **0.34.3** |
| **uv** | `.\.hackathon\.tools\uv\uv.exe` | **0.11.19** |
| **Node.js** | `.\.hackathon\.tools\node\node.exe` | **22.23.1** |
| **npm** | `.\.hackathon\.tools\node\npm.cmd` | **10.9.8** |

---

## 3. Stack Tecnológico Estrictamente Bloqueado

> [!CAUTION]
> **PROHIBIDO AGREGAR NUEVAS DEPENDENCIAS O CAMBIAR VERSIONES:**  
> AWS validará el stack antes del despliegue mediante checksums y versiones fijas. Si agregas paquetes o cambias versiones en `requirements.txt` o `package.json`, la entrega fallará y AWS no hospedará la aplicación.

### Backend (`requirements.lock`)
- `python == 3.12.12`
- `fastapi == 0.115.14`
- `uvicorn == 0.34.3`
- `pydantic == 2.11.7`
- `pandas == 2.2.3`
- `numpy == 2.1.3`
- `strands-agents == 1.64.0`
- `boto3 == 1.44.0`
- `pytest == 8.3.5`
- `httpx == 0.28.1`

### Frontend (`dashboard/package.json`)
- `react == 18.3.1`
- `react-dom == 18.3.1`
- `recharts == 3.10.1`
- `vite == 5.4.21`
- `typescript == 5.7.3`
- `tailwindcss == 3.4.19`
- `@types/react == 18.3.31`

---

## 4. Reglas Críticas de Desarrollo que KIRO DEBE Cumplir

### ⚠️ Regla 1: Rutas de Fetch en el Frontend (Sin diagonal inicial)
- En AWS, la aplicación se publica bajo una subruta (ej. `/evento/equipo/`).
- **CORRECTO:** `fetch('api/mi-endpoint')`
- **INCORRECTO:** `fetch('/api/mi-endpoint')` *(rompe en producción con error 404)*
- **INCORRECTO:** `fetch('http://localhost:8000/api/...')` *(jamás usar URLs absolutas ni localhost)*
- Aplica a todas las llamadas API, enlaces internos y rutas de recursos.

### ⚠️ Regla 2: Configuración de Vite (`dashboard/vite.config.ts`)
- Mantener siempre `base: './'`.
- En desarrollo, Vite maneja un proxy hacia `http://localhost:8000` para `/api`.

### ⚠️ Regla 3: Estructura del Backend (`backend/main.py`)
- Siempre debe existir el endpoint de salud:
  ```python
  @app.get("/health")
  def health() -> dict:
      return {"status": "ok"}
  ```
- Todos los demás endpoints del equipo deben definirse bajo el prefijo `/api/...` (ej. `/api/analytics`, `/api/query`, etc.).

### ⚠️ Regla 4: Tailwind CSS versión 3.x
- El proyecto usa **Tailwind CSS 3.4.19**.
- **PROHIBIDO** usar sintaxis de Tailwind 4 (no usar `@import "tailwindcss";`, `@theme`, ni `@tailwindcss/vite`).
- Toda personalización debe realizarse en `dashboard/tailwind.config.js`.

### ⚠️ Regla 5: Manejo de Datos (`data/`)
- La carpeta `data/` contiene los archivos del evento.
- Son de **solo lectura**. No modifiques ni sobreescribas los archivos fuente originales.
- Las rutas deben ser relativas a la raíz del proyecto.
- El servidor es efímero en AWS: no bases la lógica en guardar archivos en disco en caliente. Realiza cálculos en memoria al arrancar o al responder.

### ⚠️ Regla 6: Integración con Amazon Bedrock e IA
- La IA es complementaria: la aplicación **debe funcionar y mostrar su análisis principal aun si la IA o Bedrock no responden**.
- Modelo permitido: `os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-pro-v1:0")`.
- Región: `os.environ.get("AWS_REGION", "us-east-1")`.
- **Cero llaves quemadas:** En AWS se utiliza el rol IAM asignado a la tarea. No pases `aws_access_key_id` ni `aws_secret_access_key` en `boto3.client()`. Instáncialo solo así:
  ```python
  client = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
  ```
- **Carga de `.env` en local:** Para no instalar librerías externas como `python-dotenv`, usar esta función nativa al inicio de `backend/main.py`:
  ```python
  import os
  from pathlib import Path

  def cargar_env():
      f = Path(__file__).resolve().parent.parent / ".env"
      if f.exists():
          for linea in f.read_text(encoding="utf-8-sig").splitlines():
              linea = linea.strip()
              if linea and not linea.startswith("#") and "=" in linea:
                  k, v = linea.split("=", 1)
                  os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

  cargar_env()
  ```

---

## 5. Comandos para Ejecutar y Probar

### En Desarrollo Local:
- **Iniciar Backend:**
  ```powershell
  .\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000
  ```
- **Iniciar Frontend:**
  ```powershell
  .\.hackathon\.tools\node\npm.cmd --prefix dashboard run dev
  ```
- **Compilar Frontend (Vite Build):**
  ```powershell
  .\.hackathon\.tools\node\npm.cmd --prefix dashboard run build
  ```

### Validación y Entrega:
- **Validar el Stack (No modifica nada):**
  ```powershell
  .\.hackathon\setup.cmd --check
  ```
- **Generar ZIP de Entrega para AWS:**
  ```powershell
  .\.hackathon\setup.cmd --entregar
  ```

---

## 6. Checklist de Buenas Prácticas para KIRO

- [ ] ¿El nuevo endpoint está bajo `/api/...`?
- [ ] ¿El frontend consume mediante `fetch('api/...')` sin diagonal inicial?
- [ ] ¿La interfaz utiliza componentes de Recharts y estilos de Tailwind 3?
- [ ] ¿Se respetaron las versiones fijas sin modificar `requirements.lock` ni `package.json`?
- [ ] ¿El comando `.\.hackathon\setup.cmd --check` sigue dando `TODO OK`?
