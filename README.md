# VA-11 Hall-A → 3DS (via Cinnamon)

Meta: correr VA-11 Hall-A: Cyberpunk Bartender Action en una 3DS homebrew, usando
los assets del juego que el usuario ya compró (copia física/digital de PS Vita,
backupeada). No se distribuye ni se sube a ningún lado el data file del juego ni
ningún asset — todo el procesamiento es local, para uso personal, igual que un
port de ScummVM/RPCS3/Citra que requiere que vos pongas tus propios archivos.

## Qué es "Cinnamon"

No es un motor de novela visual. Es una **reimplementación open source (MPL-2.0)
del runtime/runner de GameMaker: Studio, escrita en C, para 3DS y Wii U**
(proyecto [Project-Sunshine-Native/cinnamon](https://github.com/Project-Sunshine-Native/cinnamon),
fork de [Butterscotch](https://github.com/MrPowerGamerBR/Butterscotch)). GameMaker
compila los juegos a bytecode portable (no a código nativo, salvo que se use YYC),
así que cualquier runner compatible con esa versión de bytecode puede ejecutar el
juego en otra plataforma — es la misma idea que Droidtale (Undertale en Android) o
los ports de Undertale/Deltarune a Wii U/3DS que ya tiene el proyecto.

**VA-11 Hall-A está hecho en GameMaker: Studio** (confirmado por la propia
[showcase page de GameMaker](https://gamemaker.io/en/showcase/va-11-hall-a-cyberpunk-bartender-action)
y por discusiones de los devs de Sukeban Games — el prototipo/prólogo era Ren'Py,
pero el juego final se reescribió en GameMaker). Eso es lo que hace viable, en
principio, este proyecto.

## El riesgo real: bytecode VM vs. YYC

Cinnamon **solo soporta bytecode versión 16 y 17, generado por el runner VM
normal de GameMaker**. Si el juego fue compilado con **YYC** (YoYo Compiler, que
genera código nativo ARM/x86 en vez de bytecode) o con el nuevo formato **GMRT**,
Cinnamon no puede ejecutarlo — no hay bytecode que interpretar.

- La versión PC/Mac/Linux (2016) de VA-11 Hall-A casi seguro usa el runner VM
  estándar (es lo normal para releases de escritorio).
- El port de **PS Vita fue hecho por el estudio Wolfgame**. No hay información
  pública sobre si usaron YYC (habitual en ports de consola por rendimiento/
  certificación) o el runner VM. **Esto no se puede saber sin mirar el archivo
  real** — por eso el primer paso técnico es sacar el data file de tu backup y
  correr el scanner de este repo sobre él.

Si resulta que la build de Vita es YYC, la Vita queda descartada como fuente de
assets ejecutables (igual serviría como fuente de sprites/audio/texto, pero no
del código del juego) y haría falta la build de PC/Mac/Linux en su lugar.

## Actualización: la Vita quedó descartada como fuente (por ahora)

Se probó con el `.pkg` real del usuario (300MB, PCSB01166 EUR). Resultó ser un
pkg ya parcheado — `pkg2zip` lo extrajo sin necesitar zRIF. Adentro apareció
`games/game.win` (21MB, el tamaño esperado), pero **no empieza con la firma
`FORM`**: el histograma de bytes es plano (alta entropía) y se probaron
sistemáticamente períodos de XOR de clave repetida de 1 a 256 bytes contra el
plaintext conocido (`FORM`+largo+`GEN8`) sin que ninguno diera un largo de
chunk GEN8 plausible. Es cifrado real, no una ofuscación trivial — no vale la
pena seguir adivinando a ciegas.

Investigando la escena de "GameMaker en Vita/3DS" (el proyecto
[yoyoloader_vita](https://github.com/Rinnegatamante/yoyoloader_vita) de
Rinnegatamante y su [guía oficial de asset-swap](https://gist.github.com/CatoTheYounger97/fa47e7eef92f772e4004d4dac22f9bdb))
se confirma que esto no es mala suerte nuestra: **todo el flujo de trabajo
establecido en esa comunidad parte del `data.win` de PC/Steam, nunca de
exports nativos de consola** (Vita/PS4/Switch) — su propia guía marca
"PC/Console Bytecode" como algo que necesita este workaround específico, y no
hay ningún decryptor documentado para exports nativos de consola en ningún
lado. Es la señal de que perseguir el cifrado de la Vita no tiene sentido
cuando el camino real y probado es la copia de PC.

**Por eso ahora hace falta la versión de PC** (Steam/GOG/itch, cualquiera) —
sortea el cifrado por completo y de paso resuelve la duda de YYC-vs-VM (los
builds de escritorio de GMS 1.4 son casi siempre VM). El `pkg2zip` compilado
(con un fix al Makefile para arm64 — el original asume x86 y pasa `-maes
-mssse3`, que clang rechaza en Apple Silicon; el fallback en C portable ya
existe en el propio código así que alcanzaba con no compilar los archivos
`*_x86.c` ahí) queda disponible en `pkg2zip/` por si hace falta de nuevo.

## Actualización: datos limpios conseguidos, pero es bytecode v15

Se consiguió `game.unx` (211MB) desde un instalador offline de GOG para Linux
(`.sh` tipo makeself+mojosetup, extraído sin correr el instalador — es un
script con un `data.zip` pegado al final; el offset real del zip se encontró
buscando la firma `PK\x03\x04`, no confiando en el valor `OLDSKIP` que reporta
`--dumpconf`, que no coincidía). El scanner lo confirma como el archivo real:

```
Nombre mostrado: 'VA-11 Hall-A: Cyberpunk Bartender Action'
Bytecode version: 15
Veredicto: Bytecode v15 no soportado por Cinnamon (solo soporta v16 y v17).
```

Buena noticia: **no está cifrado y no es YYC** (chunk `CODE` presente, 1.2MB)
— el miedo original quedó resuelto del todo. La mala: es una versión de
bytecode más vieja que las que Cinnamon soporta. Y esto **no se arregla
consiguiendo otra plataforma** — la versión de bytecode depende de qué
build de GameMaker Studio usó Sukeban Games en 2016, no de para qué
plataforma se exportó, así que Windows/Mac/Android de este mismo juego
casi seguro también son v15.

Revisando `cinnamon/src/bytecode_versions.h`: no es un límite blando/no
probado, es arquitectónico — el dispatch de opcodes de la VM en `vm.c` está
construido enteramente sobre flags de compilación `ENABLE_BC16`/`ENABLE_BC17`,
sin ningún punto de anclaje para v15. Pero el proyecto padre de Cinnamon,
[Butterscotch](https://github.com/MrPowerGamerBR/Butterscotch) (AGPL-3.0,
activo, ~1700 commits), soporta bytecode 8–17 y ya apunta a PS Vita/PS2/PS3 —
casi seguro ya tiene la lógica de opcodes de v15 resuelta. Osea que esto es
más "portar lógica ya existente de Butterscotch a Cinnamon" que "reversear
un formato desconocido de cero" — real trabajo de desarrollo, pero acotado y
con una implementación de referencia a mano.

El archivo bueno para cuando esto se destrabe:
`extracted/gog_linux/data/noarch/game/assets/game.unx`.

## Actualización: hay un .3dsx real, pero crashea al arrancar en el emulador

En la práctica, el problema de bytecode v15 de arriba resultó ser menos grave
de lo que parecía: `vm.c` solo distingue "v17 o más" de "todo lo anterior"
(`IS_BC16_OR_BELOW` vs `IS_BC17_OR_HIGHER`), nada separa v15 de v16
específicamente. Con devkitPro instalado (`/opt/devkitpro`, vía el `.pkg`
oficial + `sudo dkp-pacman -S 3ds-dev`, más `brew install cmake` porque
devkitPro no trae un `cmake` genérico) se pudo:

1. Renombrar `game.unx` a `data.win` (el preprocesador busca ese nombre
   literal por el string, cosmético, mismo contenido).
2. Correr `n3ds-preprocess` sobre el archivo real → **88 sonidos empaquetados
   bien** (872MB) una vez que se sacaron unos `.ogg` de la Vita que resultaron
   ser *también* falsos (no arrancan con la firma `OggS`, probablemente
   Sony los pasa a ATRAC9) — estaban tapando el audio embebido real que sí
   funciona. Quedan 32 pistas de música que este `.zip` de GOG en particular
   no trae sueltas (huecos reales, pero no bloquean nada, solo quedan mudas).
3. Compilar Cinnamon para `n3ds` de verdad (con
   `-DCMAKE_TOOLCHAIN_FILE="$DEVKITPRO/cmake/3DS.cmake"`, no con el wrapper
   `arm-none-eabi-cmake` que apunta al toolchain equivocado) →
   **`cinnamon/build/n3ds/cinnamon.3dsx`, 2.1GB, compila limpio.**

Probado en [Azahar](https://github.com/azahar-emu/azahar) (el fork
mantenido de Citra): carga de verdad (no lo rechaza, se ve en
`~/Library/Application Support/Azahar/log/azahar_log.txt` que arranca
Vulkan, carga shaders, arranca audio, hace llamadas de servicio HLE), pero
**se cierra solo, siempre en el mismo punto exacto**: justo después de dos
avisos `unknown/unimplemented function 'ConfigureNew3DSCPU'`. Sin reporte de
crash de macOS → es una salida controlada, no un segfault. Probar sin "New
3DS mode" en la config de Azahar no cambió nada (mismo log, mismo cierre),
así que esa función puntual probablemente no es la causa real, solo está
cerca.

**Para retomar:** probar renderer OpenGL en vez de Vulkan en Azahar (el log
está lleno de warnings de MoltenVK tipo "blacklisted"/"unsupported" — muy
sospechoso), compilar Cinnamon en modo Debug para un error real en vez de un
exit silencioso, o directamente probarlo en una 3DS real si hay una modeada
a mano (Azahar/Citra tienen sus propias rarezas de compatibilidad aparte de
si el port en sí está bien). El `.3dsx` en sí es el entregable correcto y
completo del pipeline — Cinnamon no genera `.cia`, así que esto ya es
"lo que se puede correr en 3DS" tal como lo distribuye el propio proyecto.

## Estado de este repo

- `cinnamon/` — clone de Cinnamon, rama **`UNDERTALE-3DS`** (no `main`): `main`
  es el motor pelado sin la herramienta de preprocesado; `UNDERTALE-3DS` es la
  rama de un port real y completo ("UNDERTALE: 3DS Edition") que sí incluye
  `tools/n3ds-preprocess`, la herramienta que convierte un `data.win` a los
  formatos que Cinnamon usa en 3DS (texturas ETC1A4/RGBA5551 vía `tex3ds`, audio
  a BCWAV). Es la base más probada para partir a armar un nuevo port.
- `tools/scan_gm_data.py` — script propio (sin dependencias, solo stdlib) que
  busca archivos con firma `FORM` (el contenedor de GameMaker), lista sus chunks,
  y da un veredicto de compatibilidad con Cinnamon. La lectura de bytes (offset
  del `bytecodeVersion` dentro de `GEN8`, detección de YYC por chunk `CODE`
  vacío, offsets de `name`/`displayName`) está tomada directamente de
  `cinnamon/src/data_win.c`, no de documentación de terceros — y quedó probada
  contra archivos sintéticos que reproducen esa estructura byte a byte
  (caso compatible, caso YYC, y caso de firma embebida dentro de un binario más
  grande tipo `eboot.bin`).
- No se instaló todavía devkitPro (hace falta para compilar Cinnamon para 3DS y
  para `tex3ds`). No hace falta hasta que confirmemos que el data file es
  compatible.
- Todavía no tenemos el data file de VA-11 Hall-A en ningún formato — el
  siguiente paso depende de vos.

## Plan / pipeline completo

1. **Sacar el data file de tu backup de Vita.**
   - Si tu backup es un `.pkg` + `zRIF`/`work.bin` (formato típico de backup
     legítimo): convertilo a `.vpk` con [`pkg2zip`](https://github.com/mmozeiko/pkg2zip)
     (open source, es el estándar de la escena Vita para esto).
   - Un `.vpk` es un `.zip` normal — descomprimilo con lo que quieras
     (`unzip juego.vpk -d extracted/`).
   - Puede que el data file no se llame `data.win` (en exports no-Windows de
     GameMaker suele ser `game.unx`, `game.ios`, o directamente estar embebido
     dentro de `eboot.bin`) — por eso el scanner busca la firma de bytes, no el
     nombre del archivo.
2. **Correr el scanner** sobre la carpeta descomprimida:
   ```bash
   python3 tools/scan_gm_data.py extracted/
   ```
   Si no encuentra nada como archivo independiente, probar el modo profundo
   (busca la firma `FORM` embebida dentro de binarios grandes como `eboot.bin`):
   ```bash
   python3 tools/scan_gm_data.py extracted/ --deep
   ```
3. **Leer el veredicto.** Si dice `COMPATIBLE (probable): bytecode v16` o `v17`
   con `CODE presente` → seguimos. Si dice `YYC / código nativo detectado` →
   la build de Vita no sirve como fuente de bytecode, hay que conseguir la
   build de PC/Mac/Linux.
4. **Instalar devkitPro (entorno 3DS)** y compilar `tools/n3ds-preprocess`
   dentro de `cinnamon/` (instrucciones en `cinnamon/README.md`).
5. **Convertir los assets:**
   ```bash
   n3ds-preprocess <data-file-encontrado> resources/3ds/romfs
   ```
6. **Compilar Cinnamon para 3DS:**
   ```bash
   arm-none-eabi-cmake -S . -B build/n3ds -DPLATFORM=n3ds -DCMAKE_BUILD_TYPE=Release
   cmake --build build/n3ds
   ```
   Esto genera `cinnamon.3dsx`.
7. **Probar.** En una 3DS con Luma3DS/homebrew launcher, o en el emulador
   Citra/Azahar si no tenés la consola modeada a mano. Copiar `cinnamon.3dsx`
   más la carpeta de assets generada a `sdmc:/3ds/cinnamon`.

## Qué falta que hagas vos

Pasar el backup de Vita (o decirme la ruta/carpeta donde lo tenés en esta Mac,
o el formato exacto: `.vpk` ya armado, o `.pkg`+`zRIF`) para correr el scanner y
saber en qué punto del plan estamos parados realmente.
