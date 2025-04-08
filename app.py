import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
import pymysql.cursors
import re
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
# Configuración
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Configuración de la base de datos
DB_CONFIG = {
    'host': '38.58.181.152',
    'port': 3306,
    'user': 'u27637_MN0cSbObTr',
    'password': 'th9IcEXYK!+h@aTDn2Z3oSYo',
    'db': 's27637_CineDB',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# Configuración SMTP
SMTP_CONFIG = {
    'server': 'smtp.gmail.com',
    'port': 587,
    'username': '23301800@uttt.edu.mx',
    'password': 'mkll mpxe zmtn fqke',
    'from_email': '23301800@uttt.edu.mx'
}

# Crear directorio de uploads si no existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Decorador para rutas que requieren autenticación
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Por favor inicie sesión para acceder a esta página.', 'danger')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Decorador para rutas que requieren ser admin
# Decorador para rutas que requieren ser admin
# Lista de usuarios administradores
ADMIN_USERS = {'jorge'}  # Agrega aquí todos los nombres de usuario que son admins

# Decorador para rutas que requieren ser admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or session.get('username') not in ADMIN_USERS:
            flash('Acceso restringido a administradores.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Conexión a la base de datos
def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

# Validar extensión de archivo
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Sanitizar entrada
def sanitize_input(input_str):
    if not input_str:
        return None
    # Eliminar espacios en blanco al inicio y final
    input_str = input_str.strip()
    # Reemplazar múltiples espacios por uno solo
    input_str = re.sub(r'\s+', ' ', input_str)
    # Eliminar caracteres potencialmente peligrosos
    input_str = re.sub(r'[<>"\';()&]', '', input_str)
    return input_str if input_str else None

# Rutas principales
@app.route('/')
def index():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Películas en cartelera (limite de 4)
            sql = "SELECT * FROM peliculas WHERE estado = 'En cartelera' ORDER BY created_at DESC LIMIT 4"
            cursor.execute(sql)
            en_cartelera = cursor.fetchall()
            
            # Próximos estrenos (limite de 3)
            sql = "SELECT * FROM peliculas WHERE estado = 'Próximamente' ORDER BY created_at DESC LIMIT 3"
            cursor.execute(sql)
            proximas_estrenos = cursor.fetchall()
    finally:
        connection.close()
    
    return render_template('index.html', en_cartelera=en_cartelera, proximas_estrenos=proximas_estrenos)

@app.route('/cartelera')
def cartelera():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM peliculas ORDER BY created_at DESC"
            cursor.execute(sql)
            peliculas = cursor.fetchall()
    finally:
        connection.close()
    
    return render_template('cartelera.html', peliculas=peliculas)

@app.route('/pelicula/<int:id>')
def pelicula(id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM peliculas WHERE id = %s"
            cursor.execute(sql, (id,))
            pelicula = cursor.fetchone()
    finally:
        connection.close()
    
    if not pelicula:
        flash('Película no encontrada.', 'danger')
        return redirect(url_for('cartelera'))
    
    return render_template('pelicula.html', pelicula=pelicula)

# Rutas de autenticación
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Por favor ingrese nombre de usuario y contraseña.', 'danger')
            return redirect(url_for('login'))
        
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT * FROM usuarios WHERE username = %s"
                cursor.execute(sql, (username,))
                user = cursor.fetchone()
                
                if user:
                    # Verificar la contraseña
                    if password == user['password']:  # Comparación directa para pruebas
                        session['logged_in'] = True
                        session['username'] = user['username']
                        flash('Inicio de sesión exitoso!', 'success')
                        return redirect(url_for('index'))
                
                flash('Nombre de usuario o contraseña incorrectos.', 'danger')
                return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error al iniciar sesión: {str(e)}', 'danger')
            return redirect(url_for('login'))
        finally:
            connection.close()
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('index'))

@app.route('/session-status')
def session_status():
    return jsonify({
        'logged_in': session.get('logged_in', False),
        'username': session.get('username')
    })

# Rutas de administración
@app.route('/admin/peliculas')
@login_required
@admin_required
def admin_peliculas():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM peliculas ORDER BY created_at DESC"
            cursor.execute(sql)
            peliculas = cursor.fetchall()
    finally:
        connection.close()
    
    return render_template('admin/peliculas.html', peliculas=peliculas)

@app.route('/admin/peliculas/nueva', methods=['GET', 'POST'])
@login_required
@admin_required
def nueva_pelicula():
    if request.method == 'POST':
        # Validar y sanitizar todos los campos
        titulo = sanitize_input(request.form.get('titulo'))
        duracion = sanitize_input(request.form.get('duracion'))
        clasificacion = sanitize_input(request.form.get('clasificacion'))
        categoria = sanitize_input(request.form.get('categoria'))
        estado = sanitize_input(request.form.get('estado'))
        idioma = sanitize_input(request.form.get('idioma'))
        horarios = sanitize_input(request.form.get('horarios'))
        sala = sanitize_input(request.form.get('sala'))
        director = sanitize_input(request.form.get('director'))
        trailer_url = sanitize_input(request.form.get('trailer_url'))
        sinopsis = sanitize_input(request.form.get('sinopsis'))
        
        # Validar archivo de imagen
        if 'imagen' not in request.files:
            flash('No se ha seleccionado ninguna imagen.', 'danger')
            return redirect(request.url)
        
        file = request.files['imagen']
        if file.filename == '':
            flash('No se ha seleccionado ninguna imagen.', 'danger')
            return redirect(request.url)
        
        if not (file and allowed_file(file.filename)):
            flash('Formato de imagen no permitido. Use JPG, PNG o GIF.', 'danger')
            return redirect(request.url)
        
        # Validar campos obligatorios
        required_fields = {
            'título': titulo,
            'duración': duracion,
            'clasificación': clasificacion,
            'categoría': categoria,
            'estado': estado,
            'idioma': idioma,
            'horarios': horarios,
            'sala': sala,
            'director': director,
            'trailer': trailer_url,
            'sinopsis': sinopsis
        }
        
        for field, value in required_fields.items():
            if not value:
                flash(f'El campo {field} es obligatorio.', 'danger')
                return redirect(request.url)
        
        # Guardar la imagen
        filename = secure_filename(file.filename)
        unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(save_path)
        imagen_url = url_for('static', filename=f'uploads/{unique_filename}')
        
        # Insertar en la base de datos
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                sql = """
                INSERT INTO peliculas 
                (titulo, duracion, clasificacion, categoria, estado, idioma, 
                 horarios, sala, director, trailer_url, sinopsis, imagen_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    titulo, duracion, clasificacion, categoria, estado, 
                    idioma, horarios, sala, director, trailer_url, 
                    sinopsis, imagen_url
                ))
                connection.commit()
                flash('Película agregada exitosamente!', 'success')
                return redirect(url_for('admin_peliculas'))
        except Exception as e:
            connection.rollback()
            flash(f'Error al agregar película: {str(e)}', 'danger')
        finally:
            connection.close()
    
    return render_template('admin/editar.html', pelicula=None)

@app.route('/admin/peliculas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_pelicula(id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM peliculas WHERE id = %s"
            cursor.execute(sql, (id,))
            pelicula = cursor.fetchone()
            
            if not pelicula:
                flash('Película no encontrada.', 'danger')
                return redirect(url_for('admin_peliculas'))
            
            if request.method == 'POST':
                # Obtener y validar datos del formulario
                titulo = sanitize_input(request.form.get('titulo'))
                duracion = sanitize_input(request.form.get('duracion'))
                clasificacion = sanitize_input(request.form.get('clasificacion'))
                categoria = sanitize_input(request.form.get('categoria'))
                estado = sanitize_input(request.form.get('estado'))
                idioma = sanitize_input(request.form.get('idioma'))
                horarios = sanitize_input(request.form.get('horarios'))
                sala = sanitize_input(request.form.get('sala'))
                director = sanitize_input(request.form.get('director'))
                trailer_url = sanitize_input(request.form.get('trailer_url'))
                sinopsis = sanitize_input(request.form.get('sinopsis'))
                
                # Validar campos obligatorios
                required_fields = {
                    'título': titulo,
                    'duración': duracion,
                    'clasificación': clasificacion,
                    'categoría': categoria,
                    'estado': estado,
                    'idioma': idioma,
                    'horarios': horarios,
                    'sala': sala,
                    'director': director,
                    'trailer': trailer_url,
                    'sinopsis': sinopsis
                }
                
                for field, value in required_fields.items():
                    if not value:
                        flash(f'El campo {field} es obligatorio.', 'danger')
                        return redirect(request.url)
                
                # Manejar la imagen si se subió una nueva
                imagen_url = pelicula['imagen_url']
                if 'imagen' in request.files:
                    file = request.files['imagen']
                    if file.filename != '' and allowed_file(file.filename):
                        # Eliminar la imagen anterior si existe
                        if pelicula['imagen_url']:
                            old_filename = pelicula['imagen_url'].split('/')[-1]
                            old_path = os.path.join(app.config['UPLOAD_FOLDER'], old_filename)
                            if os.path.exists(old_path):
                                os.remove(old_path)
                        
                        # Guardar la nueva imagen
                        filename = secure_filename(file.filename)
                        unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                        file.save(save_path)
                        imagen_url = url_for('static', filename=f'uploads/{unique_filename}')
                
                # Actualizar en la base de datos
                sql = """
                UPDATE peliculas 
                SET titulo = %s, duracion = %s, clasificacion = %s, categoria = %s, 
                    estado = %s, idioma = %s, horarios = %s, sala = %s, 
                    director = %s, trailer_url = %s, sinopsis = %s, imagen_url = %s
                WHERE id = %s
                """
                cursor.execute(sql, (
                    titulo, duracion, clasificacion, categoria, estado, 
                    idioma, horarios, sala, director, trailer_url, 
                    sinopsis, imagen_url, id
                ))
                connection.commit()
                flash('Película actualizada exitosamente!', 'success')
                return redirect(url_for('admin_peliculas'))
            
    finally:
        connection.close()
    
    return render_template('admin/editar.html', pelicula=pelicula)

@app.route('/admin/peliculas/eliminar/<int:id>', methods=['POST'])
@login_required
@admin_required
def eliminar_pelicula(id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Obtener la película para eliminar su imagen
            sql = "SELECT imagen_url FROM peliculas WHERE id = %s"
            cursor.execute(sql, (id,))
            pelicula = cursor.fetchone()
            
            if pelicula and pelicula['imagen_url']:
                # Eliminar la imagen del sistema de archivos
                filename = pelicula['imagen_url'].split('/')[-1]
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
            
            # Eliminar la película de la base de datos
            sql = "DELETE FROM peliculas WHERE id = %s"
            cursor.execute(sql, (id,))
            connection.commit()
            flash('Película eliminada exitosamente!', 'success')
    except Exception as e:
        connection.rollback()
        flash(f'Error al eliminar película: {str(e)}', 'danger')
    finally:
        connection.close()
    
    return redirect(url_for('admin_peliculas'))

# Ruta para enviar correo de contacto
@app.route('/contacto', methods=['POST'])
def contacto():
    nombre = sanitize_input(request.form.get('nombre'))
    email = sanitize_input(request.form.get('email'))
    mensaje = sanitize_input(request.form.get('mensaje'))
    
    if not nombre or not email or not mensaje:
        flash('Por favor complete todos los campos del formulario.', 'danger')
        return redirect(url_for('index'))
    
    # Validar formato de email
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        flash('Por favor ingrese un correo electrónico válido.', 'danger')
        return redirect(url_for('index'))
    
    # Configurar el mensaje de correo
    msg = MIMEMultipart()
    msg['From'] = SMTP_CONFIG['from_email']
    msg['To'] = SMTP_CONFIG['from_email']
    msg['Subject'] = f'Mensaje de contacto de {nombre} - CineFlask'
    
    body = f"""
    Nombre: {nombre}
    Email: {email}
    Mensaje:
    {mensaje}
    """
    msg.attach(MIMEText(body, 'plain'))
    
    # Enviar el correo
    try:
        server = smtplib.SMTP(SMTP_CONFIG['server'], SMTP_CONFIG['port'])
        server.starttls()
        server.login(SMTP_CONFIG['username'], SMTP_CONFIG['password'])
        server.send_message(msg)
        server.quit()
        flash('Mensaje enviado correctamente. Gracias por contactarnos!', 'success')
    except Exception as e:
        flash(f'Error al enviar el mensaje: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)