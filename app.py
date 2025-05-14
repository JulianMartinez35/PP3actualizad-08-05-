#python -m venv venv
#pip install flask
#pip install mysqlclient
#pip install flask-mysqldb

from flask import Flask, render_template, request, redirect, url_for, session
from flask_mysqldb import MySQL, MySQLdb
import os
from werkzeug.utils import secure_filename


# Configuración general
app = Flask(__name__, template_folder='template')
app.secret_key = "pinchellave"  # Clave secreta para sesiones

# Configuración de la base de datos
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'login'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

# =============================
# RUTAS PRINCIPALES
# =============================

@app.route('/')
def home():
    return render_template('index.html')

# RUTA A INICIO
@app.route("/inicio")
def inicio():
    return render_template("inicio.html")

# RUTA A PRODUCTOS
@app.route("/productos")
def productos():
    return render_template("productos.html")

# RUTA A NOSOTROS
@app.route("/nosotros")
def nosotros():
    return render_template("nosotros.html")

# RUTA A REGISTROS
@app.route('/registro')
def registro():
    return render_template('registro.html')

# ==============================
# LOGIN
# ==============================

@app.route('/acceso-login', methods=["POST", "GET"])
def login():
    if request.method == 'POST':
        correo = request.form['txtCorreo']
        password = request.form['txtPassword']

        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM usuarios WHERE correo = %s AND password = %s', (correo, password))
        usuario = cur.fetchone()
        cur.close()

        if usuario:
            session['logueado'] = True
            session['id'] = usuario['id']
            session['id_rol'] = usuario['id_rol']
            session['email'] = usuario['correo']

            if session['id_rol'] == 1:
                return redirect(url_for('admin'))
            elif session['id_rol'] == 2:
                return redirect(url_for('usuario'))
        else:
            return render_template('index.html', mensaje="Usuario o Contraseña Incorrectos")

    return render_template('index.html')

# ==============================
# REGISTRO
# ============================

@app.route('/crear-registro', methods=["POST"])
def crear_registro():
    correo = request.form['txtCorreo']
    password = request.form['txtPassword']
    confirm_password = request.form['txtConfirmPassword']
    pregunta = request.form['pregunta_seguridad']
    respuesta = request.form['respuesta_seguridad']

    # Validar coincidencia de contraseñas
    if password != confirm_password:
        return render_template("registro.html", mensaje="Las contraseñas no coinciden.")

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM usuarios WHERE correo = %s", (correo,))
    existente = cur.fetchone()

    if existente:
        cur.close()
        return render_template("registro.html", mensaje="Este correo ya está registrado.")

    # Registrar nuevo usuario
    cur.execute("""
        INSERT INTO usuarios (correo, password, id_rol, pregunta_seguridad, respuesta_seguridad)
        VALUES (%s, %s, '2', %s, %s)
    """, (correo, password, pregunta, respuesta))
    mysql.connection.commit()
    cur.close()

    return render_template("index.html", mensaje2="Usuario registrado exitosamente.")

# ==============================
# RECUPERACIÓN DE CONTRASEÑA
# ==============================

@app.route('/recuperar', methods=["GET"])
def mostrar_recuperar():
    return render_template("recuperar.html")

@app.route('/recuperar', methods=["POST"])
def recuperar():
    correo = request.form['correo']
    nueva_password = request.form['nueva_password']
    confirmar_password = request.form['confirmar_password']
    pregunta = request.form['pregunta_seguridad']
    respuesta = request.form['respuesta_seguridad']

    if nueva_password != confirmar_password:
        return render_template("recuperar.html", mensaje="Las contraseñas no coinciden.")

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM usuarios WHERE correo = %s", (correo,))
    usuario = cur.fetchone()

    if not usuario:
        cur.close()
        return render_template("recuperar.html", mensaje="Correo no registrado.")

    if usuario['pregunta_seguridad'] != pregunta or usuario['respuesta_seguridad'].lower() != respuesta.lower():
        cur.close()
        return render_template("recuperar.html", mensaje="Respuesta incorrecta.")

    cur.execute("UPDATE usuarios SET password = %s WHERE correo = %s", (nueva_password, correo))
    mysql.connection.commit()
    cur.close()

    return render_template("index.html", mensaje2="Contraseña actualizada correctamente.")

# ==============================
# PÁGINAS PROTEGIDAS
# ==============================

# RUTA PARA ADMIN (protegida)
@app.route('/admin')
def admin():
    if 'logueado' in session and session['id_rol'] == 1:
        return render_template('admin.html')
    return redirect(url_for('home'))

# RUTA PARA USUARIO COMÚN (protegida)
@app.route('/usuario')
def usuario():
    if 'logueado' in session and session['id_rol'] == 2:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM productos")
        productos = cur.fetchall()
        cur.close()
        return render_template('usuario.html', productos=productos)
    return redirect(url_for('home'))


# =============================
# CERRAR SESIÓN
# =============================

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

#CARGAR PRODUCTOS

# Carpeta para subir imágenes
UPLOAD_FOLDER = 'static/imagenes_productos'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/cargar-producto', methods=['POST'])
def cargar_producto():
    if 'logueado' in session and session['id_rol'] == 1:
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        color = request.form['color']
        talle = request.form['talle']
        imagen = request.files['imagen']

        if imagen:
            filename = secure_filename(imagen.filename)
            imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagen.save(imagen_path)

            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO productos (nombre, descripcion, precio, color, talle, imagen)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (nombre, descripcion, precio, color, talle, filename))
            mysql.connection.commit()
            cur.close()

        return redirect(url_for('admin'))

    return redirect(url_for('home'))



# ==============================
# EJECUCIÓN DE LA APP
# ==============================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
