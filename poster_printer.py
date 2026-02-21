import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkFont
from PIL import Image, ImageTk, ImageDraw, ImageFont
import math
import win32print
import win32ui
from PIL import ImageWin
import os
import sys
import json
import random
import tempfile
from about import show_about_dialog
from print_dialog import show_print_dialog

# Drag & Drop
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False
    print("tkinterdnd2 no disponible - drag & drop deshabilitado")

class FontManager:
    """Gestor de fuentes con fallback automático"""
    def __init__(self):
        self.base_path = self._get_base_path()
        self.fonts_loaded = {}
        self.load_aptos_fonts()
    
    def _get_base_path(self):
        """Obtener ruta base del proyecto"""
        if getattr(sys, 'frozen', False):
            return sys._MEIPASS
        else:
            return os.path.dirname(os.path.abspath(__file__))
    
    def load_aptos_fonts(self):
        """Intentar cargar fuentes Aptos desde resources/fonts"""
        fonts_dir = os.path.join(self.base_path, "resources", "fonts")
        
        aptos_variants = [
            ("Aptos", "Aptos.ttf"),
            ("Aptos-Bold", "Aptos-Bold.ttf"),
            ("Aptos-Italic", "Aptos-Italic.ttf"),
            ("Aptos-Black", "Aptos-Black.ttf"),
        ]
        
        for font_name, font_file in aptos_variants:
            font_path = os.path.join(fonts_dir, font_file)
            if os.path.exists(font_path):
                try:
                    # Registrar fuente (esto no siempre funciona en runtime)
                    self.fonts_loaded[font_name] = font_path
                    print(f"✓ Fuente encontrada: {font_name}")
                except Exception as e:
                    print(f"Error cargando {font_name}: {e}")
    
    def get_font(self, size=10, weight='normal', slant='roman'):
        """Obtener fuente con fallback automático"""
        # Intentar Aptos primero
        try:
            if weight == 'bold':
                return tkFont.Font(family='Aptos', size=size, weight='bold', slant=slant)
            else:
                return tkFont.Font(family='Aptos', size=size, weight=weight, slant=slant)
        except Exception:
            pass

        # Fallback a Segoe UI
        try:
            return tkFont.Font(family='Segoe UI', size=size, weight=weight, slant=slant)
        except Exception:
            pass

        # Fallback a Calibri
        try:
            return tkFont.Font(family='Calibri', size=size, weight=weight, slant=slant)
        except Exception:
            pass
        
        # Fallback final a Arial
        return tkFont.Font(family='Arial', size=size, weight=weight, slant=slant)


class VersionManager:
    """Gestor de versiones con rotación"""
    def __init__(self):
        self.base_path = self._get_base_path()
        self.version_data = self.load_version_info()
        self.current_version_index = 0
    
    def _get_base_path(self):
        """Obtener ruta base del proyecto"""
        if getattr(sys, 'frozen', False):
            return sys._MEIPASS
        else:
            return os.path.dirname(os.path.abspath(__file__))
    
    def load_version_info(self):
        """Cargar información de versiones desde JSON"""
        try:
            version_path = os.path.join(self.base_path, "resources", "data", "version_info.json")
            
            if os.path.exists(version_path):
                with open(version_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"✓ Versiones cargadas: {len(data['versions'])} encontradas")
                    return data
            else:
                print(f"version_info.json no encontrado en: {version_path}")
        except Exception as e:
            print(f"Error cargando version_info.json: {e}")
        
        # Fallback si no se puede cargar
        return {
            "current_version": "2.12.6",
            "versions": [
                {
                    "version": "2.12.6",
                    "date": "Noviembre 2025",
                    "description": "Correcciones de usabilidad pre-release"
                }
            ]
        }
    
    def get_current_version(self):
        """Obtener versión actual"""
        return self.version_data["current_version"]
    
    def get_next_version_data(self):
        """Rotar y obtener siguiente versión para mostrar"""
        if not self.version_data["versions"]:
            return {
                "version": "2.12.6",
                "date": "Noviembre 2025",
                "description": "Sin info"
            }
        
        # Rotar índice
        version_info = self.version_data["versions"][self.current_version_index]
        self.current_version_index = (self.current_version_index + 1) % len(self.version_data["versions"])
        
        return version_info


