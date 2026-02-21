import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageDraw, ImageFont
import win32print
import win32ui
import win32api
from PIL import ImageWin
import os
import tempfile
import subprocess
import re
import atexit


class PrintDialog:
    """Diálogo de impresión modular con motor propio y delegación a Windows - v2.12.6"""
    
    def __init__(self, parent, app_data):
        """
        app_data debe contener:
        - original_image: PIL.Image
        - rotation_angle: int
        - orientation: str ('vertical' o 'horizontal')
        - paper_w_mm, paper_h_mm: float
        - overlap_mm: float
        - img_x, img_y, img_width, img_height: float (mm)
        - pages_with_image: list de (row, col)
        - show_page_numbers: bool
        - font_manager: FontManager instance
        """
        self.parent = parent
        self.app_data = app_data
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Imprimir Poster")
        self.dialog.geometry("650x580")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Centrar
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (650 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (580 // 2)
        self.dialog.geometry(f"650x580+{x}+{y}")

        # Escape para cerrar
        self.dialog.bind("<Escape>", lambda e: self.dialog.destroy())
        
        # Variables
        self.selected_printer = None
        self.print_mode = tk.StringVar(value="internal")  # "internal" o "windows"
        self.quality = tk.StringVar(value="normal")  # "draft", "normal", "high"
        self.enable_reprint = tk.BooleanVar(value=False)
        self.reprint_tiles = tk.StringVar(value="")
        self.windows_mode = tk.StringVar(value="pdf_print")
        
        # Obtener impresoras
        self.printers = self.get_printers()
        self.default_printer = win32print.GetDefaultPrinter() if self.printers else None
        
        self.create_ui()
    
    def get_printers(self):
        """Obtener lista de impresoras instaladas"""
        try:
            printers = [printer[2] for printer in win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
            return printers
        except Exception:
            return []
    
    def create_ui(self):
        """Crear interfaz del diálogo con arquitectura fija: Header + Content Scrolleable + Footer Fijo"""
        
        # ==================== CONTENEDOR PRINCIPAL ====================
        main_container = ttk.Frame(self.dialog)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # ==================== HEADER FIJO (no scrolleable) ====================
        header_frame = ttk.Frame(main_container, padding="15 10 15 5")
        header_frame.pack(fill=tk.X, side=tk.TOP)
        
        # Título
        title_font = self.app_data['font_manager'].get_font(14, 'bold')
        ttk.Label(header_frame, text="🖨 Configuración de Impresión", font=title_font).pack(pady=(0, 5))
        
        # Info de páginas
        total_pages = len(self.app_data['pages_with_image'])
        if total_pages > 0:
            cols = max(p[1] for p in self.app_data['pages_with_image']) - min(p[1] for p in self.app_data['pages_with_image']) + 1
            rows = max(p[0] for p in self.app_data['pages_with_image']) - min(p[0] for p in self.app_data['pages_with_image']) + 1
        else:
            cols = rows = 0
        
        info_font = self.app_data['font_manager'].get_font(11, 'bold')
        ttk.Label(header_frame, text=f"Páginas: {cols}×{rows} = {total_pages} hojas", 
                 font=info_font, foreground='#0066cc').pack(pady=(0, 5))
        
        ttk.Separator(header_frame, orient='horizontal').pack(fill='x')
        
        # ==================== CONTENIDO SCROLLEABLE ====================
        # Canvas con scrollbar para el contenido central
        canvas_frame = ttk.Frame(main_container)
        canvas_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
        
        content_canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=content_canvas.yview)
        
        # Frame scrolleable interno
        scrollable_content = ttk.Frame(content_canvas)
        
        scrollable_content.bind(
            "<Configure>",
            lambda e: content_canvas.configure(scrollregion=content_canvas.bbox("all"))
        )
        
        self._scroll_window_id = content_canvas.create_window((0, 0), window=scrollable_content, anchor="nw")
        content_canvas.configure(yscrollcommand=scrollbar.set)

        # Estirar el contenido al ancho completo del canvas
        def _on_canvas_configure(event):
            content_canvas.itemconfig(self._scroll_window_id, width=event.width)
        content_canvas.bind("<Configure>", _on_canvas_configure)

        content_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # ==================== CONTENIDO INTERNO (dentro del scroll) ====================
        content_inner = ttk.Frame(scrollable_content, padding="15 5 15 5")
        content_inner.pack(fill=tk.BOTH, expand=True)
        
        # --- Selección de impresora ---
        printer_frame = ttk.Frame(content_inner)
        printer_frame.pack(fill='x', pady=(0, 8))
        
        label_font = self.app_data['font_manager'].get_font(10, 'bold')
        ttk.Label(printer_frame, text="Impresora:", font=label_font).pack(anchor='w', pady=(0, 3))
        
        # Lista de impresoras (altura reducida para no ocupar tanto espacio)
        list_frame = ttk.Frame(printer_frame)
        list_frame.pack(fill='x', pady=(0, 3))
        
        list_scrollbar = ttk.Scrollbar(list_frame)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.printer_listbox = tk.Listbox(list_frame, yscrollcommand=list_scrollbar.set, 
                                         font=self.app_data['font_manager'].get_font(9), height=4)
        self.printer_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scrollbar.config(command=self.printer_listbox.yview)
        
        # Llenar lista
        for i, printer in enumerate(self.printers):
            if printer == self.default_printer:
                self.printer_listbox.insert(tk.END, f"{printer} (Predeterminada)")
                self.printer_listbox.selection_set(i)
            else:
                self.printer_listbox.insert(tk.END, printer)
        
        ttk.Separator(content_inner, orient='horizontal').pack(fill='x', pady=8)
        
        # --- MOTOR DE IMPRESIÓN ---
        ttk.Label(content_inner, text="Motor de Impresión:", font=label_font).pack(anchor='w', pady=(3, 3))
        
        mode_frame = ttk.Frame(content_inner)
        mode_frame.pack(fill='x', pady=(0, 8))
        
        # Motor interno
        internal_frame = ttk.Frame(mode_frame)
        internal_frame.pack(fill='x', pady=(0, 3))
        
        ttk.Radiobutton(internal_frame, text="🔧 Motor Interno (tolerante a fallos, tiles individuales)", 
                       value="internal", variable=self.print_mode,
                       command=self.on_mode_change).pack(anchor='w')
        
        # Opciones motor interno (indentadas)
        internal_opts = ttk.Frame(internal_frame, padding=(25, 3, 0, 0))
        internal_opts.pack(fill='x')
        
        quality_frame = ttk.Frame(internal_opts)
        quality_frame.pack(fill='x', pady=2)
        ttk.Label(quality_frame, text="Calidad:", 
                 font=self.app_data['font_manager'].get_font(9)).pack(side='left', padx=(0, 10))
        ttk.Radiobutton(quality_frame, text="Borrador", value="draft", 
                       variable=self.quality).pack(side='left', padx=5)
        ttk.Radiobutton(quality_frame, text="Normal", value="normal", 
                       variable=self.quality).pack(side='left', padx=5)
        ttk.Radiobutton(quality_frame, text="Alta", value="high", 
                       variable=self.quality).pack(side='left', padx=5)
        
        # Reimprimir tiles específicos
        reprint_check = ttk.Checkbutton(internal_opts, text="⚙ Reimprimir tiles específicos", 
                                       variable=self.enable_reprint,
                                       command=self.on_reprint_toggle)
        reprint_check.pack(anchor='w', pady=(3, 2))
        
        self.reprint_frame = ttk.Frame(internal_opts, padding=(20, 2, 0, 0))
        self.reprint_frame.pack(fill='x')
        
        ttk.Label(self.reprint_frame, text="Tiles (ej: 1-3, 5, 7, 10, 9):", 
                 font=self.app_data['font_manager'].get_font(8), foreground='gray').pack(anchor='w')
        self.reprint_entry = ttk.Entry(self.reprint_frame, textvariable=self.reprint_tiles, state='disabled')
        self.reprint_entry.pack(fill='x', pady=2)
        
        ttk.Separator(mode_frame, orient='horizontal').pack(fill='x', pady=8)
        
        # Motor Windows
        windows_frame = ttk.Frame(mode_frame)
        windows_frame.pack(fill='x', pady=(0, 3))
        
        ttk.Radiobutton(windows_frame, text="🪟 Motor de Windows (delegado al sistema)", 
                       value="windows", variable=self.print_mode,
                       command=self.on_mode_change).pack(anchor='w')
        
        # Opciones motor Windows (indentadas)
        windows_opts = ttk.Frame(windows_frame, padding=(25, 3, 0, 0))
        windows_opts.pack(fill='x')
        
        ttk.Radiobutton(windows_opts, text="📄 Generar PDF e imprimir (recomendado)", 
                       value="pdf_print", variable=self.windows_mode).pack(anchor='w', pady=2)
        ttk.Radiobutton(windows_opts, text="🖨 Imprimir con diálogo del sistema (trabajo único)", 
                       value="system_dialog", variable=self.windows_mode).pack(anchor='w', pady=2)
        
        # ==================== FOOTER FIJO (botones siempre visibles) ====================
        footer_frame = ttk.Frame(main_container, padding="15 8 15 15")
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttk.Separator(footer_frame, orient='horizontal').pack(fill='x', pady=(0, 10))
        
        btn_container = ttk.Frame(footer_frame)
        btn_container.pack()
        
        # Botones principales - SIEMPRE VISIBLES
        ttk.Button(btn_container, text="✅ Imprimir", 
                  command=self.on_print, width=15).pack(side='left', padx=5)
        ttk.Button(btn_container, text="❌ Cancelar", 
                  command=self.dialog.destroy, width=15).pack(side='left', padx=5)
    
    def on_mode_change(self):
        """Cambio de modo de impresión"""
        # Actualizar estados si es necesario en el futuro
        pass
    
    def on_reprint_toggle(self):
        """Activar/desactivar campo de reimprimir tiles"""
        if self.enable_reprint.get():
            self.reprint_entry.config(state='normal')
        else:
            self.reprint_entry.config(state='disabled')
            self.reprint_tiles.set("")
    
    def parse_tile_range(self, range_str, total_pages):
        """
        Parsear string de tiles: "1-3, 5, 7, 10, 9" → [1, 2, 3, 5, 7, 9, 10]
        """
        if not range_str.strip():
            return list(range(1, total_pages + 1))
        
        tiles = set()
        parts = [p.strip() for p in range_str.split(',')]
        
        for part in parts:
            if '-' in part:
                # Rango: "1-3"
                try:
                    start, end = part.split('-')
                    start = int(start.strip())
                    end = int(end.strip())
                    for i in range(start, end + 1):
                        if 1 <= i <= total_pages:
                            tiles.add(i)
                except (ValueError, TypeError):
                    pass
            else:
                # Individual: "5"
                try:
                    tile = int(part.strip())
                    if 1 <= tile <= total_pages:
                        tiles.add(tile)
                except (ValueError, TypeError):
                    pass
        
        return sorted(list(tiles))
    
    def on_print(self):
        """Ejecutar impresión según modo seleccionado"""
        # Validar impresora seleccionada
        selection = self.printer_listbox.curselection()
        if not selection:
            messagebox.showwarning("Advertencia", "Selecciona una impresora")
            return
        
        self.selected_printer = self.printers[selection[0]]
        
        # Ejecutar según modo
        if self.print_mode.get() == "internal":
            self.print_internal()
        else:
            if self.windows_mode.get() == "pdf_print":
                self.print_pdf_windows()
            else:
                self.print_system_dialog()
    
    def print_internal(self):
        """Motor interno - tiles individuales con tolerancia a fallos"""
        try:
            # Determinar tiles a imprimir
            total_pages = len(self.app_data['pages_with_image'])
            
            if self.enable_reprint.get():
                tile_numbers = self.parse_tile_range(self.reprint_tiles.get(), total_pages)
                if not tile_numbers:
                    messagebox.showwarning("Advertencia", "No se especificaron tiles válidos")
                    return
                pages_to_print = [self.app_data['pages_with_image'][i-1] for i in tile_numbers]
            else:
                pages_to_print = self.app_data['pages_with_image']
            
            # Preparar imagen
            img_to_print = self.app_data['original_image'].copy()
            if self.app_data['rotation_angle'] != 0:
                img_to_print = img_to_print.rotate(-self.app_data['rotation_angle'], 
                                                   expand=True, resample=Image.BICUBIC)
            
            scale_factor = self.app_data['img_width'] / img_to_print.width
            
            paper_w = self.app_data['paper_w_mm']
            paper_h = self.app_data['paper_h_mm']
            overlap = self.app_data['overlap_mm']
            effective_w = paper_w - overlap
            effective_h = paper_h - overlap
            
            # Abrir impresora
            hprinter = win32print.OpenPrinter(self.selected_printer)
            
            try:
                total_to_print = len(pages_to_print)
                
                for idx, (row, col) in enumerate(pages_to_print):
                    current_page = idx + 1
                    
                    hdc = win32ui.CreateDC()
                    hdc.CreatePrinterDC(self.selected_printer)
                    hdc.StartDoc(f"Poster - Tile {current_page} de {total_to_print}")
                    hdc.StartPage()
                    
                    # Calcular área
                    page_left_mm = col * effective_w
                    page_top_mm = row * effective_h
                    
                    crop_left_mm = max(0, page_left_mm - self.app_data['img_x'])
                    crop_top_mm = max(0, page_top_mm - self.app_data['img_y'])
                    crop_right_mm = min(self.app_data['img_width'], 
                                       (page_left_mm + paper_w) - self.app_data['img_x'])
                    crop_bottom_mm = min(self.app_data['img_height'], 
                                        (page_top_mm + paper_h) - self.app_data['img_y'])
                    
                    # Convertir a pixels
                    crop_left_px = int(crop_left_mm / scale_factor)
                    crop_top_px = int(crop_top_mm / scale_factor)
                    crop_right_px = int(crop_right_mm / scale_factor)
                    crop_bottom_px = int(crop_bottom_mm / scale_factor)
                    
                    # Recortar
                    cropped = img_to_print.crop((crop_left_px, crop_top_px, 
                                                crop_right_px, crop_bottom_px))
                    
                    # Rotar si horizontal
                    if self.app_data['orientation'] == 'horizontal':
                        cropped = cropped.rotate(-90, expand=True, resample=Image.BICUBIC)
                    
                    # Ajustar calidad
                    if self.quality.get() == "draft":
                        # Reducir resolución para borrador
                        w, h = cropped.size
                        cropped = cropped.resize((w//2, h//2), Image.NEAREST)
                    elif self.quality.get() == "high":
                        # Mantener calidad alta (sin cambios)
                        pass
                    
                    # Añadir número
                    if self.app_data['show_page_numbers']:
                        draw = ImageDraw.Draw(cropped)
                        # Si es reimpresión, usar número original del tile
                        if self.enable_reprint.get():
                            page_num = self.app_data['pages_with_image'].index((row, col)) + 1
                        else:
                            page_num = current_page
                        
                        try:
                            font = ImageFont.truetype("arial.ttf", 9)
                        except Exception:
                            font = ImageFont.load_default()
                        draw.text((10, 10), str(page_num), fill='#4a4a4a', font=font)
                    
                    # Imprimir
                    dib = ImageWin.Dib(cropped)
                    printer_w = hdc.GetDeviceCaps(8)
                    printer_h = hdc.GetDeviceCaps(10)
                    dib.draw(hdc.GetHandleOutput(), (0, 0, printer_w, printer_h))
                    
                    hdc.EndPage()
                    hdc.EndDoc()
                    hdc.DeleteDC()
                    
            finally:
                win32print.ClosePrinter(hprinter)
            
            self.dialog.destroy()
            messagebox.showinfo("Éxito", f"Impresión completada\nTotal: {total_to_print} tiles")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error en impresión:\n{str(e)}")
    
    def print_pdf_windows(self):
        """Generar PDF temporal y enviar a motor de Windows"""
        try:
            from reportlab.pdfgen import canvas as pdf_canvas
            from reportlab.lib.pagesizes import landscape
            from reportlab.lib.units import mm
            
            # Crear PDF temporal
            temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_pdf_path = temp_pdf.name
            temp_pdf.close()
            
            paper_w = self.app_data['paper_w_mm']
            paper_h = self.app_data['paper_h_mm']
            
            if self.app_data['orientation'] == 'horizontal':
                page_size = landscape((paper_w * mm, paper_h * mm))
            else:
                page_size = (paper_w * mm, paper_h * mm)
            
            overlap = self.app_data['overlap_mm']
            
            img = self.app_data['original_image'].copy()
            if self.app_data['rotation_angle'] != 0:
                img = img.rotate(-self.app_data['rotation_angle'], expand=True, resample=Image.BICUBIC)
            
            actual_img_w_mm = self.app_data['img_width']
            actual_img_h_mm = self.app_data['img_height']
            
            aspect_ratio = img.height / img.width
            dpi = 300
            target_width_px = int((actual_img_w_mm / 25.4) * dpi)
            target_height_px = int(target_width_px * aspect_ratio)
            
            img = img.resize((target_width_px, target_height_px), Image.LANCZOS)
            
            temp_img_path = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            img.save(temp_img_path.name)
            temp_img_path.close()
            
            effective_w = paper_w - overlap
            effective_h = paper_h - overlap
            
            pages_with_image = self.app_data['pages_with_image']
            
            c = pdf_canvas.Canvas(temp_pdf_path, pagesize=page_size)
            
            for page_idx, (row, col) in enumerate(pages_with_image):
                page_num = page_idx + 1
                page_left_mm = col * effective_w
                page_top_mm = row * effective_h
                
                img_offset_x = self.app_data['img_x'] - page_left_mm
                img_offset_y = self.app_data['img_y'] - page_top_mm
                
                c.drawImage(temp_img_path.name,
                          img_offset_x * mm,
                          page_size[1] - img_offset_y * mm - actual_img_h_mm * mm,
                          width=actual_img_w_mm * mm,
                          height=actual_img_h_mm * mm)
                
                if self.app_data['show_page_numbers']:
                    c.setFillColorRGB(0.2, 0.2, 0.2)
                    c.setFont("Helvetica-Bold", 12)
                    c.drawString(10 * mm, page_size[1] - 10 * mm, str(page_num))
                
                c.showPage()
            
            c.save()
            
            # Limpiar temp image
            os.unlink(temp_img_path.name)

            # Programar limpieza del PDF temporal al cerrar la app
            atexit.register(lambda p=temp_pdf_path: os.unlink(p) if os.path.exists(p) else None)

            # Abrir PDF con diálogo de impresión de Windows
            os.startfile(temp_pdf_path, "print")

            self.dialog.destroy()
            messagebox.showinfo("Éxito", f"PDF generado y enviado al sistema de impresión de Windows\n\n"
                                        f"Nota: El archivo temporal se eliminará al cerrar la aplicación.")

        except ImportError:
            messagebox.showerror("Error", "Falta la librería 'reportlab'.\nInstálala con: pip install reportlab")
        except Exception as e:
            messagebox.showerror("Error", f"Error generando PDF:\n{str(e)}")
    
    def print_system_dialog(self):
        """Imprimir usando diálogo nativo de Windows (trabajo único)"""
        try:
            from reportlab.pdfgen import canvas as pdf_canvas
            from reportlab.lib.pagesizes import landscape
            from reportlab.lib.units import mm
            import win32api
            
            # Crear PDF temporal
            temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_pdf_path = temp_pdf.name
            temp_pdf.close()
            
            paper_w = self.app_data['paper_w_mm']
            paper_h = self.app_data['paper_h_mm']
            
            if self.app_data['orientation'] == 'horizontal':
                page_size = landscape((paper_w * mm, paper_h * mm))
            else:
                page_size = (paper_w * mm, paper_h * mm)
            
            overlap = self.app_data['overlap_mm']
            
            img = self.app_data['original_image'].copy()
            if self.app_data['rotation_angle'] != 0:
                img = img.rotate(-self.app_data['rotation_angle'], expand=True, resample=Image.BICUBIC)
            
            actual_img_w_mm = self.app_data['img_width']
            actual_img_h_mm = self.app_data['img_height']
            
            aspect_ratio = img.height / img.width
            dpi = 300
            target_width_px = int((actual_img_w_mm / 25.4) * dpi)
            target_height_px = int(target_width_px * aspect_ratio)
            
            img = img.resize((target_width_px, target_height_px), Image.LANCZOS)
            
            temp_img_path = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            img.save(temp_img_path.name)
            temp_img_path.close()
            
            effective_w = paper_w - overlap
            effective_h = paper_h - overlap
            
            pages_with_image = self.app_data['pages_with_image']
            
            c = pdf_canvas.Canvas(temp_pdf_path, pagesize=page_size)
            
            for page_idx, (row, col) in enumerate(pages_with_image):
                page_num = page_idx + 1
                page_left_mm = col * effective_w
                page_top_mm = row * effective_h
                
                img_offset_x = self.app_data['img_x'] - page_left_mm
                img_offset_y = self.app_data['img_y'] - page_top_mm
                
                c.drawImage(temp_img_path.name,
                          img_offset_x * mm,
                          page_size[1] - img_offset_y * mm - actual_img_h_mm * mm,
                          width=actual_img_w_mm * mm,
                          height=actual_img_h_mm * mm)
                
                if self.app_data['show_page_numbers']:
                    c.setFillColorRGB(0.2, 0.2, 0.2)
                    c.setFont("Helvetica-Bold", 12)
                    c.drawString(10 * mm, page_size[1] - 10 * mm, str(page_num))
                
                c.showPage()
            
            c.save()
            
            # Limpiar temp image
            os.unlink(temp_img_path.name)

            # Programar limpieza del PDF temporal al cerrar la app
            atexit.register(lambda p=temp_pdf_path: os.unlink(p) if os.path.exists(p) else None)

            # Usar ShellExecute con verbo "printto" para imprimir directamente
            win32api.ShellExecute(
                0,
                "print",
                temp_pdf_path,
                f'/d:"{self.selected_printer}"',
                ".",
                0
            )
            
            self.dialog.destroy()
            messagebox.showinfo("Éxito", f"Documento enviado al diálogo del sistema\n\n"
                                        f"Se abrirá la ventana de impresión de Windows.")
            
        except ImportError:
            messagebox.showerror("Error", "Falta la librería 'reportlab'.\nInstálala con: pip install reportlab")
        except Exception as e:
            messagebox.showerror("Error", f"Error enviando a sistema:\n{str(e)}")


def show_print_dialog(parent, app_data):
    """Función helper para mostrar el diálogo"""
    PrintDialog(parent, app_data)