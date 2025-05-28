#python -m venv venv
#pip install flask
#pip install mysqlclient
#pip install flask-mysqldb

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL, MySQLdb
import os
from werkzeug.utils import secure_filename
from MySQLdb.cursors import DictCursor
from datetime import datetime



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
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM categorias")
        categorias = cursor.fetchall()
        cursor.close()
        return render_template('admin.html', categorias=categorias)
    return redirect(url_for('home'))


# RUTA PARA USUARIO COMÚN (protegida) + (RESEÑAS)
@app.route('/usuario')
def usuario():
    if 'logueado' in session and session['id_rol'] == 2:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Obtener todas las categorías
        cursor.execute("SELECT * FROM categorias")
        categorias = cursor.fetchall()

        # Obtener el ID de la categoría seleccionada desde la URL
        categoria_id = request.args.get('categoria_id')

        # Filtrar productos según la categoría si se seleccionó alguna
        if categoria_id:
            cursor.execute("SELECT * FROM productos WHERE categoria_id = %s", (categoria_id,))
        else:
            cursor.execute("SELECT * FROM productos")
        productos = cursor.fetchall()

        lista_productos = []
        for producto in productos:
            producto['talles'] = [t.strip() for t in producto['talle'].split(',')] if producto['talle'] else []
            producto['colores'] = [c.strip() for c in producto['color'].split(',')] if producto['color'] else []

            cursor.execute("""
                SELECT r.comentario, r.puntuacion, u.correo, r.fecha
                FROM resenas r
                JOIN usuarios u ON r.usuario_id = u.id
                WHERE r.producto_id = %s
                ORDER BY r.fecha DESC;
            """, (producto['id'],))
            resenas = cursor.fetchall()

            producto['resenas'] = resenas if resenas else []
            lista_productos.append(producto)

        cursor.close()

        return render_template(
            'usuario.html',
            productos=lista_productos,
            categorias=categorias,
            categoria_seleccionada=int(categoria_id) if categoria_id else None
        )

    return redirect(url_for('home'))





# =============================
# CERRAR SESIÓN
# =============================

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# CARGAR PRODUCTOS

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
        stock = request.form['stock']
        categoria_id = request.form['categoria_id']  # ✅ NUEVO CAMPO
        imagen = request.files['imagen']

        if imagen:
            filename = secure_filename(imagen.filename)
            imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagen.save(imagen_path)

            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO productos (nombre, descripcion, precio, color, talle, stock, imagen, categoria_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (nombre, descripcion, precio, color, talle, stock, filename, categoria_id))  # ✅ MODIFICADO
            mysql.connection.commit()
            cur.close()

        return redirect(url_for('admin'))

    return redirect(url_for('home'))


#AGREGAR CARRITO

@app.route('/agregar-carrito/<int:id_producto>', methods=['POST'])
def agregar_carrito(id_producto):
    if 'logueado' in session and session['id_rol'] == 2:
        cantidad = int(request.form.get('cantidad', 1))
        color = request.form.get('color')
        talle = request.form.get('talle')
        id_usuario = session['id']

        cur = mysql.connection.cursor()
        # Verificar si ya existe el producto con el mismo talle y color
        cur.execute("""
            SELECT * FROM carrito 
            WHERE id_usuario = %s AND id_producto = %s AND talle = %s AND color = %s
        """, (id_usuario, id_producto, talle, color))
        existente = cur.fetchone()

        if existente:
            cur.execute("""
                UPDATE carrito 
                SET cantidad = cantidad + %s 
                WHERE id_usuario = %s AND id_producto = %s AND talle = %s AND color = %s
            """, (cantidad, id_usuario, id_producto, talle, color))
        else:
            cur.execute("""
                INSERT INTO carrito (id_usuario, id_producto, cantidad, talle, color)
                VALUES (%s, %s, %s, %s, %s)
            """, (id_usuario, id_producto, cantidad, talle, color))

        mysql.connection.commit()
        cur.close()
        return redirect(url_for('usuario'))
    return redirect(url_for('login'))


#VISTA CARRITO

