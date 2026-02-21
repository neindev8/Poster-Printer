# Poster Printer

Poster Printer es una herramienta de escritorio para Windows que permite convertir cualquier imagen en un póster grande dividiéndola en múltiples páginas (tiles) para luego ensamblarlas físicamente.

Podés cargar una imagen, posicionarla, escalarla, rotarla y configurarla sobre una grilla de páginas, ajustar el papel y el solapado, y luego imprimir cada hoja o exportarlas como PDF multipágina.

---

## 🚀 Funcionalidades

### Flujo principal
- Carga de imagen mediante:
  - Diálogo de archivo (**Ctrl+O**)
  - Arrastrar y soltar (con degradación elegante si `tkinterdnd2` no está instalado)
- Posicionamiento libre arrastrando con el mouse
- Redimensionado con handles en las esquinas (proporción bloqueada)
- Rotación:
  - Slider (0–360°)
  - Botón rápido de 90°
- Centrado automático en el espacio de trabajo
- Impresión o exportación a PDF

---

### 🧾 Papel y diseño
- Tamaños de papel:
  - A4
  - A3
  - A5
  - Carta
  - Legal
- Orientación:
  - Vertical
  - Horizontal
- Solapado (0–50 mm) con visualización real en la grilla
- Modo sangrado (borderless) con dirección configurable:
  - izquierda/arriba
  - derecha/abajo
- Activar/desactivar:
  - Marcas de corte
  - Numeración de páginas

---

### 🖼 Canvas de vista previa
- Espacio desplazable de hasta 20×20 páginas
- Zoom mediante slider y rueda del mouse
- Resalta solo las páginas que la imagen ocupa
- Numeración visible en cada tile
- Cursor contextual (mover/redimensionar)

---

### 🖨 Modos de impresión (3)

1️⃣ **Motor interno**
- Imprime hoja por hoja (tile-by-tile) usando Windows DC
- Tolerante a fallos individuales
- Calidad seleccionable:
  - Borrador
  - Normal
  - Alta
- Permite reimprimir páginas específicas:
  - Ejemplo: `1-3, 5, 7`

2️⃣ **Modo PDF de Windows**
- Genera un PDF multipágina
- Lo abre con el manejador de impresión del sistema

3️⃣ **Diálogo del sistema Windows**
- Genera PDF
- Lo envía directamente a la impresora seleccionada mediante `ShellExecute`

---

### 📄 Exportación a PDF
- Generación independiente con ReportLab
- Una página por tile
- Offsets correctos
- Soporte de sangrado
- Numeración opcional

---

## 🔧 Internamente

- `FontManager`:
  - Carga fuentes Aptos incluidas
  - Cadena de fallback: Segoe UI → Calibri → Arial
- `VersionManager`:
  - Lee historial de versiones desde JSON
- Todas las medidas se manejan en milímetros internamente
- Conversión a píxeles solo para representación visual
- Compilado como un único `.exe` usando PyInstaller

---

## 💻 Requisitos

- Windows 10 o 11
- Python (para desarrollo)
- Dependencias típicas:
  - reportlab
  - tkinter
  - opcional: tkinterdnd2

---

## 📦 Instalación (Usuarios)

1. Descargar la última versión desde la sección Releases.
2. Ejecutar `PosterPrinter.exe`.

---

## 🛠 Desarrollo

### Crear entorno virtual
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
