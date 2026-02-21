import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import random
import os
import sys
import json

class AboutDialog:
    def __init__(self, parent, version_data=None):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Acerca de Poster Printer")
        self.dialog.geometry("450x590")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Centrar ventana
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (590 // 2)
        self.dialog.geometry(f"450x590+{x}+{y}")

        # Escape para cerrar
        self.dialog.bind("<Escape>", lambda e: self.dialog.destroy())
        
        # Variables de estado
        self.click_count = 0
        self.ctrl_click_count = 0
        self.easter_egg_active = False
        self.animating = False
        
        # Datos de versión (pasados desde main)
        self.version_data = version_data or {
            "version": "2.12.6",
            "date": "Noviembre 2025",
            "description": "Print Dialog optimizado"
        }
        
        # Cargar frases románticas
        self.romantic_phrases = self.load_romantic_phrases()
        
        # Cargar imágenes
        self.load_images()
        
        # Crear interfaz
        self.create_ui()
    
    def load_romantic_phrases(self):
        """Cargar frases románticas desde archivo"""
        try:
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            phrases_path = os.path.join(base_path, "resources", "data", "romantic_phrases.txt")
            
            if os.path.exists(phrases_path):
                with open(phrases_path, 'r', encoding='utf-8') as f:
                    phrases = [line.strip() for line in f.readlines() if line.strip()]
                    return phrases
            else:
                print(f"Phrases file not found: {phrases_path}")
                return ["Para mi Aries: esos brazos tuyos fueron hechos para rodearme."]
        except Exception as e:
            print(f"Error loading phrases: {e}")
            return ["Para mi Aries: esos brazos tuyos fueron hechos para rodearme."]
    
    def load_images(self):
        """Cargar todas las imágenes necesarias"""
        try:
            # Obtener directorio base
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            # Icono principal - resize fijo 128x128
            icon_path = os.path.join(base_path, "resources", "icons", "icon.png")
            if os.path.exists(icon_path):
                self.icon_img_pil = Image.open(icon_path).convert('RGBA')
                icon_resized = self.icon_img_pil.resize((128, 128), Image.LANCZOS)
                self.icon_photo = ImageTk.PhotoImage(icon_resized)
            else:
                print(f"Icon not found at: {icon_path}")
                self.icon_photo = None
                self.icon_img_pil = None
            
            # Dragones - resize fijo 128x128
            self.dragon_photos = []
            dragon_files = ["dragon_dead.png", "dragon_hug.png", "dragon_head.png", 
                           "dragon_s.png", "dragon_hug2.png"]
            
            for dragon_file in dragon_files:
                dragon_path = os.path.join(base_path, "resources", "easter_egg", dragon_file)
                if os.path.exists(dragon_path):
                    dragon_img = Image.open(dragon_path).convert('RGBA')
                    dragon_img = dragon_img.resize((128, 128), Image.LANCZOS)
                    self.dragon_photos.append(ImageTk.PhotoImage(dragon_img))
                else:
                    print(f"Dragon not found: {dragon_path}")
            
            print(f"Loaded {len(self.dragon_photos)} dragon images")
            
        except Exception as e:
            print(f"Error loading images: {e}")
            import traceback
            traceback.print_exc()
            self.icon_photo = None
            self.icon_img_pil = None
            self.dragon_photos = []
    
    def create_ui(self):
        """Crear la interfaz del diálogo - Layout vertical ordenado"""
        # Contenedor principal
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # === SECCIÓN 1: ICONO (siempre arriba, clickeable) ===
        icon_container = ttk.Frame(main_frame)
        icon_container.pack(pady=(10, 15))
        
        if self.icon_photo:
            self.icon_label = tk.Label(icon_container, image=self.icon_photo, cursor="hand2",
                                      borderwidth=0, highlightthickness=0)
        else:
            self.icon_label = tk.Label(icon_container, text="🖼️", font=('Arial', 64), cursor="hand2",
                                      borderwidth=0, highlightthickness=0)
        
        self.icon_label.pack()
        self.icon_label.bind("<Button-1>", self.on_icon_click)
        
        # === SECCIÓN 2: TÍTULO ===
        app_name = ttk.Label(main_frame, text="Poster Printer", 
                            font=('Aptos', 16, 'bold'), justify='center')
        app_name.pack(pady=(0, 5))
        
        # === SECCIÓN 3: VERSIÓN ===
        self.version_label = ttk.Label(main_frame, text=f"Versión {self.version_data['version']}", 
                                      font=('Aptos', 10), justify='center')
        self.version_label.pack(pady=2)
        
        # === SECCIÓN 4: FECHA ===
        self.date_label = ttk.Label(main_frame, text=self.version_data['date'], 
                                   font=('Aptos', 9), foreground='gray', justify='center')
        self.date_label.pack(pady=2)
        
        # === SECCIÓN 5: INDICADOR DE PROGRESO (easter egg) ===
        self.progress_label = ttk.Label(main_frame, text="", 
                                       font=('Aptos', 7), foreground='#ccc', justify='center')
        self.progress_label.pack(pady=2)
        
        # === SECCIÓN 6: SEPARADOR ===
        ttk.Separator(main_frame, orient='horizontal').pack(fill='x', pady=15)
        
        # === SECCIÓN 7: CRÉDITOS ===
        self.credits_label = ttk.Label(main_frame, 
                                      text="Dirigido por neindev8\npara asistencia profesional",
                                      font=('Aptos', 9), foreground='#555',
                                      justify='center')
        self.credits_label.pack(pady=10)
        
        # === SECCIÓN 8: ESPACIO FLEXIBLE ===
        spacer = ttk.Frame(main_frame)
        spacer.pack(fill=tk.BOTH, expand=True)
        
        # === SECCIÓN 9: BOTÓN CERRAR ===
        close_btn = ttk.Button(main_frame, text="Cerrar", 
                              command=self.dialog.destroy, width=15)
        close_btn.pack(pady=10)
    
    def on_icon_click(self, event):
        """Manejar clicks en el icono"""
        # Si el easter egg ya está activo, cualquier click cambia dragón/frase
        if self.easter_egg_active:
            self.change_easter_egg()
            return
        
        # Detectar si se presionó Ctrl
        if event.state & 0x0004:  # Ctrl presionado
            self.ctrl_click_count += 1
            
            # Mostrar progreso discreto
            if self.ctrl_click_count < 8:
                dots = '•' * self.ctrl_click_count
                self.progress_label.config(text=dots)
            
            if self.ctrl_click_count >= 8:
                # Primera activación del easter egg
                self.easter_egg_active = True
                self.progress_label.config(text="")  # Limpiar
                self.activate_easter_egg()
        else:
            # Click normal: hacer animación divertida
            if not self.animating:
                self.click_count += 1
                self.play_random_animation()
    
    def play_random_animation(self):
        """Reproducir una animación random del icono"""
        if self.animating:
            return
        
        animations = [
            self.anim_blink,
            self.anim_rotate,
            self.anim_bounce,
            self.anim_scale,
            self.anim_shake,
            self.anim_pingpong,  # NUEVA animación estilo WinRAR
        ]
        
        random_anim = random.choice(animations)
        random_anim()
    
    def anim_blink(self):
        """Animación: Parpadear"""
        self.animating = True
        steps = 6
        
        def blink_step(step=0, visible=True):
            if step < steps:
                if visible:
                    self.icon_label.config(image='')
                else:
                    if self.icon_photo:
                        self.icon_label.config(image=self.icon_photo)
                    else:
                        self.icon_label.config(text="🖼️")
                
                self.dialog.after(100, lambda: blink_step(step + 1, not visible))
            else:
                # Restaurar imagen original
                if self.icon_photo:
                    self.icon_label.config(image=self.icon_photo)
                else:
                    self.icon_label.config(text="🖼️")
                self.animating = False
        
        blink_step()
    
    def anim_rotate(self):
        """Animación: Rotar 360°"""
        if not self.icon_photo or not self.icon_img_pil:
            self.anim_blink()
            return
        
        self.animating = True
        steps = 12
        
        def rotate_step(step=0):
            if step < steps:
                angle = (step * 30) % 360
                rotated = self.icon_img_pil.resize((128, 128), Image.LANCZOS).rotate(
                    angle, expand=False, resample=Image.BICUBIC)
                photo = ImageTk.PhotoImage(rotated)
                self.icon_label.config(image=photo)
                self.icon_label.image = photo
                self.dialog.after(50, lambda: rotate_step(step + 1))
            else:
                self.icon_label.config(image=self.icon_photo)
                self.icon_label.image = self.icon_photo
                self.animating = False
        
        rotate_step()
    
    def anim_bounce(self):
        """Animación: Saltar verticalmente"""
        self.animating = True
        
        # Guardar posición original
        self.icon_label.pack_forget()
        icon_container = self.icon_label.master
        
        # Frame temporal para animación con place
        temp_frame = tk.Frame(icon_container)
        temp_frame.pack()
        
        temp_label = tk.Label(temp_frame, image=self.icon_photo if self.icon_photo else None,
                             text="" if self.icon_photo else "🖼️",
                             font=('Arial', 64) if not self.icon_photo else None,
                             borderwidth=0, highlightthickness=0)
        temp_label.pack()
        
        def bounce_step(step=0):
            if step < 10:
                offset = int(30 * abs((step - 5) / 5))
                temp_label.place(y=-offset, x=0)
                self.dialog.after(50, lambda: bounce_step(step + 1))
            else:
                temp_frame.destroy()
                self.icon_label.pack()
                self.animating = False
        
        bounce_step()
    
    def anim_scale(self):
        """Animación: Escalar (zoom in/out)"""
        if not self.icon_photo or not self.icon_img_pil:
            self.anim_blink()
            return
        
        self.animating = True
        
        def scale_step(step=0):
            if step < 10:
                scale = 1.0 + (0.4 * abs((step - 5) / 5))
                new_size = int(128 * scale)
                scaled = self.icon_img_pil.resize((new_size, new_size), Image.LANCZOS)
                photo = ImageTk.PhotoImage(scaled)
                self.icon_label.config(image=photo)
                self.icon_label.image = photo
                self.dialog.after(50, lambda: scale_step(step + 1))
            else:
                self.icon_label.config(image=self.icon_photo)
                self.icon_label.image = self.icon_photo
                self.animating = False
        
        scale_step()
    
    def anim_shake(self):
        """Animación: Temblar horizontalmente"""
        self.animating = True
        
        # Guardar posición original
        self.icon_label.pack_forget()
        icon_container = self.icon_label.master
        
        # Frame temporal para animación
        temp_frame = tk.Frame(icon_container)
        temp_frame.pack()
        
        temp_label = tk.Label(temp_frame, image=self.icon_photo if self.icon_photo else None,
                             text="" if self.icon_photo else "🖼️",
                             font=('Arial', 64) if not self.icon_photo else None,
                             borderwidth=0, highlightthickness=0)
        temp_label.pack()
        
        def shake_step(step=0):
            if step < 12:
                offset = 10 if step % 2 == 0 else -10
                temp_label.place(x=offset, y=0)
                self.dialog.after(30, lambda: shake_step(step + 1))
            else:
                temp_frame.destroy()
                self.icon_label.pack()
                self.animating = False
        
        shake_step()
    
    def anim_pingpong(self):
        """Animación: Ping-pong lateral (estilo WinRAR) - NUEVA"""
        self.animating = True
        
        # Guardar posición original
        self.icon_label.pack_forget()
        icon_container = self.icon_label.master
        
        # Frame temporal para animación
        temp_frame = tk.Frame(icon_container, width=128, height=128)
        temp_frame.pack()
        temp_frame.pack_propagate(False)
        
        temp_label = tk.Label(temp_frame, image=self.icon_photo if self.icon_photo else None,
                             text="" if self.icon_photo else "🖼️",
                             font=('Arial', 64) if not self.icon_photo else None,
                             borderwidth=0, highlightthickness=0)
        
        # Calcular rango de movimiento (ancho del frame - ancho del icono)
        max_offset = 100
        
        def pingpong_step(step=0, direction=1):
            if step < 20:
                # Movimiento suave de ida y vuelta
                if step < 10:
                    # Ida (0 → max_offset)
                    offset = int((step / 10) * max_offset)
                else:
                    # Vuelta (max_offset → 0)
                    offset = int(((20 - step) / 10) * max_offset)
                
                temp_label.place(x=offset, y=0)
                self.dialog.after(40, lambda: pingpong_step(step + 1, direction))
            else:
                temp_frame.destroy()
                self.icon_label.pack()
                self.animating = False
        
        pingpong_step()
    
    def change_easter_egg(self):
        """Cambiar dragón y frase (para clicks después del 8vo)"""
        # Cambiar icono a un dragón random
        if self.dragon_photos:
            random_dragon = random.choice(self.dragon_photos)
            self.icon_label.config(image=random_dragon)
            self.icon_label.image = random_dragon
        
        # Cambiar a nueva frase romántica en VERDE BOLD (#2e7d32)
        if self.romantic_phrases:
            random_phrase = random.choice(self.romantic_phrases)
            self.date_label.config(text=random_phrase,
                                  font=('Aptos', 9, 'bold'),
                                  foreground='#2e7d32',
                                  wraplength=350)
    
    def activate_easter_egg(self):
        """Activar el easter egg"""
        self.easter_egg_active = True
        
        # Cambiar icono a un dragón random
        if self.dragon_photos:
            random_dragon = random.choice(self.dragon_photos)
            self.icon_label.config(image=random_dragon)
            self.icon_label.image = random_dragon  # Mantener referencia
        
        # Cambiar versión a dedicatoria en VERDE BOLD (#2e7d32)
        self.version_label.config(text="Dedicado a Drakercool\n(MeikerDrag)",
                                 font=('Aptos', 11, 'bold'),
                                 foreground='#2e7d32')
        
        # Cambiar fecha a frase romántica en VERDE BOLD (#2e7d32)
        if self.romantic_phrases:
            random_phrase = random.choice(self.romantic_phrases)
            self.date_label.config(text=random_phrase,
                                  font=('Aptos', 9, 'bold'),
                                  foreground='#2e7d32',
                                  wraplength=350,
                                  justify='center')
        
        # Ocultar créditos
        self.credits_label.pack_forget()


def show_about_dialog(parent, version_data=None):
    """Función helper para mostrar el diálogo"""
    AboutDialog(parent, version_data)