class PosterPrinter:
    def __init__(self, root):
        self.root = root
        self.root.title("Poster Printer - Impresión en Tiles")
        self.root.geometry("1400x900")
        
        # Inicializar gestores
        self.font_manager = FontManager()
        self.version_manager = VersionManager()
        
        # Configurar icono de la ventana
        self.setup_window_icon()
        
        # Configurar drag & drop en toda la ventana si está disponible
        if DND_AVAILABLE:
            self.setup_drag_drop()
        
        # Variables de configuración
        self.image_path = None
        self.original_image = None
        self.display_image = None
        self.paper_sizes = {
            'A4': (210, 297),
            'A3': (297, 420),
            'A5': (148, 210),
            'Carta': (216, 279),
            'Legal': (216, 356),
        }
        
        self.current_paper = 'A4'
        self.orientation = 'vertical'
        self.overlap_mm = tk.DoubleVar(value=5.0)
        self.show_cut_marks = tk.BooleanVar(value=True)
        self.show_page_numbers = tk.BooleanVar(value=True)
        self.rotation_angle = tk.IntVar(value=0)
        self.bleed_mode = tk.BooleanVar(value=False)
        self.bleed_direction = tk.StringVar(value='left')
        
        # Variables de imagen (en mm)
        self.img_x = 0
        self.img_y = 0
        self.img_width = 400
        self.img_height = 300
        
        # Variables de interacción
        self.drag_data = {"x": 0, "y": 0, "dragging": False, "resizing": False, "handle": None}
        self.selected = False
        
        # Escala de visualización (pixels por mm)
        self.display_scale = 1.5
        
        # Área de trabajo grande
        self.workspace_cols = 20
        self.workspace_rows = 20
        
        # Canvas IDs
        self.image_id = None
        self.selection_rect = None
        self.resize_handles = []
        
        self.create_ui()

        # Atajos de teclado
        self.root.bind("<Control-o>", lambda e: self.load_image())

    def setup_window_icon(self):
        """Configurar icono de la ventana desde resources"""
        try:
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            icon_path = os.path.join(base_path, "resources", "icons", "icon.png")
            if os.path.exists(icon_path):
                icon_img = Image.open(icon_path)
                icon_photo = ImageTk.PhotoImage(icon_img)
                self.root.iconphoto(True, icon_photo)
                print("✓ Icono de ventana cargado")
        except Exception as e:
            print(f"Error cargando icono de ventana: {e}")
    
    def create_ui(self):
        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        left_frame = ttk.Frame(main_paned, width=300)
        main_paned.add(left_frame)
        
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame)
        
        # CONTROLES
        self.control_canvas = tk.Canvas(left_frame)
        scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=self.control_canvas.yview)
        scrollable_frame = ttk.Frame(self.control_canvas)

        scrollable_frame.bind("<Configure>", lambda e: self.control_canvas.configure(scrollregion=self.control_canvas.bbox("all")))

        self.control_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        self.control_canvas.configure(yscrollcommand=scrollbar.set)

        self.control_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mousewheel en el panel izquierdo scrollea los controles
        def _on_control_mousewheel(event):
            self.control_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.control_canvas.bind("<MouseWheel>", _on_control_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_control_mousewheel)
        # Propagar a hijos cuando se creen (bind_all con filtro)
        self._control_mousewheel_handler = _on_control_mousewheel
        self._scrollable_frame = scrollable_frame
        
        # Cargar imagen
        title_font = self.font_manager.get_font(10, 'bold')
        ttk.Label(scrollable_frame, text="IMAGEN", font=title_font).pack(pady=(10,5), padx=10, anchor='w')
        ttk.Button(scrollable_frame, text="📁 Cargar Imagen", command=self.load_image).pack(pady=5, padx=10, fill='x')
        
        # Área de drag & drop simple
        self.drop_frame = tk.Frame(scrollable_frame, relief='groove', borderwidth=2, bg='#f0f0f0', height=50)
        self.drop_frame.pack(pady=5, padx=10, fill='x')
        self.drop_frame.pack_propagate(False)
        
        if DND_AVAILABLE:
            drop_text = "📥 Arrastra imagen aquí (o en cualquier parte de la ventana)"
        else:
            drop_text = "⚠️ Drag & Drop no disponible - ejecuta INSTALAR.bat"
        
        drop_label = tk.Label(self.drop_frame, text=drop_text, bg='#f0f0f0', fg='gray', 
                             font=self.font_manager.get_font(9))
        drop_label.pack(expand=True)
        
        self.info_label = ttk.Label(scrollable_frame, text="No hay imagen cargada", wraplength=250,
                                   font=self.font_manager.get_font(9))
        self.info_label.pack(pady=5, padx=10)
        
        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill='x', pady=10)
        
        # Papel
        ttk.Label(scrollable_frame, text="PAPEL", font=title_font).pack(pady=(5,5), padx=10, anchor='w')
        
        paper_frame = ttk.Frame(scrollable_frame)
        paper_frame.pack(pady=5, padx=10, fill='x')
        ttk.Label(paper_frame, text="Tamaño:", font=self.font_manager.get_font(9)).pack(anchor='w')
        self.paper_combo = ttk.Combobox(paper_frame, values=list(self.paper_sizes.keys()), state='readonly')
        self.paper_combo.set('A4')
        self.paper_combo.pack(fill='x')
        self.paper_combo.bind('<<ComboboxSelected>>', lambda e: self.update_preview())
        
        orient_frame = ttk.Frame(scrollable_frame)
        orient_frame.pack(pady=5, padx=10, fill='x')
        ttk.Label(orient_frame, text="Orientación:", font=self.font_manager.get_font(9)).pack(anchor='w')
        self.orient_var = tk.StringVar(value='vertical')
        ttk.Radiobutton(orient_frame, text="Vertical", value='vertical', variable=self.orient_var,
                       command=lambda: self.change_orientation('vertical')).pack(anchor='w')
        ttk.Radiobutton(orient_frame, text="Horizontal", value='horizontal', variable=self.orient_var,
                       command=lambda: self.change_orientation('horizontal')).pack(anchor='w')
        
        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill='x', pady=10)
        
        # Posición y tamaño
        ttk.Label(scrollable_frame, text="POSICIÓN Y TAMAÑO", font=title_font).pack(pady=(5,5), padx=10, anchor='w')
        
        ttk.Label(scrollable_frame, text="💡 Arrastra la imagen para mover\n💡 Arrastra las esquinas para escalar", 
                 foreground='gray', font=self.font_manager.get_font(8)).pack(pady=5, padx=10)
        
        rotation_frame = ttk.Frame(scrollable_frame)
        rotation_frame.pack(pady=5, padx=10, fill='x')
        ttk.Label(rotation_frame, text="Rotación (°):", font=self.font_manager.get_font(9)).pack(anchor='w')
        rotation_slider = ttk.Scale(rotation_frame, from_=0, to=360, variable=self.rotation_angle,
                                   orient='horizontal', command=lambda v: self.update_preview())
        rotation_slider.pack(fill='x')
        self.rotation_label = ttk.Label(rotation_frame, text="0°", font=self.font_manager.get_font(9))
        self.rotation_label.pack(anchor='w')
        self.rotation_angle.trace('w', lambda *args: self.rotation_label.config(text=f"{self.rotation_angle.get()}°"))
        
        btn_frame = ttk.Frame(scrollable_frame)
        btn_frame.pack(pady=5, padx=10, fill='x')
        ttk.Button(btn_frame, text="↻ 90°", command=self.rotate_90, width=8).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="⟲ Centrar", command=self.center_image, width=10).pack(side='left', padx=2)
        
        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill='x', pady=10)
        
        # Opciones de impresión
        ttk.Label(scrollable_frame, text="OPCIONES DE IMPRESIÓN", font=title_font).pack(pady=(5,5), padx=10, anchor='w')
        
        overlap_frame = ttk.Frame(scrollable_frame)
        overlap_frame.pack(pady=5, padx=10, fill='x')
        ttk.Label(overlap_frame, text="Superposición (mm):", font=self.font_manager.get_font(9)).pack(anchor='w')
        overlap_slider = ttk.Scale(overlap_frame, from_=0, to=50, variable=self.overlap_mm,
                                  orient='horizontal', command=lambda v: self.update_preview())
        overlap_slider.pack(fill='x')
        self.overlap_label = ttk.Label(overlap_frame, text="5.0 mm", font=self.font_manager.get_font(9))
        self.overlap_label.pack(anchor='w')
        self.overlap_mm.trace('w', lambda *args: self.overlap_label.config(text=f"{self.overlap_mm.get():.1f} mm"))
        
        ttk.Checkbutton(scrollable_frame, text="Mostrar marcas de corte", variable=self.show_cut_marks,
                       command=self.update_preview).pack(pady=5, padx=10, anchor='w')
        
        ttk.Checkbutton(scrollable_frame, text="Numerar páginas en impresión", variable=self.show_page_numbers,
                       command=self.update_preview).pack(pady=5, padx=10, anchor='w')
        
        # Modo sin bordes (sangrado)
        ttk.Checkbutton(scrollable_frame, text="☑ Impresión sin bordes (sangrado)", variable=self.bleed_mode,
                       command=self.update_preview).pack(pady=5, padx=10, anchor='w')
        
        bleed_frame = ttk.Frame(scrollable_frame)
        bleed_frame.pack(pady=5, padx=20, fill='x')
        ttk.Label(bleed_frame, text="Dirección del borde:", font=self.font_manager.get_font(9)).pack(anchor='w')
        ttk.Radiobutton(bleed_frame, text="⬅ Izquierda/Arriba (derecha tapa izq, abajo tapa arriba)", 
                       value='left', variable=self.bleed_direction,
                       command=self.update_preview).pack(anchor='w')
        ttk.Radiobutton(bleed_frame, text="➡ Derecha/Abajo (izquierda tapa der, arriba tapa abajo)", 
                       value='right', variable=self.bleed_direction,
                       command=self.update_preview).pack(anchor='w')
        
        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill='x', pady=10)
        
        # Info páginas
        self.pages_label = ttk.Label(scrollable_frame, text="Páginas: 0x0 = 0 hojas", 
                                    font=self.font_manager.get_font(10, 'bold'))
        self.pages_label.pack(pady=10, padx=10)
        
        # Zoom
        zoom_frame = ttk.Frame(scrollable_frame)
        zoom_frame.pack(pady=5, padx=10, fill='x')
        ttk.Label(zoom_frame, text="Zoom Vista:", font=self.font_manager.get_font(9)).pack(anchor='w')
        zoom_slider = ttk.Scale(zoom_frame, from_=0.5, to=3, value=self.display_scale,
                               orient='horizontal', command=self.on_zoom_change)
        zoom_slider.pack(fill='x')
        
        # Botones
        ttk.Button(scrollable_frame, text="🖨 IMPRIMIR", command=self.print_poster).pack(pady=10, padx=10, fill='x', ipady=10)
        ttk.Button(scrollable_frame, text="💾 Exportar PDF", command=self.export_pdf).pack(pady=5, padx=10, fill='x')
        
        # VISTA PREVIA
        preview_font = self.font_manager.get_font(12, 'bold')
        ttk.Label(right_frame, text="VISTA PREVIA - ÁREA DE TRABAJO", font=preview_font).pack(pady=5)
        
        canvas_frame = ttk.Frame(right_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(canvas_frame, bg='#f0f0f0', cursor='arrow')
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        
        self.canvas.configure(xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set)
        
        self.canvas.grid(row=0, column=0, sticky='nsew')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        
        # Eventos
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        
        # Label de ayuda + versión clickeable (botón disimulado) con rotación
        help_frame = ttk.Frame(right_frame)
        help_frame.pack(pady=5, fill='x')
        
        help_font = self.font_manager.get_font(9)
        ttk.Label(help_frame, text="💡 Arrastra la imagen | Arrastra esquinas para escalar | Rueda para zoom",
                 foreground='gray', font=help_font).pack(side='left', padx=10)
        
        # Botón disimulado "Acerca de" con versión rotatoria
        current_version = self.version_manager.get_current_version()
        version_label = tk.Label(help_frame, text=f"v{current_version} ⓘ", 
                                foreground='#999', font=self.font_manager.get_font(8),
                                cursor='hand2', bg=self.root.cget('bg'))
        version_label.pack(side='right', padx=10)
        version_label.bind("<Button-1>", self.show_about_with_rotation)
        
        self.draw_grid()

        # Propagar mousewheel a todos los hijos del panel de controles
        self._bind_mousewheel_recursive(self._scrollable_frame)

    def _bind_mousewheel_recursive(self, widget):
        """Bind mousewheel a un widget y todos sus hijos para scroll del panel izquierdo."""
        widget.bind("<MouseWheel>", self._control_mousewheel_handler)
        for child in widget.winfo_children():
            self._bind_mousewheel_recursive(child)

    def show_about_with_rotation(self, event=None):
        """Mostrar diálogo About con versión rotativa"""
        version_data = self.version_manager.get_next_version_data()
        show_about_dialog(self.root, version_data)
    
    def mm_to_px(self, mm):
        return int(mm * self.display_scale)
    
    def px_to_mm(self, px):
        return px / self.display_scale
    
    def get_paper_size_mm(self):
        paper = self.paper_combo.get()
        width, height = self.paper_sizes[paper]
        if self.orientation == 'horizontal':
            width, height = height, width
        return width, height
    
    def get_pages_with_image(self):
        """
        Calcula qué páginas contienen el RECTÁNGULO DE SELECCIÓN (borde punteado).
        FIX v2.11.9: Usa el bounding box del rectángulo de selección, no solo la imagen.
        """
        if self.original_image is None:
            return []
        
        paper_w, paper_h = self.get_paper_size_mm()
        overlap = self.overlap_mm.get()
        effective_w = paper_w - overlap
        effective_h = paper_h - overlap
        
        # Bounding box del RECTÁNGULO DE SELECCIÓN (no de la imagen interior)
        # El rectángulo de selección está definido por img_x, img_y, img_width, img_height
        selection_left = self.img_x
        selection_top = self.img_y
        selection_right = self.img_x + self.img_width
        selection_bottom = self.img_y + self.img_height
        
        # Calcular rango de páginas que el rectángulo de selección toca
        start_col = max(0, int(selection_left / effective_w))
        start_row = max(0, int(selection_top / effective_h))
        end_col = int(selection_right / effective_w) + 1
        end_row = int(selection_bottom / effective_h) + 1
        
        pages_with_content = []
        
        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                # Calcular bounds de esta página
                page_left = col * effective_w
                page_top = row * effective_h
                page_right = page_left + paper_w
                page_bottom = page_top + paper_h
                
                # Verificar si el RECTÁNGULO DE SELECCIÓN intersecta con esta página
                intersects = not (selection_right <= page_left or selection_left >= page_right or
                                selection_bottom <= page_top or selection_top >= page_bottom)
                
                if intersects:
                    pages_with_content.append((row, col))
        
        return pages_with_content
    
    def _process_loaded_image(self, file_path):
        """Cargar y procesar una imagen desde ruta. Usado por load_image() y on_drop()."""
        self.image_path = file_path
        self.original_image = Image.open(file_path)

        if self.original_image.mode not in ('RGB', 'RGBA'):
            self.original_image = self.original_image.convert('RGB')

        width, height = self.original_image.size
        file_size = os.path.getsize(file_path) / 1024 / 1024
        self.info_label.config(text=f"{os.path.basename(file_path)}\n{width}x{height} px\n{file_size:.2f} MB")

        # Calcular tamaño de imagen basándose SOLO en la imagen original
        dpi = 300

        # Convertir pixels a mm (1 inch = 25.4mm)
        img_width_mm = (width / dpi) * 25.4
        img_height_mm = (height / dpi) * 25.4

        # Si la imagen es muy pequeña, escalarla a un tamaño visible (mínimo 100mm de ancho)
        if img_width_mm < 100:
            scale = 100 / img_width_mm
            img_width_mm = 100
            img_height_mm = img_height_mm * scale

        # Si la imagen es muy grande, escalarla a máximo 500mm de ancho
        if img_width_mm > 500:
            scale = 500 / img_width_mm
            img_width_mm = 500
            img_height_mm = img_height_mm * scale

        # Guardar dimensiones en mm
        self.img_width = img_width_mm
        self.img_height = img_height_mm

        # Posicionar en una ubicación visible del grid
        paper_w, paper_h = self.get_paper_size_mm()
        self.img_x = paper_w * 0.25
        self.img_y = paper_h * 0.25

        # Seleccionar automáticamente
        self.selected = True

        self.update_preview()

    def load_image(self):
        filetypes = [
            ('Todos los archivos de imagen', '*.jpg *.jpeg *.png *.bmp *.gif *.tiff *.tif *.webp'),
            ('JPEG', '*.jpg *.jpeg'),
            ('PNG', '*.png'),
            ('BMP', '*.bmp'),
            ('GIF', '*.gif'),
            ('TIFF', '*.tiff *.tif'),
            ('WebP', '*.webp'),
        ]

        filename = filedialog.askopenfilename(title="Seleccionar imagen", filetypes=filetypes)

        if filename:
            try:
                self._process_loaded_image(filename)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar la imagen:\n{str(e)}")
    
    def setup_drag_drop(self):
        """Configurar drag & drop en toda la ventana"""
        # Registrar toda la ventana principal para recibir archivos
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop)
        self.root.dnd_bind('<<DragEnter>>', self.on_drag_enter)
        self.root.dnd_bind('<<DragLeave>>', self.on_drag_leave)
    
    def on_drag_enter(self, event):
        """Cuando el archivo entra en la ventana"""
        # Cambiar color del drop frame para feedback visual
        self.drop_frame.config(bg='#e3f2fd', relief='solid', borderwidth=2)
    
    def on_drag_leave(self, event):
        """Cuando el archivo sale de la ventana"""
        # Restaurar color original
        self.drop_frame.config(bg='#f0f0f0', relief='groove', borderwidth=2)
    
    def on_drop(self, event):
        """Cuando se suelta un archivo en la ventana"""
        # Restaurar color
        self.drop_frame.config(bg='#f0f0f0', relief='groove', borderwidth=2)
        
        # Obtener ruta del archivo
        files = self.root.tk.splitlist(event.data)
        
        if not files:
            return
        
        file_path = files[0]  # Tomar el primer archivo
        
        # Validar extensión
        valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.tif', '.webp')
        if not file_path.lower().endswith(valid_extensions):
            messagebox.showerror("Error", 
                               f"Formato no soportado.\n\n"
                               f"Formatos válidos:\n"
                               f"JPG, PNG, BMP, GIF, TIFF, WebP")
            return
        
        # Cargar la imagen
        try:
            self._process_loaded_image(file_path)

            # Feedback visual de éxito
            self.drop_frame.config(bg='#c8e6c9')  # Verde claro
            self.root.after(1000, lambda: self.drop_frame.config(bg='#f0f0f0'))

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar la imagen:\n{str(e)}")
    
    def change_orientation(self, orient):
        self.orientation = orient
        self.update_preview()
    
    def rotate_90(self):
        current = self.rotation_angle.get()
        self.rotation_angle.set((current + 90) % 360)
    
    def center_image(self):
        paper_w, paper_h = self.get_paper_size_mm()
        overlap = self.overlap_mm.get()
        effective_w = paper_w - overlap
        effective_h = paper_h - overlap
        workspace_w = effective_w * self.workspace_cols / 2
        workspace_h = effective_h * self.workspace_rows / 2
        self.img_x = workspace_w - self.img_width / 2
        self.img_y = workspace_h - self.img_height / 2
        self.update_preview()
    
    def on_zoom_change(self, value):
        self.display_scale = float(value)
        self.update_preview()
    
    def draw_grid(self):
        self.canvas.delete("all")

        paper_w, paper_h = self.get_paper_size_mm()
        overlap = self.overlap_mm.get()
        effective_w = paper_w - overlap
        effective_h = paper_h - overlap

        # Dibujar cuadrícula de páginas (paso = effective, tamaño = paper)
        for row in range(self.workspace_rows):
            for col in range(self.workspace_cols):
                x1 = self.mm_to_px(col * effective_w)
                y1 = self.mm_to_px(row * effective_h)
                x2 = self.mm_to_px(col * effective_w + paper_w)
                y2 = self.mm_to_px(row * effective_h + paper_h)

                self.canvas.create_rectangle(x1, y1, x2, y2, outline='#ccc', width=1)

        # Configurar scroll region
        total_w = self.mm_to_px(effective_w * self.workspace_cols + overlap)
        total_h = self.mm_to_px(effective_h * self.workspace_rows + overlap)
        self.canvas.configure(scrollregion=(0, 0, total_w, total_h))
    
    def update_preview(self):
        self.canvas.delete("all")
        
        paper_w, paper_h = self.get_paper_size_mm()
        overlap = self.overlap_mm.get()
        
        # Obtener páginas que realmente tienen imagen (basado en rectángulo de selección)
        pages_with_image = []
        if self.original_image is not None:
            pages_with_image = self.get_pages_with_image()
            total_pages = len(pages_with_image)
            
            # Calcular dimensiones para mostrar
            if pages_with_image:
                cols = max(p[1] for p in pages_with_image) - min(p[1] for p in pages_with_image) + 1
                rows = max(p[0] for p in pages_with_image) - min(p[0] for p in pages_with_image) + 1
            else:
                cols = rows = 0
            
            self.pages_label.config(text=f"Páginas: {cols}x{rows} = {total_pages} hojas")
        else:
            self.pages_label.config(text="Páginas: 0x0 = 0 hojas")
        
        # Dibujar cuadrícula de páginas (paso = effective, tamaño = paper)
        effective_w = paper_w - overlap
        effective_h = paper_h - overlap
        for row in range(self.workspace_rows):
            for col in range(self.workspace_cols):
                x1 = self.mm_to_px(col * effective_w)
                y1 = self.mm_to_px(row * effective_h)
                x2 = self.mm_to_px(col * effective_w + paper_w)
                y2 = self.mm_to_px(row * effective_h + paper_h)

                # Resaltar SOLO páginas que tienen imagen
                if (row, col) in pages_with_image:
                    self.canvas.create_rectangle(x1, y1, x2, y2, outline='#0066cc', width=2, fill='#e6f2ff', tags='grid')
                    # Numerar solo las páginas con imagen
                    page_num = pages_with_image.index((row, col)) + 1
                    self.canvas.create_text(x1 + 15, y1 + 15, text=str(page_num),
                                          font=self.font_manager.get_font(14, 'bold'), fill='#0066cc', tags='grid')
                else:
                    self.canvas.create_rectangle(x1, y1, x2, y2, outline='#ccc', width=1, tags='grid')
        
        # Dibujar imagen si existe
        if self.original_image is not None:
            # Rotar imagen
            img = self.original_image.copy()
            if self.rotation_angle.get() != 0:
                img = img.rotate(-self.rotation_angle.get(), expand=True, resample=Image.BICUBIC)
            
            # Calcular tamaño en pixels para display
            display_w = self.mm_to_px(self.img_width)
            display_h = self.mm_to_px(self.img_height)
            
            if display_w > 0 and display_h > 0:
                img_resized = img.resize((int(display_w), int(display_h)), Image.LANCZOS)
                self.display_image = ImageTk.PhotoImage(img_resized)
                
                # Dibujar imagen
                img_x_px = self.mm_to_px(self.img_x)
                img_y_px = self.mm_to_px(self.img_y)
                self.image_id = self.canvas.create_image(img_x_px, img_y_px, image=self.display_image, 
                                                        anchor='nw', tags='image')
            
            # Dibujar handles de resize si está seleccionada
            if self.selected:
                self.draw_selection()
        
        # Configurar scroll region
        total_w = self.mm_to_px(effective_w * self.workspace_cols + overlap)
        total_h = self.mm_to_px(effective_h * self.workspace_rows + overlap)
        self.canvas.configure(scrollregion=(0, 0, total_w, total_h))

    def draw_selection(self):
        # Limpiar handles anteriores
        for handle in self.resize_handles:
            self.canvas.delete(handle)
        self.resize_handles = []
        
        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
        
        x1 = self.mm_to_px(self.img_x)
        y1 = self.mm_to_px(self.img_y)
        x2 = self.mm_to_px(self.img_x + self.img_width)
        y2 = self.mm_to_px(self.img_y + self.img_height)
        
        # Rectángulo de selección más visible
        self.selection_rect = self.canvas.create_rectangle(x1, y1, x2, y2, outline='#0066cc', width=3, dash=(5, 3), tags='selection')
        
        # Handles en las esquinas (dentro del rectángulo de selección)
        handle_size = 10
        positions = [
            (x1, y1, 'nw', x1, y1, x1 + handle_size * 2, y1 + handle_size * 2),
            (x2, y1, 'ne', x2 - handle_size * 2, y1, x2, y1 + handle_size * 2),
            (x1, y2, 'sw', x1, y2 - handle_size * 2, x1 + handle_size * 2, y2),
            (x2, y2, 'se', x2 - handle_size * 2, y2 - handle_size * 2, x2, y2),
        ]

        for cx, cy, corner, hx1, hy1, hx2, hy2 in positions:
            handle = self.canvas.create_rectangle(
                hx1, hy1, hx2, hy2,
                fill='#0066cc', outline='white', width=2, tags=f'handle_{corner}'
            )
            self.resize_handles.append(handle)
    
    def on_mouse_down(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        
        # Verificar si hizo click en un handle
        for handle in self.resize_handles:
            bbox = self.canvas.bbox(handle)
            if bbox and bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]:
                tags = self.canvas.gettags(handle)
                corner = tags[0].split('_')[1] if tags else None
                self.drag_data = {"x": x, "y": y, "resizing": True, "handle": corner, "dragging": False}
                return
        
        # Verificar si hizo click en la imagen
        if self.image_id:
            bbox = self.canvas.bbox(self.image_id)
            if bbox and bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]:
                self.selected = True
                self.drag_data = {"x": x, "y": y, "dragging": True, "resizing": False, "handle": None}
                self.update_preview()
                return
        
        # Click fuera de la imagen
        self.selected = False
        self.drag_data = {"x": 0, "y": 0, "dragging": False, "resizing": False, "handle": None}
        self.update_preview()
    
    
    def on_mouse_drag(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        
        if self.drag_data["resizing"] and self.drag_data["handle"]:
            # Resize manteniendo proporción
            dx_mm = self.px_to_mm(x - self.drag_data["x"])
            dy_mm = self.px_to_mm(y - self.drag_data["y"])
            
            corner = self.drag_data["handle"]
            
            # Calcular proporción original
            if self.original_image:
                img = self.original_image.copy()
                if self.rotation_angle.get() != 0:
                    img = img.rotate(-self.rotation_angle.get(), expand=True, resample=Image.BICUBIC)
                aspect_ratio = img.height / img.width
            else:
                aspect_ratio = self.img_height / self.img_width
            
            if corner == 'se':
                new_width = max(50, self.img_width + dx_mm)
                self.img_width = new_width
                self.img_height = new_width * aspect_ratio
                
            elif corner == 'sw':
                new_width = max(50, self.img_width - dx_mm)
                if new_width != self.img_width:
                    self.img_x += self.img_width - new_width
                    self.img_width = new_width
                    self.img_height = new_width * aspect_ratio
                    
            elif corner == 'ne':
                new_width = max(50, self.img_width + dx_mm)
                new_height = new_width * aspect_ratio
                self.img_y += self.img_height - new_height
                self.img_width = new_width
                self.img_height = new_height
                
            elif corner == 'nw':
                new_width = max(50, self.img_width - dx_mm)
                if new_width != self.img_width:
                    new_height = new_width * aspect_ratio
                    self.img_x += self.img_width - new_width
                    self.img_y += self.img_height - new_height
                    self.img_width = new_width
                    self.img_height = new_height
            
            self.drag_data["x"] = x
            self.drag_data["y"] = y
            self.update_preview()
            
        elif self.drag_data["dragging"]:
            # Move
            dx_mm = self.px_to_mm(x - self.drag_data["x"])
            dy_mm = self.px_to_mm(y - self.drag_data["y"])
            
            self.img_x += dx_mm
            self.img_y += dy_mm
            
            self.drag_data["x"] = x
            self.drag_data["y"] = y
            self.update_preview()
    
    def on_mouse_up(self, event):
        self.drag_data = {"x": 0, "y": 0, "dragging": False, "resizing": False, "handle": None}
    
    def on_mouse_move(self, event):
        if self.drag_data["resizing"] or self.drag_data["dragging"]:
            return
        
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        
        # Cambiar cursor según posición
        for handle in self.resize_handles:
            bbox = self.canvas.bbox(handle)
            if bbox and bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]:
                tags = self.canvas.gettags(handle)
                corner = tags[0].split('_')[1] if tags else None
                if corner in ['nw', 'se']:
                    self.canvas.config(cursor='size_nw_se')
                elif corner in ['ne', 'sw']:
                    self.canvas.config(cursor='size_ne_sw')
                return
        
        if self.image_id:
            bbox = self.canvas.bbox(self.image_id)
            if bbox and bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]:
                self.canvas.config(cursor='fleur')
                return
        
        self.canvas.config(cursor='arrow')
    
    def on_mousewheel(self, event):
        if event.delta > 0:
            new_scale = min(3, self.display_scale + 0.1)
        else:
            new_scale = max(0.5, self.display_scale - 0.1)
        self.display_scale = new_scale
        self.update_preview()
    
    def print_poster(self):
        """Abrir diálogo de impresión modular"""
        if self.original_image is None:
            messagebox.showwarning("Advertencia", "Por favor carga una imagen primero")
            return
        
        # Preparar datos para el diálogo
        paper_w, paper_h = self.get_paper_size_mm()
        pages_with_image = self.get_pages_with_image()
        
        if not pages_with_image:
            messagebox.showwarning("Advertencia", "No hay páginas con imagen para imprimir")
            return
        
        app_data = {
            'original_image': self.original_image,
            'rotation_angle': self.rotation_angle.get(),
            'orientation': self.orientation,
            'paper_w_mm': paper_w,
            'paper_h_mm': paper_h,
            'overlap_mm': self.overlap_mm.get(),
            'img_x': self.img_x,
            'img_y': self.img_y,
            'img_width': self.img_width,
            'img_height': self.img_height,
            'pages_with_image': pages_with_image,
            'show_page_numbers': self.show_page_numbers.get(),
            'font_manager': self.font_manager,
        }
        
        show_print_dialog(self.root, app_data)
    
    def export_pdf(self):
        if self.original_image is None:
            messagebox.showwarning("Advertencia", "Por favor carga una imagen primero")
            return
        
        filename = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        
        if filename:
            try:
                from reportlab.pdfgen import canvas as pdf_canvas
                from reportlab.lib.pagesizes import A4, landscape
                from reportlab.lib.units import mm
                
                paper_w, paper_h = self.get_paper_size_mm()
                
                if self.orientation == 'horizontal':
                    page_size = landscape((paper_w * mm, paper_h * mm))
                else:
                    page_size = (paper_w * mm, paper_h * mm)
                
                overlap = self.overlap_mm.get()
                bleed_mode = self.bleed_mode.get()
                bleed_dir = self.bleed_direction.get()
                
                # Preparar imagen - NO rotar aquí, mantener original
                img = self.original_image.copy()
                if self.rotation_angle.get() != 0:
                    img = img.rotate(-self.rotation_angle.get(), expand=True, resample=Image.BICUBIC)
                
                # NO rotar por orientación - mantener dimensiones originales
                actual_img_w_mm = self.img_width
                actual_img_h_mm = self.img_height
                
                # Calcular proporción actual
                aspect_ratio = img.height / img.width
                
                # Escalar imagen según el tamaño establecido
                dpi = 300
                target_width_px = int((actual_img_w_mm / 25.4) * dpi)
                target_height_px = int(target_width_px * aspect_ratio)
                
                img = img.resize((target_width_px, target_height_px), Image.LANCZOS)
                
                # Guardar imagen temporalmente
                temp_img_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                temp_img_path = temp_img_file.name
                temp_img_file.close()
                img.save(temp_img_path)
                
                effective_w = paper_w - overlap
                effective_h = paper_h - overlap
                
                # Obtener solo páginas que tienen imagen
                pages_with_image = self.get_pages_with_image()
                
                if not pages_with_image:
                    messagebox.showwarning("Advertencia", "No hay páginas con imagen para exportar")
                    return
                
                total_pages = len(pages_with_image)
                
                c = pdf_canvas.Canvas(filename, pagesize=page_size)
                
                for page_idx, (row, col) in enumerate(pages_with_image):
                    page_num = page_idx + 1
                    
                    # Calcular offset de esta página
                    page_left_mm = col * effective_w
                    page_top_mm = row * effective_h
                    
                    # Determinar posición en la matriz de páginas con imagen
                    min_col = min(p[1] for p in pages_with_image)
                    min_row = min(p[0] for p in pages_with_image)
                    max_col = max(p[1] for p in pages_with_image)
                    max_row = max(p[0] for p in pages_with_image)
                    
                    # Calcular área visible de esta página según modo sangrado
                    if bleed_mode:
                        # Determinar si tiene borde en cada lado
                        is_first_col = (col == min_col)
                        is_last_col = (col == max_col)
                        is_first_row = (row == min_row)
                        is_last_row = (row == max_row)
                        
                        if bleed_dir == 'left':
                            bleed_left = 0 if is_first_col else overlap
                            bleed_right = 0
                            bleed_top = 0 if is_first_row else overlap
                            bleed_bottom = 0
                        else:
                            bleed_left = 0
                            bleed_right = 0 if is_last_col else overlap
                            bleed_top = 0
                            bleed_bottom = 0 if is_last_row else overlap
                        
                        # Ajustar área de dibujo
                        draw_x = bleed_left * mm
                        draw_y = bleed_bottom * mm
                        draw_width = (paper_w - bleed_left - bleed_right) * mm
                        draw_height = (paper_h - bleed_top - bleed_bottom) * mm
                        
                        # Posición de la imagen considerando el sangrado
                        img_offset_x = (self.img_x - page_left_mm + bleed_left)
                        img_offset_y = (self.img_y - page_top_mm + bleed_bottom)
                        
                    else:
                        # Modo normal (sin sangrado)
                        draw_x = 0
                        draw_y = 0
                        draw_width = paper_w * mm
                        draw_height = paper_h * mm
                        img_offset_x = self.img_x - page_left_mm
                        img_offset_y = self.img_y - page_top_mm
                    
                    # Dibujar imagen (invertir Y para PDF)
                    c.drawImage(temp_img_path,
                              draw_x + (img_offset_x - (bleed_left if bleed_mode else 0)) * mm,
                              page_size[1] - draw_y - (img_offset_y - (bleed_bottom if bleed_mode else 0)) * mm - actual_img_h_mm * mm,
                              width=actual_img_w_mm * mm,
                              height=actual_img_h_mm * mm)
                    
                    # Añadir número de página si está activado
                    if self.show_page_numbers.get():
                        c.setFillColorRGB(0.2, 0.2, 0.2)
                        c.setFont("Helvetica-Bold", 12)
                        c.drawString(10 * mm, page_size[1] - 10 * mm, str(page_num))
                    
                    # Dibujar indicador de borde de sangrado
                    if bleed_mode:
                        c.setStrokeColorRGB(1, 0, 0)
                        c.setLineWidth(0.5)
                        if bleed_dir == 'left':
                            if not is_first_col:
                                c.line(bleed_left * mm, 0, bleed_left * mm, page_size[1])
                            if not is_first_row:
                                c.line(0, page_size[1] - bleed_top * mm, page_size[0], page_size[1] - bleed_top * mm)
                        else:
                            if not is_last_col:
                                c.line(page_size[0] - bleed_right * mm, 0, page_size[0] - bleed_right * mm, page_size[1])
                            if not is_last_row:
                                c.line(0, bleed_bottom * mm, page_size[0], bleed_bottom * mm)
                    
                    c.showPage()
                
                c.save()
                
                # Limpiar archivo temporal
                if os.path.exists(temp_img_path):
                    os.remove(temp_img_path)
                
                bleed_info = ""
                if bleed_mode:
                    bleed_info = f"\n\nModo sangrado: {'Izquierda/Arriba' if bleed_dir == 'left' else 'Derecha/Abajo'}"
                
                messagebox.showinfo("Éxito", f"PDF exportado exitosamente:\n{filename}{bleed_info}")
                
            except ImportError:
                messagebox.showerror("Error", "Falta la librería 'reportlab'.\nInstálala con: pip install reportlab")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo exportar el PDF:\n{str(e)}")


if __name__ == "__main__":
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    
    app = PosterPrinter(root)
    root.mainloop()