@app.route('/carrito')
def ver_carrito():
    if 'logueado' in session and session['id_rol'] == 2:
        id_usuario = session['id']
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT c.id, p.nombre, p.precio, p.imagen, c.cantidad, c.talle, c.color
            FROM carrito c
            JOIN productos p ON c.id_producto = p.id
            WHERE c.id_usuario = %s
        """, (id_usuario,))
        items = cur.fetchall()
        cur.close()

        total = sum(item['precio'] * item['cantidad'] for item in items)
        total_cantidad = sum(item['cantidad'] for item in items)

        return render_template('carrito.html', items=items, total=total, total_cantidad=total_cantidad)
    return redirect(url_for('login'))



#ELIMINAR CARRITO
@app.route('/eliminar_del_carrito', methods=['POST'])
def eliminar_del_carrito():
    if 'logueado' in session and session['id_rol'] == 2:
        id_carrito = request.form['id']
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM carrito WHERE id = %s", (id_carrito,))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('ver_carrito'))
    return redirect(url_for('login'))

@app.context_processor
def carrito_total():
    total_cantidad = 0
    if 'logueado' in session and session['id_rol'] == 2:
        cur = mysql.connection.cursor()
        cur.execute("SELECT SUM(cantidad) AS total FROM carrito WHERE id_usuario = %s", (session['id'],))
        result = cur.fetchone()
        cur.close()
        total_cantidad = result['total'] if result['total'] else 0
    return dict(total_cantidad=total_cantidad)



#VISTA DE PRODUCTOS CARGADOS
@app.route('/admin/productos')
def admin_productos():
    if 'logueado' in session and session['id_rol'] == 1:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  # <- Cambiado aquí
        cur.execute("SELECT * FROM productos")
        productos = cur.fetchall()
        cur.close()

        for producto in productos:
            producto['talles'] = producto['talle'].split(',') if producto['talle'] else []
            producto['colores'] = producto['color'].split(',') if producto['color'] else []

        return render_template('admin_productos.html', productos=productos)
    return redirect(url_for('home'))

 

# EDITAR PRODUCTO 
@app.route('/admin/producto/editar/<int:id>', methods=['GET', 'POST'])
def editar_producto(id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = float(request.form['precio'])
        stock = int(request.form['stock'])

        colores_input = request.form['color']
        talles_input = request.form['talle']
        categoria_id = request.form['categoria_id']  # 🟢 Nuevo

        colores = [c.strip() for c in colores_input.split(',') if c.strip()]
        talles = [t.strip() for t in talles_input.split(',') if t.strip()]
        colores_str = ','.join(colores)
        talles_str = ','.join(talles)

        cur.execute("SELECT imagen FROM productos WHERE id = %s", (id,))
        producto_actual = cur.fetchone()
        imagen_actual = producto_actual['imagen'] if producto_actual else None

        imagen_nueva = request.files.get('imagen')
        if imagen_nueva and imagen_nueva.filename != '':
            filename = secure_filename(imagen_nueva.filename)
            ruta_guardado = os.path.join('static/imagenes_productos', filename)
            imagen_nueva.save(ruta_guardado)

            if imagen_actual and imagen_actual != filename:
                ruta_imagen_actual = os.path.join('static/imagenes_productos', imagen_actual)
                if os.path.exists(ruta_imagen_actual):
                    os.remove(ruta_imagen_actual)

            imagen_a_guardar = filename
        else:
            imagen_a_guardar = imagen_actual

        # 🔄 Agregamos categoria_id al UPDATE
        cur.execute("""
            UPDATE productos
            SET nombre=%s, descripcion=%s, precio=%s, stock=%s, color=%s, talle=%s, imagen=%s, categoria_id=%s
            WHERE id=%s
        """, (nombre, descripcion, precio, stock, colores_str, talles_str, imagen_a_guardar, categoria_id, id))
        mysql.connection.commit()

        return redirect(url_for('admin_productos'))

    else:
        # Obtener el producto
        cur.execute("SELECT * FROM productos WHERE id = %s", (id,))
        producto = cur.fetchone()

        if not producto:
            return "Producto no encontrado", 404

        # 🟢 Obtener categorías
        cur.execute("SELECT * FROM categorias")
        categorias = cur.fetchall()

        producto_dict = {
            'id': producto["id"],
            'nombre': producto["nombre"],
            'descripcion': producto["descripcion"],
            'precio': producto["precio"],
            'stock': producto["stock"],
            'imagen': producto["imagen"],
            'colores': producto["color"].split(',') if producto["color"] else [],
            'talles': producto["talle"].split(',') if producto["talle"] else [],
            'categoria_id': producto["categoria_id"]  # 🟢 Necesario para marcar la categoría seleccionada
        }

        return render_template('editar_producto.html', producto=producto_dict, categorias=categorias)





# BORRAR PRODUCTO 
@app.route('/admin/producto/eliminar/<int:id>', methods=['POST'])
def eliminar_producto(id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)  # 🛠️ Usamos DictCursor

    # Buscar la imagen actual
    cur.execute("SELECT imagen FROM productos WHERE id = %s", (id,))
    producto = cur.fetchone()

    if producto:
        imagen = producto['imagen']  # Acceso por nombre de campo
        ruta_imagen = os.path.join('static/imagenes_productos', imagen)

        if os.path.exists(ruta_imagen):
            os.remove(ruta_imagen)

        cur.execute("DELETE FROM productos WHERE id = %s", (id,))
        mysql.connection.commit()
        return redirect(url_for('admin_productos'))
    
# AGREGAR RESEÑAS
@app.route('/agregar_resena/<int:producto_id>', methods=['POST'])
def agregar_resena(producto_id):
    if not session.get('logueado'):
        return redirect(url_for('login'))

    usuario_id = session.get('id')
    comentario = request.form.get('comentario', '').strip()
    try:
        puntuacion = int(request.form.get('puntuacion'))
    except (ValueError, TypeError):
        return "Puntuación inválida", 400

    if not comentario:
        return "El comentario no puede estar vacío", 400

    if puntuacion < 1 or puntuacion > 5:
        return "Puntuación inválida", 400

    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO resenas (producto_id, usuario_id, puntuacion, comentario, fecha)
            VALUES (%s, %s, %s, %s, NOW())
        """, (producto_id, usuario_id, puntuacion, comentario))
        mysql.connection.commit()
    except mysql.connection.Error as e:
        # Aquí podrías manejar errores de base de datos, por ejemplo, si existe una reseña duplicada por la restricción UNIQUE
        return f"Error al agregar la reseña: {str(e)}", 500
    finally:
        cursor.close()

    return redirect(url_for('usuario'))



