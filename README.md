# Simulador Espacial - Construye tu Cohete

Juego de misiones espaciales hecho en Python + pygame (proyecto Nasa-Space-App).
Compras piezas, armas tu nave dentro de un presupuesto, despegas y completas misiones en la **Luna** y en **Marte**.
Cada decisión cuenta: el peso, la energía, la antena, el instrumento y el dinero cambian tu éxito y tu puntuación.

---

## Jugar con el .exe (Windows)

1. Descarga el archivo ZIP del juego y **descomprímelo completo** (no lo abras desde dentro del ZIP).
2. Abre la carpeta `SimuladorEspacial` y haz doble clic en **`SimuladorEspacial.exe`**.
3. No necesitas instalar Python. El juego se abre a pantalla completa.

> **Aviso de Windows:** si aparece "Windows protegió tu PC", pulsa **Más información** y luego **Ejecutar de todos modos**.
> Sale porque el programa no está firmado; no es un virus.

**Mantén el .exe dentro de su carpeta**: necesita los archivos que están junto a él.

Tu partida se guarda automáticamente en `%APPDATA%\SimuladorEspacial\partida.json`
(pega esa ruta en el Explorador de archivos). Si quieres empezar de cero, elige **Nuevo juego** o borra ese archivo.

---

## Controles

| Tecla | Qué hace |
|---|---|
| **W A S D** o **flechas** | Caminar |
| **E** | Interactuar (abrir paneles, recoger piezas, desplegar el dron, subir a la nave) |
| **Mantener E** | Reparar el robot lunar (5 segundos) |
| **H** | Abrir el glosario (en la estación y sus paneles) |
| **ESPACIO / ENTER / clic** | Saltar animaciones (despegue y viaje) |
| **ESC** | Cerrar la ventana abierta / volver al menú (se guarda tu avance) |
| **F1** (mantener) | Mostrar las zonas de colisión (para depurar) |
| **Mouse** | Pulsar botones y elegir piezas |

Para salir del juego: botón **Salir** del menú, o **ESC** en el menú principal (también funciona **Alt + F4**).

---

## Cómo se juega

1. **MISIONES (computadora):** elige y acepta una misión. Primero la Luna y, al completarla, se desbloquea Marte.
2. **TIENDA:** compra las piezas que necesitas con tu presupuesto (puedes vender las que no uses).
3. **HANGAR (la nave):** equipa las piezas. El botón **Sugerir** pone las recomendadas que ya tienes.
   Con **¿Qué pasa si…?** pruebas cambiar una pieza y ves cómo cambiarían el peso, la energía y los puntos antes de decidir.
4. **Revisar vuelo:** la lista de revisión debe estar en verde.
   Si despegas con errores, el cohete **falla en pleno vuelo** y pierdes fondos.
5. **Despegue y viaje:** disfruta la animación de lanzamiento.
6. **En la Luna:** recoge las 3 piezas y repara el robot (mantén **E**).
7. **En Marte:** acércate al dron y pulsa **E**. Se despliega, explora la zona hasta llenar la barra y regresa.
8. **Vuelve a la nave** y pulsa **E** para regresar a la Tierra.
9. Al terminar recibes la **recompensa**, un **reporte científico** con tus decisiones y su puntuación, y se desbloquea la siguiente misión.
   Al completar todas las misiones se muestra el final.

---

## Opciones (menú > Opciones)

- **Zoom de cámara:** qué tan cerca ves el mapa.
- **Velocidad del jugador:** qué tan rápido camina el astronauta.
- **Tamaño del personaje:** barra deslizante para hacerlo más grande o más pequeño.

Se guardan solas.

---

## Ejecutar desde el código (para desarrolladores)

Requiere Python 3.9 o superior.

    pip install -r requirements.txt
    python main.py

## Crear el .exe

En Windows, con todo el proyecto en la misma carpeta (`main.py`, `images`, `sonidos`, `Fondo`, ...):

    crear_exe.bat

Genera `dist\SimuladorEspacial\SimuladorEspacial.exe`. Para compartirlo, comprime en ZIP **toda** la carpeta `dist\SimuladorEspacial`.
Si el .exe se cierra solo al abrirlo, quita `--windowed` en `crear_exe.bat`, vuelve a compilar y mira el error en la consola.

---

## Estructura del proyecto

    main.py          Juego principal: estación, paneles, tienda, misiones
    despegue.py      Animación de despegue (y de fallo del cohete)
    dron.py          Dron y expedición en Marte
    final.py         Final cinematográfico
    sonido.py        Sonidos y música (carpeta sonidos/)
    player.py        Astronauta
    map.py           Mapas con colisiones
    sprite.py        Sprites
    input.py         Teclas presionadas
    Fondo/           Video animado del menú
    images/          Imágenes del juego
    sonidos/         Audio (si falta un archivo, el juego sigue sin ese sonido)
    crear_exe.bat    Script para crear el .exe
