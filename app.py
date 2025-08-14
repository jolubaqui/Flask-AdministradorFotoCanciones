# importar flask
from flask import Flask, render_template, request, redirect, url_for, flash, g # Importar 'g'
import sqlite3
import os
from werkzeug.utils import secure_filename
import cloudinary
import cloudinary.uploader
import cloudinary.api
from flask import Flask, jsonify

# Define la ruta base del proyecto
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# ¡IMPORTANTE! Las fotos ahora se servirán como estáticas. Es buena práctica que estén dentro de 'static'
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'fotos_canciones')
DATABASE = os.path.join(BASE_DIR, 'instance', 'database.db')


# Asegúrate que las carpetas existan
os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configuración de Cloudinary
cloudinary.config(
    cloud_name = "dwcomv0hv", 
    api_key = "646295341746146",  
    api_secret = "0oid-hmmji7Hg8dMG6h-inbKsAw"  
)

# Crear la aplicación Flask
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'tu_clave_secreta_real_y_segura_aqui'  # ¡IMPORTANTE! Cambia esto por una clave secreta real y compleja
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Opcional: Limitar tamaño de subida a 16MB

# Extensiones de archivo permitidas para las fotos
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Función para verificar si la extensión del archivo es permitida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Función para conectar a la base de datos
# Usamos 'g' para almacenar la conexión y reusarla en la misma solicitud
def get_db_connection():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row  # Permite acceder a las columnas por nombre
    return g.db

