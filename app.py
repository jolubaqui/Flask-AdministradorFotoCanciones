# importar flask
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
from werkzeug.utils import secure_filename

# Define la ruta base del proyecto
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, 'instance', 'database.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'fotos_canciones') # Carpeta para guardar las fotos

# Asegúrate que las carpetas existan
os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Crear la aplicación Flask
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Cambia esto por una clave secreta real
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Opcional: Limitar tamaño de subida a 16MB

# Extensiones de archivo permitidas para las fotos
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Función para verificar si la extensión del archivo es permitida
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Función para conectar a la base de datos
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Permite acceder a las columnas por nombre
    return conn

def init_db():
    """Inicializa la base de datos y crea las tablas necesarias."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS canciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            artista TEXT NOT NULL,
            foto TEXT,
            url_web_foto TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("Base de datos inicializada y tabla 'canciones' creada.")

    with app.app_context():
        init_db()

# --- Rutas de la Aplicación (Mínimo para empezar) ---
@app.route('/')
def index():
    """Página principal que muestra todas las canciones."""
    conn = get_db_connection()
    canciones = conn.execute('SELECT * FROM canciones').fetchall()
    conn.close()
    return render_template('index.html', canciones=canciones)

@app.route('/agregar', methods=['GET', 'POST'])
def agregar_cancion():
    """Página para agregar una nueva canción."""
    if request.method == 'POST':
        titulo = request.form['titulo']
        artista = request.form['artista']
        album = request.form.get('album') # Usar .get() para campos opcionales
        genero = request.form.get('genero')
        ano_lanzamiento = request.form.get('ano_lanzamiento')
        ruta_audio = request.form['ruta_audio']

        ruta_foto_db = None # Inicialmente no hay ruta de foto en DB
        filename = None # Nombre del archivo de la foto

        # Lógica para manejar la subida de la foto
        if 'foto' in request.files: # Verificar si hay un archivo 'foto' en la petición
            foto_file = request.files['foto']
        # Si el usuario no selecciona un archivo, el navegador envía un archivo vacío sin nombre.
            if foto_file.filename != '' and allowed_file(foto_file.filename):
                filename = secure_filename(foto_file.filename) # Asegurar el nombre del archivo
                foto_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                foto_file.save(foto_path) # Guardar el archivo en el servidor
                ruta_foto = os.path.join('fotos_canciones', filename) # Guardamos la ruta relativa para facilitar la visualización en HTML

        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO canciones (titulo, artista, ruta_foto) VALUES (?, ?, ?)',
                (titulo, artista, ruta_foto)
            )
            conn.commit()
            flash('Canción agregada exitosamente!', 'success')
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            flash('Error: La ruta de audio ya existe para otra canción.', 'error')
        except Exception as e:
            flash(f'Error al agregar la canción: {e}', 'error')
        finally:
            conn.close()

    return render_template('agregar.html')

# ejecutar la aplicación
if __name__ == '__main__':
    app.run(debug=True)