"""
Sonidos del juego (pygame.mixer).

Pon tus archivos de audio en una carpeta llamada  sonidos/  junto a main.py
(también se buscan en  Sonidos/, sounds/, audio/  o junto a main.py).
Si un archivo no existe, el juego NO se cae: avisa una vez en la consola y sigue sin ese sonido.
No importan las mayúsculas, los acentos ni los espacios/guiones del nombre (reparación-robot = reparacion robot).
"""
import os
import unicodedata

import pygame

# ----------------------------------------------------------------------
#  NOMBRES DE LOS ARCHIVOS  (cámbialos aquí si tus archivos se llaman distinto)
# ----------------------------------------------------------------------
REPARAR = "reparación-robot.wav"   # en bucle mientras reparas al robot
COMPRA = "compra.wav"              # al comprar en la tienda
PASOS = "pasos.wav"                # en bucle mientras el personaje camina
TOMA_ITEM = "toma-items.wav"       # al recoger una pieza en la misión lunar
MENU = "Menu.wav"                  # en bucle en el menú
APARICION = "aparicion.wav"        # al llegar a la Luna o a Marte

# Volumen de cada sonido (0.0 a 1.0)
VOLUMEN = {REPARAR: 0.8, COMPRA: 0.9, PASOS: 0.5, TOMA_ITEM: 0.9, MENU: 0.5, APARICION: 0.9}

CARPETAS = ("sonidos", "Sonidos", "sounds", "audio", "")
EXTENSIONES = (".wav", ".ogg", ".mp3")
BASE = os.path.dirname(os.path.abspath(__file__))

_cache = {}   # nombre -> pygame.mixer.Sound o None si no existe
_loops = {}   # nombre -> Channel donde suena en bucle
_activo = None


def _mixer_listo():
    """Inicia el mixer una sola vez. Si no hay tarjeta de sonido, el juego sigue en silencio."""
    global _activo
    if _activo is None:
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.set_num_channels(16)
            _activo = True
        except pygame.error as e:
            print("Sin audio:", e)
            _activo = False
    return _activo


def _norm(s):
    s = unicodedata.normalize("NFD", os.path.splitext(s)[0])
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().replace(" ", "").replace("_", "").replace("-", "")


def _buscar(nombre):
    for carpeta in CARPETAS:
        d = os.path.join(BASE, carpeta)
        exacto = os.path.join(d, nombre)
        if os.path.isfile(exacto):
            return exacto
        try:
            for f in os.listdir(d):
                if f.lower().endswith(EXTENSIONES) and _norm(f) == _norm(nombre):
                    return os.path.join(d, f)
        except OSError:
            pass
    return None


def cargar(nombre):
    """Carga el sonido una sola vez (y lo guarda). Devuelve None si no se encuentra."""
    if not _mixer_listo():
        return None
    if nombre not in _cache:
        ruta = _buscar(nombre)
        snd = None
        if ruta is None:
            print("No se encontró el sonido", nombre, "(carpeta sonidos/)")
        else:
            try:
                snd = pygame.mixer.Sound(ruta)
                snd.set_volume(VOLUMEN.get(nombre, 1.0))
            except pygame.error as e:
                print("No se pudo cargar", ruta, "-", e)
        _cache[nombre] = snd
    return _cache[nombre]


def tocar(nombre):
    """Suena una sola vez."""
    snd = cargar(nombre)
    if snd:
        snd.play()


def loop(nombre):
    """Suena en bucle. Si ya está sonando no se reinicia, así que se puede llamar cada frame."""
    snd = cargar(nombre)
    if snd is None:
        return
    canal = _loops.get(nombre)
    if canal is not None and canal.get_busy() and canal.get_sound() is snd:
        return
    _loops[nombre] = snd.play(loops=-1)


def parar(nombre, fade_ms=150):
    """Corta un sonido en bucle con un pequeño fundido. Si no estaba sonando, no hace nada."""
    canal = _loops.pop(nombre, None)
    snd = _cache.get(nombre)
    if canal is not None and snd is not None:
        snd.fadeout(fade_ms)


def pasos(moviendo):
    """Pasos mientras el personaje se mueve; se cortan al detenerse."""
    if moviendo:
        loop(PASOS)
    else:
        parar(PASOS, 80)
