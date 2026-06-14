# ⚽ Clasificación Histórica

App interactiva en Streamlit para explorar la clasificación histórica de la
liga (temporadas T6–T18): clasificación agregada por rango de temporadas,
récords y curiosidades, evolución de un equipo y comparador entre dos equipos.

Los equipos se identifican internamente por su **ID de StrikerManager**
(extraído del enlace de cada equipo), no por el nombre, así que si un club se
renombra en el futuro, su historial sigue contando correctamente.

## Estructura del proyecto

```
futbol_app/
├── app.py                  # App de Streamlit
├── requirements.txt        # Dependencias
├── iniciar_app.bat          # Doble clic para instalar y arrancar en Windows
└── data/
    ├── temporadas.csv        # Clasificación de cada temporada (T6-T18), formato largo
    └── equipos_meta.csv       # ID, nombre actual, palmarés e historial de cada equipo
```

## Ejecutar en Windows (forma más fácil)

1. Instala Python si no lo tienes: https://www.python.org/downloads/
   (en el instalador, marca la casilla **"Add Python to PATH"**).
2. Descomprime esta carpeta donde quieras.
3. Haz doble clic en **`iniciar_app.bat`**.
   - La primera vez instalará las dependencias (tarda un poco).
   - Después abrirá automáticamente el navegador con la app en
     `http://localhost:8501`.
4. Para volver a abrirla otro día, vuelve a hacer doble clic en
   `iniciar_app.bat` (ya no tendrá que reinstalar nada).
5. Para cerrarla, cierra la ventana negra (la consola) que se abrió.

## Ejecutar en Windows manualmente (PowerShell / CMD)

Si prefieres no usar el `.bat`, desde dentro de la carpeta `futbol_app`:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

> Si `python` tampoco se reconoce, vuelve a instalar Python marcando
> "Add Python to PATH", o usa `py` en lugar de `python`:
> ```powershell
> py -m pip install -r requirements.txt
> py -m streamlit run app.py
> ```

## Ejecutar en Mac / Linux

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Actualizar los datos (nueva temporada)

1. Añade las filas correspondientes a `data/temporadas.csv` con las columnas:
   `temporada,pos,equipo_id,equipo_nombre,PJ,PG,PE,PP,GF,GC,DG,Pnt`
   - `equipo_id` es el número que aparece en el enlace
     `https://eu.strikermanager.com/equipo.php?id=XXX`.
   - `equipo_nombre` es el nombre del equipo **en esa temporada** (si cambió
     de nombre, pon el nuevo nombre; el ID es lo que lo vincula con el
     historial anterior).
2. Si es un equipo nuevo (ID que no existe en `equipos_meta.csv`), añade una
   fila en `data/equipos_meta.csv` con sus datos básicos
   (`equipo_id,nombre_actual,link,nombre_historico,primeros,segundos,playoff,notas,podios`).
3. Guarda y vuelve a abrir la app (o pulsa "Rerun" en Streamlit).

## Desplegar gratis en Streamlit Community Cloud

1. Crea un repositorio en GitHub y sube esta carpeta (`app.py`,
   `requirements.txt`, `data/`).
   ```bash
   cd futbol_app
   git init
   git add .
   git commit -m "Clasificación histórica - app inicial"
   git branch -M main
   git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
   git push -u origin main
   ```
2. Ve a https://share.streamlit.io y entra con tu cuenta de GitHub.
3. "New app" → selecciona el repo, la rama `main` y el archivo `app.py`.
4. Deploy. En 1-2 minutos tendrás una URL pública tipo
   `https://tu-app.streamlit.app` para compartir con quien quieras.

### Alternativa: Hugging Face Spaces
Si prefieres no usar GitHub o quieres más control de recursos, puedes crear
un Space de tipo "Streamlit" en https://huggingface.co/spaces y subir los
mismos archivos directamente desde la web.