# Función para cerrar la conexión a la base de datos al final de cada solicitud
@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Inicializa la base de datos y crea las tablas necesarias."""
    conn = get_db_connection() # Usamos get_db_connection para que use 'g'
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS canciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            artista TEXT NOT NULL,
            ruta_foto TEXT,
            url_web_foto TEXT
        )
    ''')
    conn.commit()
    # No cerramos la conexión aquí, porque 'teardown_appcontext' lo hará.
    print("Base de datos inicializada y tabla 'canciones' creada.")


# --- ¡CORRECCIÓN IMPORTANTE AQUÍ! ---
# Llama a init_db() fuera de su propia definición y dentro del contexto de la aplicación.
# Esto asegura que se ejecute solo una vez al iniciar la app, si la DB no existe.
with app.app_context():
    # Solo inicializa la DB si el archivo no existe (para evitar sobrescribir datos en cada reinicio)
    if not os.path.exists(DATABASE):
        init_db()
    else:
        # Si la DB ya existe, podrías querer hacer algo aquí, como un 'print'
        print("La base de datos ya existe. Saltando la inicialización de tabla.")


# --- Rutas de la Aplicación ---
@app.route('/')
def index():
    """Página principal que muestra todas las canciones."""
    conn = get_db_connection()
    canciones = conn.execute('SELECT * FROM canciones').fetchall()
    # La conexión se cerrará automáticamente por @app.teardown_appcontext
    return render_template('index.html', canciones=canciones)

@app.route('/agregar', methods=['GET', 'POST'])
def agregar_cancion():
    """Página para agregar una nueva canción."""
    if request.method == 'POST':
        # Estas variables solo se necesitan y definen cuando se envía el formulario (POST)
        titulo = request.form['titulo']
        artista = request.form['artista']
        letra = request.form['letra']
        
        ruta_foto = None # Inicialmente no hay ruta de foto en DB
        
        # Lógica para manejar la subida de la foto
        if 'foto' in request.files:
            foto_file = request.files['foto']
            if foto_file.filename != '' and allowed_file(foto_file.filename):
                filename = secure_filename(foto_file.filename)
                foto_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                foto_file.save(foto_path)
                ruta_foto = os.path.join('fotos_canciones/', filename) 
            else:
                flash('No se seleccionó una foto o el formato no es permitido.', 'warning')
        else:
            flash('No se encontró el campo de archivo "foto". Asegúrate de que tu formulario HTML sea correcto.', 'error')

        conn = get_db_connection() # Obtener la conexión dentro del POST
        try:
            conn.execute(
                'INSERT INTO canciones (titulo, artista, ruta_foto, letra) VALUES (?, ?, ?, ?)',
                (titulo, artista, ruta_foto, letra)
            )
            conn.commit()
            flash('Canción agregada exitosamente!', 'success')
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            flash('Error de integridad: Puede que ya exista una entrada similar.', 'error')
        except Exception as e:
            flash(f'Error al agregar la canción: {e}', 'error')
        finally:
            # La conexión se cerrará automáticamente por @app.teardown_appcontext
            pass 

    # Esto se ejecuta si es un GET, o si un POST falló y no hubo un redirect
    return render_template('agregar.html')

# ... (tu código app.py existente, incluyendo importaciones y configuraciones) ...

# ... (tus rutas index y agregar_cancion) ...

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_cancion(id):
    """
    Página para editar una canción existente.
    GET: Muestra el formulario con los datos actuales de la canción.
    POST: Procesa los cambios enviados por el formulario.
    """
    conn = get_db_connection()
    cancion = conn.execute('SELECT * FROM canciones WHERE id = ?', (id,)).fetchone()

    if cancion is None:
        flash('Canción no encontrada.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        titulo = request.form['titulo']
        artista = request.form['artista']
        letra = request.form['letra']
        
        ruta_foto_db = cancion['ruta_foto'] # Mantener la foto existente por defecto
        
        # Lógica para manejar la subida de una NUEVA foto
        if 'foto' in request.files:
            foto_file = request.files['foto']
            if foto_file.filename != '' and allowed_file(foto_file.filename):
                filename = secure_filename(foto_file.filename)
                foto_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                foto_file.save(foto_path)
                ruta_foto_db = os.path.join('fotos_canciones/', filename)
                flash('Foto de canción actualizada exitosamente!', 'success')
            elif foto_file.filename == '':
                # El usuario no seleccionó una nueva foto, mantiene la existente
                pass 
            else:
                flash('El formato de la nueva foto no es permitido.', 'warning')

        try:
            conn.execute(
                'UPDATE canciones SET titulo = ?, artista = ?, ruta_foto = ?, letra = ? WHERE id = ?',
                (titulo, artista, ruta_foto_db, letra, id)
            )
            conn.commit()
            flash('Canción actualizada exitosamente!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error al actualizar la canción: {e}', 'error')
        finally:
            conn.close() # Aunque tenemos teardown_appcontext, es buena práctica cerrar si se abre manualmente

    # Para la petición GET, se muestra el formulario con los datos actuales
    return render_template('editar.html', cancion=cancion)

# --- RUTA DE BÚSQUEDA ---
@app.route('/buscar')
def buscar():
    """
    Ruta para buscar canciones en tiempo real y devolver los resultados en JSON.
    """
    # Obtener el término de búsqueda de los argumentos de la URL (ej. ?q=nombre)
    query = request.args.get('q', '')
    conn = get_db_connection()
    
    # Usar LIKE para buscar coincidencias parciales, y el operador '%'
    # Esto busca cualquier canción cuyo título contenga el texto de la búsqueda
    # Usamos '%{}%'.format(query) para crear la cadena de búsqueda segura
    # En proyectos más complejos se usaría parametrización para evitar inyección SQL
    query_pattern = f'%{query}%'
    canciones = conn.execute(
        'SELECT id, titulo, artista, ruta_foto, letra FROM canciones WHERE titulo LIKE ?',
        (query_pattern,)
    ).fetchall()
    
    # Convertir la lista de objetos Row de SQLite a una lista de diccionarios
    # para que se puedan serializar a JSON
    canciones_json = [dict(cancion) for cancion in canciones]
    
    # Devolver la lista como una respuesta JSON
    return jsonify(canciones_json)


@app.route('/eliminar/<int:id>', methods=['POST'])
def eliminar_cancion(id):
    """
    Ruta para eliminar una canción de la base de datos.
    Solo acepta peticiones POST para mayor seguridad.
    """
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM canciones WHERE id = ?', (id,))
        conn.commit()
        flash('Canción eliminada exitosamente!', 'success')
    except Exception as e:
        flash(f'Error al eliminar la canción: {e}', 'error')
    finally:
        # La conexión se cerrará automáticamente por @app.teardown_appcontext
        pass 
    
    return redirect(url_for('index'))

@app.route('/subir_a_web/<int:id>', methods=['POST'])
def subir_a_web(id):
    """
    Ruta PLACEHOLDER para subir la foto de una canción a un servicio web externo.
    Por ahora, solo mostrará un mensaje y redirigirá.
    La lógica real de subida a la nube iría aquí.
    """
    conn = get_db_connection()
    cancion = conn.execute('SELECT * FROM canciones WHERE id = ?', (id,)).fetchone()

    if cancion is None:
        flash('Canción no encontrada para subir a la web.', 'error')
        return redirect(url_for('index'))

    # --- Lógica Placeholder (temporal) ---
    if cancion['ruta_foto']:
        # Construir la ruta completa al archivo de la foto local
        ruta_foto_local_completa = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(cancion['ruta_foto']))
        
        # Verificar si el archivo de la foto local existe
        if not os.path.exists(ruta_foto_local_completa):
            flash(f"Error: La foto local para '{cancion['titulo']}' no se encontró en {ruta_foto_local_completa}.", 'error')
            return redirect(url_for('index'))

        try:
            # Subir la foto a Cloudinary
            
            # Usaremos el ID de la canción como parte del public_id para que sea único y fácil de encontrar.
            public_id_cloudinary = f"canciones/{cancion['id']}_{secure_filename(os.path.basename(cancion['ruta_foto']).split('.')[0])}"
            
            # response = cloudinary.uploader.upload(ruta_foto_local_completa, public_id=public_id_cloudinary, overwrite=True)
            # Para evitar sobrescribir si el nombre de archivo es similar, se puede omitir overwrite=True
            response = cloudinary.uploader.upload(ruta_foto_local_completa, public_id=public_id_cloudinary)

            # Cloudinary devuelve la URL segura (https) de la imagen subida
            url_web_foto_cloudinary = response['secure_url']

            # Actualizar la base de datos con la URL de la foto en la nube
            conn.execute(
                'UPDATE canciones SET url_web_foto = ? WHERE id = ?',
                (url_web_foto_cloudinary, id)
            )
            conn.commit()
            flash(f"Foto de '{cancion['titulo']}' subida a la web exitosamente! URL: {url_web_foto_cloudinary}", 'success')

        except cloudinary.exceptions.Error as e:
            flash(f'Error al subir la foto a Cloudinary: {e}', 'error')
        except Exception as e:
            flash(f'Error inesperado al subir la foto: {e}', 'error')
    else:
        flash(f"La canción '{cancion['titulo']}' no tiene una foto local para subir.", 'warning')

    # La conexión se cerrará automáticamente por @app.teardown_appcontext
    return redirect(url_for('index'))


# ejecutar la aplicación
if __name__ == '__main__':
    print(f"DEBUG: Intentando usar la base de datos en: {DATABASE}")
    app.run(debug=True)