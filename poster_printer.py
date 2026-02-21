import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
import math
import win32print
import win32ui
from PIL import ImageWin
import os

class PosterPrinter:
    def __init__(self, root):
        self.root = root
        self.root.title("Poster Printer - Impresión en Tiles")
        self.root.geometry("1400x900")
        
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
        
    def create_ui(self):
        main_paned = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        left_frame = ttk.Frame(main_paned, width=300)
        main_paned.add(left_frame)
        
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame)
        
        # CONTROLES
        control_canvas = tk.Canvas(left_frame)
        scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=control_canvas.yview)
        scrollable_frame = ttk.Frame(control_canvas)
        
        scrollable_frame.bind("<Configure>", lambda e: control_canvas.configure(scrollregion=control_canvas.bbox("all")))
        
        control_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        control_canvas.configure(yscrollcommand=scrollbar.set)
        
        control_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Cargar imagen
        ttk.Label(scrollable_frame, text="IMAGEN", font=('Arial', 10, 'bold')).pack(pady=(10,5), padx=10, anchor='w')
        ttk.Button(scrollable_frame, text="📁 Cargar Imagen", command=self.load_image).pack(pady=5, padx=10, fill='x')
        
        # Área de drag & drop simple
        self.drop_frame = tk.Frame(scrollable_frame, relief='groove', borderwidth=2, bg='#f0f0f0', height=50)
        self.drop_frame.pack(pady=5, padx=10, fill='x')
        self.drop_frame.pack_propagate(False)
        drop_label = tk.Label(self.drop_frame, text="📥 Arrastra imagen aquí", bg='#f0f0f0', fg='gray', font=('Arial', 9))
        drop_label.pack(expand=True)
        
        self.info_label = ttk.Label(scrollable_frame, text="No hay imagen cargada", wraplength=250)
        self.info_label.pack(pady=5, padx=10)
        
        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill='x', pady=10)
        
        # Papel
        ttk.Label(scrollable_frame, text="PAPEL", font=('Arial', 10, 'bold')).pack(pady=(5,5), padx=10, anchor='w')
        
        paper_frame = ttk.Frame(scrollable_frame)
        paper_frame.pack(pady=5, padx=10, fill='x')
        ttk.Label(paper_frame, text="Tamaño:").pack(anchor='w')
        self.paper_combo = ttk.Combobox(paper_frame, values=list(self.paper_sizes.keys()), state='readonly')
        self.paper_combo.set('A4')
        self.paper_combo.pack(fill='x')
        self.paper_combo.bind('<<ComboboxSelected>>', lambda e: self.update_preview())
        
        orient_frame = ttk.Frame(scrollable_frame)
        orient_frame.pack(pady=5, padx=10, fill='x')
        ttk.Label(orient_frame, text="Orientación:").pack(anchor='w')
        self.orient_var = tk.StringVar(value='vertical')
        ttk.Radiobutton(orient_frame, text="Vertical", value='vertical', variable=self.orient_var,
                       command=lambda: self.change_orientation('vertical')).pack(anchor='w')
        ttk.Radiobutton(orient_frame, text="Horizontal", value='horizontal', variable=self.orient_var,
                       command=lambda: self.change_orientation('horizontal')).pack(anchor='w')
        
        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill='x', pady=10)
        
        # Posición y tamaño
        ttk.Label(scrollable_frame, text="POSICIÓN Y TAMAÑO", font=('Arial', 10, 'bold')).pack(pady=(5,5), padx=10, anchor='w')
        
        ttk.Label(scrollable_frame, text="💡 Arrastra la imagen para mover\n💡 Arrastra las esquinas para escalar", 
                 foreground='gray', font=('Arial', 8)).pack(pady=5, padx=10)
        
        rotation_frame = ttk.Frame(scrollable_frame)
        rotation_frame.pack(pady=5, padx=10, fill='x')
        ttk.Label(rotation_frame, text="Rotación (°):").pack(anchor='w')
        rotation_slider = ttk.Scale(rotation_frame, from_=0, to=360, variable=self.rotation_angle,
                                   orient='horizontal', command=lambda v: self.update_preview())
        rotation_slider.pack(fill='x')
        self.rotation_label = ttk.Label(rotation_frame, text="0°")
        self.rotation_label.pack(anchor='w')
        self.rotation_angle.trace('w', lambda *args: self.rotation_label.config(text=f"{self.rotation_angle.get()}°"))
        
        btn_frame = ttk.Frame(scrollable_frame)
        btn_frame.pack(pady=5, padx=10, fill='x')
        ttk.Button(btn_frame, text="↻ 90°", command=self.rotate_90, width=8).pack(side='left', padx=2)
        ttk.Button(btn_frame, text="⟲ Centrar", command=self.center_image, width=10).pack(side='left', padx=2)
        
        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill='x', pady=10)
        
        # Opciones de impresión
        ttk.Label(scrollable_frame, text="OPCIONES DE IMPRESIÓN", font=('Arial', 10, 'bold')).pack(pady=(5,5), padx=10, anchor='w')
        
        overlap_frame = ttk.Frame(scrollable_frame)
        overlap_frame.pack(pady=5, padx=10, fill='x')
        ttk.Label(overlap_frame, text="Superposición (mm):").pack(anchor='w')
        overlap_slider = ttk.Scale(overlap_frame, from_=0, to=50, variable=self.overlap_mm,
                                  orient='horizontal', command=lambda v: self.update_preview())
        overlap_slider.pack(fill='x')
        self.overlap_label = ttk.Label(overlap_frame, text="5.0 mm")
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
        ttk.Label(bleed_frame, text="Dirección del borde:", font=('Arial', 9)).pack(anchor='w')
        ttk.Radiobutton(bleed_frame, text="⬅ Izquierda/Arriba (derecha tapa izq, abajo tapa arriba)", 
                       value='left', variable=self.bleed_direction,
                       command=self.update_preview).pack(anchor='w')
        ttk.Radiobutton(bleed_frame, text="➡ Derecha/Abajo (izquierda tapa der, arriba tapa abajo)", 
                       value='right', variable=self.bleed_direction,
                       command=self.update_preview).pack(anchor='w')
        
        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill='x', pady=10)
        
        # Info páginas
        self.pages_label = ttk.Label(scrollable_frame, text="Páginas: 0x0 = 0 hojas", font=('Arial', 10, 'bold'))
        self.pages_label.pack(pady=10, padx=10)
        
        # Zoom
        zoom_frame = ttk.Frame(scrollable_frame)
        zoom_frame.pack(pady=5, padx=10, fill='x')
        ttk.Label(zoom_frame, text="Zoom Vista:").pack(anchor='w')
        zoom_slider = ttk.Scale(zoom_frame, from_=0.5, to=3, value=self.display_scale,
                               orient='horizontal', command=self.on_zoom_change)
        zoom_slider.pack(fill='x')
        
        # Botones
        ttk.Button(scrollable_frame, text="🖨 IMPRIMIR", command=self.print_poster).pack(pady=10, padx=10, fill='x', ipady=10)
        ttk.Button(scrollable_frame, text="💾 Exportar PDF", command=self.export_pdf).pack(pady=5, padx=10, fill='x')
        
        # VISTA PREVIA
        ttk.Label(right_frame, text="VISTA PREVIA - ÁREA DE TRABAJO", font=('Arial', 12, 'bold')).pack(pady=5)
        
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
        
        ttk.Label(right_frame, text="💡 Arrastra la imagen | Arrastra esquinas para escalar | Rueda para zoom",
                 foreground='gray').pack(pady=5)
        
        self.draw_grid()
    
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
        """Calcula qué páginas realmente contienen imagen (no solo la caja)"""
        if self.original_image is None:
            return []
        
        paper_w, paper_h = self.get_paper_size_mm()
        overlap = self.overlap_mm.get()
        effective_w = paper_w - overlap
        effective_h = paper_h - overlap
        
        # Bounding box de la imagen
        img_left = self.img_x
        img_top = self.img_y
        img_right = self.img_x + self.img_width
        img_bottom = self.img_y + self.img_height
        
        # Calcular rango de páginas
        start_col = max(0, int(img_left / effective_w))
        start_row = max(0, int(img_top / effective_h))
        end_col = int(img_right / effective_w) + 1
        end_row = int(img_bottom / effective_h) + 1
        
        pages_with_content = []
        
        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                # Calcular bounds de esta página
                page_left = col * effective_w
                page_top = row * effective_h
                page_right = page_left + paper_w
                page_bottom = page_top + paper_h
                
                # Verificar si la imagen intersecta con esta página
                intersects = not (img_right <= page_left or img_left >= page_right or
                                img_bottom <= page_top or img_top >= page_bottom)
                
                if intersects:
                    pages_with_content.append((row, col))
        
        return pages_with_content
    
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
                self.image_path = filename
                self.original_image = Image.open(filename)
                
                if self.original_image.mode not in ('RGB', 'RGBA'):
                    self.original_image = self.original_image.convert('RGB')
                
                width, height = self.original_image.size
                file_size = os.path.getsize(filename) / 1024 / 1024
                self.info_label.config(text=f"{os.path.basename(filename)}\n{width}x{height} px\n{file_size:.2f} MB")
                
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
        workspace_w = paper_w * self.workspace_cols / 2
        workspace_h = paper_h * self.workspace_rows / 2
        self.img_x = workspace_w - self.img_width / 2
        self.img_y = workspace_h - self.img_height / 2
        self.update_preview()
    
    def on_zoom_change(self, value):
        self.display_scale = float(value)
        self.update_preview()
    
    def draw_grid(self):
        self.canvas.delete("all")
        
        paper_w, paper_h = self.get_paper_size_mm()
        
        # Dibujar cuadrícula de páginas
        for row in range(self.workspace_rows):
            for col in range(self.workspace_cols):
                x1 = self.mm_to_px(col * paper_w)
                y1 = self.mm_to_px(row * paper_h)
                x2 = self.mm_to_px((col + 1) * paper_w)
                y2 = self.mm_to_px((row + 1) * paper_h)
                
                self.canvas.create_rectangle(x1, y1, x2, y2, outline='#ccc', width=1)
        
        # Configurar scroll region
        total_w = self.mm_to_px(paper_w * self.workspace_cols)
        total_h = self.mm_to_px(paper_h * self.workspace_rows)
        self.canvas.configure(scrollregion=(0, 0, total_w, total_h))
    
    def update_preview(self):
        self.canvas.delete("all")
        
        paper_w, paper_h = self.get_paper_size_mm()
        overlap = self.overlap_mm.get()
        
        # Obtener páginas que realmente tienen imagen
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
        
        # Dibujar cuadrícula de páginas
        for row in range(self.workspace_rows):
            for col in range(self.workspace_cols):
                x1 = self.mm_to_px(col * paper_w)
                y1 = self.mm_to_px(row * paper_h)
                x2 = self.mm_to_px((col + 1) * paper_w)
                y2 = self.mm_to_px((row + 1) * paper_h)
                
                # Resaltar SOLO páginas que tienen imagen
                if (row, col) in pages_with_image:
                    self.canvas.create_rectangle(x1, y1, x2, y2, outline='#0066cc', width=2, fill='#e6f2ff', tags='grid')
                    # Numerar solo las páginas con imagen
                    page_num = pages_with_image.index((row, col)) + 1
                    self.canvas.create_text(x1 + 15, y1 + 15, text=str(page_num), 
                                          font=('Arial', 14, 'bold'), fill='#0066cc', tags='grid')
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
        total_w = self.mm_to_px(paper_w * self.workspace_cols)
        total_h = self.mm_to_px(paper_h * self.workspace_rows)
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
        
        # Handles más grandes en las esquinas
        handle_size = 10
        positions = [
            (x1, y1, 'nw'),
            (x2, y1, 'ne'),
            (x1, y2, 'sw'),
            (x2, y2, 'se'),
        ]
        
        for x, y, corner in positions:
            handle = self.canvas.create_rectangle(
                x - handle_size, y - handle_size, x + handle_size, y + handle_size,
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
        if self.original_image is None:
            messagebox.showwarning("Advertencia", "Por favor carga una imagen primero")
            return
        
        # Advertir si modo sangrado está activado
        if self.bleed_mode.get():
            response = messagebox.askyesno("Modo Sangrado Activado",
                                          "El modo sin bordes (sangrado) está activado.\n\n"
                                          "RECOMENDACIÓN: Usa 'Exportar PDF' para mejor resultado.\n\n"
                                          "¿Deseas continuar con impresión directa de todas formas?")
            if not response:
                return
        
        try:
            # Obtener lista de impresoras
            printers = [printer[2] for printer in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
            
            if not printers:
                messagebox.showerror("Error", "No se encontraron impresoras instaladas")
                return
            
            default_printer = win32print.GetDefaultPrinter()
            
            # Crear ventana de selección de impresora
            printer_dialog = tk.Toplevel(self.root)
            printer_dialog.title("Seleccionar Impresora")
            printer_dialog.geometry("400x300")
            printer_dialog.transient(self.root)
            printer_dialog.grab_set()
            
            ttk.Label(printer_dialog, text="Selecciona la impresora:", font=('Arial', 11, 'bold')).pack(pady=10, padx=10)
            
            # Info de impresión
            info_text = f"{self.pages_label.cget('text')}"
            ttk.Label(printer_dialog, text=info_text, font=('Arial', 10)).pack(pady=5)
            
            # Lista de impresoras
            frame = ttk.Frame(printer_dialog)
            frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            scrollbar = ttk.Scrollbar(frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            printer_listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, font=('Arial', 10))
            printer_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=printer_listbox.yview)
            
            # Llenar lista
            for i, printer in enumerate(printers):
                if printer == default_printer:
                    printer_listbox.insert(tk.END, f"{printer} (Predeterminada)")
                    printer_listbox.selection_set(i)
                else:
                    printer_listbox.insert(tk.END, printer)
            
            selected_printer = [None]
            
            def on_print():
                selection = printer_listbox.curselection()
                if selection:
                    idx = selection[0]
                    selected_printer[0] = printers[idx]
                    printer_dialog.destroy()
                else:
                    messagebox.showwarning("Advertencia", "Por favor selecciona una impresora")
            
            def on_cancel():
                printer_dialog.destroy()
            
            # Botones
            btn_frame = ttk.Frame(printer_dialog)
            btn_frame.pack(pady=10)
            
            ttk.Button(btn_frame, text="✅ Imprimir", command=on_print).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="❌ Cancelar", command=on_cancel).pack(side=tk.LEFT, padx=5)
            
            printer_dialog.wait_window()
            
            if not selected_printer[0]:
                return
            
            printer_name = selected_printer[0]
            
            # Preparar imagen - NO ROTAR AQUÍ, mantener orientación original
            paper_w, paper_h = self.get_paper_size_mm()
            overlap = self.overlap_mm.get()
            effective_w = paper_w - overlap
            effective_h = paper_h - overlap
            
            # Aplicar solo rotación manual del usuario
            img_to_print = self.original_image.copy()
            if self.rotation_angle.get() != 0:
                img_to_print = img_to_print.rotate(-self.rotation_angle.get(), expand=True, resample=Image.BICUBIC)
            
            # NO rotar por orientación aquí - mantener coordenadas originales
            # Calcular factor de escala con dimensiones ORIGINALES
            scale_factor = self.img_width / img_to_print.width
            
            # Obtener páginas con contenido
            pages_with_image = self.get_pages_with_image()
            
            # Filtrar páginas completamente vacías con validación estricta
            pages_to_print = []
            for row, col in pages_with_image:
                # Calcular área de esta página EN MM
                page_left_mm = col * effective_w
                page_top_mm = row * effective_h
                
                # Calcular qué parte de la imagen mostrar EN MM
                crop_left_mm = max(0, page_left_mm - self.img_x)
                crop_top_mm = max(0, page_top_mm - self.img_y)
                crop_right_mm = min(self.img_width, (page_left_mm + paper_w) - self.img_x)
                crop_bottom_mm = min(self.img_height, (page_top_mm + paper_h) - self.img_y)
                
                # Verificar que el área de crop es válida y tiene contenido
                if crop_right_mm > crop_left_mm and crop_bottom_mm > crop_top_mm:
                    # Convertir a PIXELS
                    crop_left_px = int(crop_left_mm / scale_factor)
                    crop_top_px = int(crop_top_mm / scale_factor)
                    crop_right_px = int(crop_right_mm / scale_factor)
                    crop_bottom_px = int(crop_bottom_mm / scale_factor)
                    
                    # Validar límites de imagen
                    if (crop_right_px > crop_left_px and crop_bottom_px > crop_top_px and
                        crop_left_px >= 0 and crop_top_px >= 0 and
                        crop_right_px <= img_to_print.width and crop_bottom_px <= img_to_print.height and
                        (crop_right_px - crop_left_px) > 10 and (crop_bottom_px - crop_top_px) > 10):
                        pages_to_print.append((row, col))
            
            if not pages_to_print:
                messagebox.showwarning("Advertencia", "No hay páginas con imagen para imprimir")
                return
            
            # Imprimir cada página
            hprinter = win32print.OpenPrinter(printer_name)
            
            try:
                total_pages = len(pages_to_print)
                current_page = 0
                
                for row, col in pages_to_print:
                    current_page += 1
                    
                    hdc = win32ui.CreateDC()
                    hdc.CreatePrinterDC(printer_name)
                    hdc.StartDoc(f"Poster - Página {current_page} de {total_pages}")
                    hdc.StartPage()
                    
                    # Calcular área de esta página EN MM (coordenadas originales)
                    page_left_mm = col * effective_w
                    page_top_mm = row * effective_h
                    
                    # Calcular qué parte de la imagen mostrar EN MM
                    crop_left_mm = max(0, page_left_mm - self.img_x)
                    crop_top_mm = max(0, page_top_mm - self.img_y)
                    crop_right_mm = min(self.img_width, (page_left_mm + paper_w) - self.img_x)
                    crop_bottom_mm = min(self.img_height, (page_top_mm + paper_h) - self.img_y)
                    
                    # Convertir a PIXELS de la imagen
                    crop_left_px = int(crop_left_mm / scale_factor)
                    crop_top_px = int(crop_top_mm / scale_factor)
                    crop_right_px = int(crop_right_mm / scale_factor)
                    crop_bottom_px = int(crop_bottom_mm / scale_factor)
                    
                    # Recortar tile de la imagen ORIGINAL (sin rotar)
                    cropped = img_to_print.crop((crop_left_px, crop_top_px, crop_right_px, crop_bottom_px))
                    
                    # ROTAR EL TILE si la orientación es horizontal
                    if self.orientation == 'horizontal':
                        cropped = cropped.rotate(-90, expand=True, resample=Image.BICUBIC)
                    
                    # Añadir número de página con tamaño PEQUEÑO (6-11pts)
                    if self.show_page_numbers.get():
                        draw = ImageDraw.Draw(cropped)
                        page_num = current_page
                        try:
                            # Tamaño pequeño: 9pts
                            font = ImageFont.truetype("arial.ttf", 9)
                        except:
                            font = ImageFont.load_default()
                        # Gris oscuro
                        draw.text((10, 10), str(page_num), fill='#4a4a4a', font=font)
                    
                    # Imprimir
                    dib = ImageWin.Dib(cropped)
                    printer_w = hdc.GetDeviceCaps(8)  # HORZRES
                    printer_h = hdc.GetDeviceCaps(10)  # VERTRES
                    dib.draw(hdc.GetHandleOutput(), (0, 0, printer_w, printer_h))
                    
                    hdc.EndPage()
                    hdc.EndDoc()
                    hdc.DeleteDC()
            finally:
                win32print.ClosePrinter(hprinter)
            
            messagebox.showinfo("Éxito", f"Impresión completada en '{printer_name}'\nTotal: {total_pages} páginas")
            
        except Exception as e:
            messagebox.showerror("Error de impresión", f"No se pudo imprimir:\n{str(e)}")
    
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
                temp_img_path = "temp_poster.png"
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
    root = tk.Tk()
    app = PosterPrinter(root)
    root.mainloop()
