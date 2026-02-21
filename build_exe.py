import PyInstaller.__main__
import os

PyInstaller.__main__.run([
    'poster_printer.py',
    '--name=PosterPrinter',
    '--onefile',
    '--windowed',
    '--icon=NONE',
    '--add-data=requirements.txt;.',
    '--hidden-import=PIL._tkinter_finder',
    '--hidden-import=win32timezone',
    '--clean',
    '--noconfirm',
])

print("\n✓ Ejecutable creado en la carpeta 'dist'")
print("  Archivo: dist/PosterPrinter.exe")