#CATEGORIAS
# Listar categorías
@app.route('/admin/categorias')
def admin_categorias():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, nombre FROM categorias ORDER BY id ASC")
    categorias = cur.fetchall()  # lista de tuplas (id, nombre)
    cur.close()

    return render_template('admin_categorias.html', categorias=categorias)

#agrgar categorias
@app.route('/admin/categorias/agregar', methods=['GET', 'POST'])
def agregar_categoria():
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        if not nombre:
            flash('El nombre de la categoría no puede estar vacío', 'danger')
            return redirect(url_for('agregar_categoria'))

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO categorias (nombre) VALUES (%s)", (nombre,))
        mysql.connection.commit()
        cur.close()

        flash('Categoría agregada con éxito', 'success')
        return redirect(url_for('admin_categorias'))

    return render_template('agregar_categoria.html')

#editar categorias
@app.route('/admin/categorias/editar/<int:id>', methods=['GET', 'POST'])
def editar_categoria(id):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        if not nombre:
            flash('El nombre de la categoría no puede estar vacío', 'danger')
            return redirect(url_for('editar_categoria', id=id))

        cur.execute("UPDATE categorias SET nombre = %s WHERE id = %s", (nombre, id))
        mysql.connection.commit()
        cur.close()
        flash('Categoría actualizada', 'success')
        return redirect(url_for('admin_categorias'))

    # GET
    cur.execute("SELECT id, nombre FROM categorias WHERE id = %s", (id,))
    categoria = cur.fetchone()
    cur.close()
    if categoria is None:
        flash('Categoría no encontrada', 'danger')
        return redirect(url_for('admin_categorias'))

    return render_template('editar_categoria.html', categoria=categoria)


#ruta eliminar categorias
@app.route('/admin/categorias/eliminar/<int:id>', methods=['POST'])
def eliminar_categoria(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM categorias WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('Categoría eliminada', 'success')
    return redirect(url_for('admin_categorias'))




# ==============================
# EJECUCIÓN DE LA APP
# ==============================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
