#python -m venv venv
#pip install flask
#pip install mysqlclient
#pip install flask-mysqldb

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL, MySQLdb
import os
import mercadopago
from werkzeug.utils import secure_filename
from MySQLdb.cursors import DictCursor
from datetime import datetime

# API MERCADO PAGO
sdk = mercadopago.SDK("TEST-5434778544108455-063007-e73a9a2bdbc519a7d09a1698cd7bce1b-1196059720")



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
            cursor.execute("SELECT * FROM productos WHERE categoria_id = %s ORDER BY id DESC", (categoria_id,))
        else:
            cursor.execute("SELECT * FROM productos ORDER BY id DESC")
        productos = cursor.fetchall()

        lista_productos = []
        for producto in productos:
            # Obtener sólo variantes activas para este producto
            cursor.execute("SELECT * FROM variantes_producto WHERE producto_id = %s AND activa = 1", (producto['id'],))
            variantes = cursor.fetchall()
            producto['variantes'] = variantes

            # Obtener reseñas
            cursor.execute("""
                SELECT r.comentario, r.puntuacion, u.correo, r.fecha
                FROM resenas r
                JOIN usuarios u ON r.usuario_id = u.id
                WHERE r.producto_id = %s
                ORDER BY r.fecha DESC
            """, (producto['id'],))
            resenas = cursor.fetchall()

            producto['resenas'] = resenas if resenas else []
            lista_productos.append(producto)

        cursor.close()

        return render_template(
            'usuario.html',
            productos=lista_productos,
            lista_productos=lista_productos,
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
        categoria_id = request.form['categoria_id']
        imagen = request.files['imagen']

        # Guardar imagen
        filename = secure_filename(imagen.filename)
        imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        imagen.save(imagen_path)

        # Insertar producto principal
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO productos (nombre, descripcion, precio, imagen, categoria_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (nombre, descripcion, precio, filename, categoria_id))
        producto_id = cur.lastrowid

        # Insertar variantes
        colores = request.form.getlist('color[]')
        talles = request.form.getlist('talle[]')
        stocks = request.form.getlist('stock_variante[]')

        for c, t, s in zip(colores, talles, stocks):
            cur.execute("""
                INSERT INTO variantes_producto (producto_id, color, talle, stock)
                VALUES (%s, %s, %s, %s)
            """, (producto_id, c.strip(), t.strip(), int(s)))

        mysql.connection.commit()
        cur.close()
        
        return redirect(url_for('admin'))
    return redirect(url_for('home'))


#AGREGAR CARRITO

@app.route('/agregar_carrito/<int:id_producto>', methods=['POST'])
def agregar_carrito(id_producto):
    if 'logueado' not in session:
        return redirect(url_for('login'))

    variante_id = request.form.get('variante_id')
    cantidad = int(request.form.get('cantidad', 1))

    if not variante_id:
        flash("Debes seleccionar una combinación válida de color y talle.")
        return redirect(url_for('usuario'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Validar stock
    cursor.execute("SELECT stock FROM variantes_producto WHERE id = %s", [variante_id])
    variante = cursor.fetchone()

    if not variante or variante['stock'] < cantidad:
        flash("No hay suficiente stock para esa combinación.")
        cursor.close()
        return redirect(url_for('usuario'))

    # Revisar si ya existe el producto en el carrito con la misma variante
    cursor.execute("""
        SELECT id, cantidad FROM carrito
        WHERE id_usuario = %s AND id_producto = %s AND id_variante = %s
    """, (session['id'], id_producto, variante_id))
    item = cursor.fetchone()

    if item:
        nueva_cantidad = item['cantidad'] + cantidad
        if nueva_cantidad <= variante['stock']:
            cursor.execute("""
                UPDATE carrito SET cantidad = %s WHERE id = %s
            """, (nueva_cantidad, item['id']))
        else:
            flash("La cantidad total supera el stock disponible.")
            cursor.close()
            return redirect(url_for('usuario'))
    else:
        cursor.execute("""
            INSERT INTO carrito (id_usuario, id_producto, id_variante, cantidad)
            VALUES (%s, %s, %s, %s)
        """, (session['id'], id_producto, variante_id, cantidad))

    mysql.connection.commit()
    cursor.close()

    flash("Producto agregado al carrito correctamente.")
    return redirect(request.referrer)



#VISTA CARRITO

@app.route('/carrito')
def ver_carrito():
    if 'logueado' in session and session['id_rol'] == 2:
        id_usuario = session['id']
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT c.id, p.nombre, p.precio, p.imagen, c.cantidad,
                   v.color, v.talle, v.stock
            FROM carrito c
            JOIN productos p ON c.id_producto = p.id
            LEFT JOIN variantes_producto v ON c.id_variante = v.id
            WHERE c.id_usuario = %s
        """, (id_usuario,))
        items = cur.fetchall()
        cur.close()

        total = sum(item['precio'] * item['cantidad'] for item in items if item['precio'])
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


#ACTUALIZAR CANTIDAD CARRITO
@app.route('/actualizar_cantidad_carrito', methods=['POST'])
def actualizar_cantidad_carrito():
    if 'logueado' in session and session['id_rol'] == 2:
        id_carrito = request.form['id']
        cantidad = int(request.form['cantidad'])
        cur = mysql.connection.cursor()

        # Opcional: verificar que cantidad sea > 0 y no supere stock de la variante
        cur.execute("""
            SELECT v.stock FROM carrito c
            JOIN variantes_producto v ON c.id_variante = v.id
            WHERE c.id = %s
        """, (id_carrito,))
        variante = cur.fetchone()
        if variante and 0 < cantidad <= variante['stock']:
            cur.execute("UPDATE carrito SET cantidad = %s WHERE id = %s", (cantidad, id_carrito))
            mysql.connection.commit()

        cur.close()
        return redirect(url_for('ver_carrito'))
    return redirect(url_for('login'))




#VISTA DE PRODUCTOS CARGADOS
@app.route('/admin/productos')
def admin_productos():
    if 'logueado' in session and session['id_rol'] == 1:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM productos ORDER BY id DESC")  # <--- Aquí el ORDER BY DESC
        productos = cur.fetchall()

        for producto in productos:
            # Obtener variantes activas solamente
            cur.execute("""
                SELECT color, talle, stock FROM variantes_producto 
                WHERE producto_id = %s AND activa = 1
            """, (producto['id'],))
            variantes = cur.fetchall()
            producto['variantes'] = variantes

            # Calcular stock total (suma de todas las variantes activas)
            producto['stock_total'] = sum(variante['stock'] for variante in variantes) if variantes else 0

        cur.close()
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
        categoria_id = request.form['categoria_id']

        # Obtener arrays del formulario
        colores = request.form.getlist('color[]')
        talles = request.form.getlist('talle[]')
        stocks = request.form.getlist('stock_variante[]')
        ids_variantes = request.form.getlist('id_variante[]')  # puede venir vacío

        # Convertir a set de IDs para comparaciones
        ids_variantes_en_form = set(int(idv) for idv in ids_variantes if idv.strip().isdigit())

        # 🧠 Obtener todas las variantes actuales del producto
        cur.execute("SELECT id FROM variantes_producto WHERE producto_id = %s", (id,))
        ids_variantes_en_bd = set(row['id'] for row in cur.fetchall())

        # 🔄 Marcar como inactivas las variantes que estaban antes pero no están en el form
        ids_para_deshabilitar = ids_variantes_en_bd - ids_variantes_en_form
        if ids_para_deshabilitar:
            cur.execute(
                "UPDATE variantes_producto SET activa = 0 WHERE id IN %s",
                (tuple(ids_para_deshabilitar),)
            )

        # Manejo de imagen
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

        # 🔄 Actualizar producto
        cur.execute("""
            UPDATE productos
            SET nombre=%s, descripcion=%s, precio=%s, imagen=%s, categoria_id=%s
            WHERE id=%s
        """, (nombre, descripcion, precio, imagen_a_guardar, categoria_id, id))

        # 💾 Insertar o actualizar variantes
        for idx in range(len(colores)):
            color = colores[idx].strip()
            talle = talles[idx].strip()
            stock = int(stocks[idx])
            id_variante = ids_variantes[idx] if idx < len(ids_variantes) else None

            if id_variante and id_variante.strip().isdigit():
                # Variante ya existente → actualizar
                cur.execute("""
                    UPDATE variantes_producto
                    SET color=%s, talle=%s, stock=%s, activa=1
                    WHERE id=%s
                """, (color, talle, stock, int(id_variante)))
            else:
                # Nueva variante
                cur.execute("""
                    INSERT INTO variantes_producto (producto_id, color, talle, stock, activa)
                    VALUES (%s, %s, %s, %s, 1)
                """, (id, color, talle, stock))

        mysql.connection.commit()
        cur.close()
        return redirect(url_for('admin_productos'))

    else:
        # Obtener producto
        cur.execute("SELECT * FROM productos WHERE id = %s", (id,))
        producto = cur.fetchone()
        if not producto:
            return "Producto no encontrado", 404

        # Obtener variantes (todas, incluso inactivas si querés mostrar en historial)
        cur.execute("SELECT * FROM variantes_producto WHERE producto_id = %s AND activa = 1", (id,))
        variantes = cur.fetchall()

        # Obtener categorías
        cur.execute("SELECT * FROM categorias")
        categorias = cur.fetchall()
        cur.close()

        producto_dict = {
            'id': producto["id"],
            'nombre': producto["nombre"],
            'descripcion': producto["descripcion"],
            'precio': producto["precio"],
            'imagen': producto["imagen"],
            'categoria_id': producto["categoria_id"],
            'variantes': variantes
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
# DATOS DEL CARRITO
# ==============================

def obtener_items_carrito():
    # Asumiendo que guardas carrito en session['carrito'] como lista de dicts
    return session.get('carrito', [])

def calcular_total_carrito(items):
    total = 0
    for item in items:
        total += item['precio'] * item['cantidad']
    return total
# ==============================
# CHECKOUT
# ==============================

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'logueado' in session and session['id_rol'] == 2:
        id_usuario = session['id']
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Obtener productos del carrito
        cur.execute("""
            SELECT c.id, p.id AS id_producto, v.id AS id_variante, p.nombre, p.precio, p.imagen, 
                   c.cantidad, v.color, v.talle, v.stock
            FROM carrito c
            JOIN productos p ON c.id_producto = p.id
            JOIN variantes_producto v ON c.id_variante = v.id
            WHERE c.id_usuario = %s
        """, (id_usuario,))
        items = cur.fetchall()

        if not items:
            flash("Tu carrito está vacío. Agregá productos antes de continuar.", "warning")
            return redirect(url_for('usuario_inicio'))

        total = sum(item['precio'] * item['cantidad'] for item in items)

        if request.method == 'POST':
            nombre = request.form['nombre']
            direccion = request.form['direccion']
            codigo_postal = request.form['codigo_postal']
            celular = request.form['celular']
            envio = request.form['envio']  # "domicilio" o "sucursal"

            # 🔁 ACTUALIZAR todos los datos del usuario
            cur.execute("""
                UPDATE usuarios 
                SET nombre = %s, direccion = %s, codigo_postal = %s, celular = %s
                WHERE id = %s
            """, (nombre, direccion, codigo_postal, celular, id_usuario))

            # Insertar venta
            cur.execute("""
                INSERT INTO ventas (
                    id_usuario, nombre_cliente, direccion_envio, total, estado_pago, estado_envio,
                    codigo_postal, celular, tipo_envio
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                id_usuario, nombre, direccion, total, "pendiente", "pendiente",
                codigo_postal, celular, envio
            ))
            id_venta = cur.lastrowid

            for item in items:
                cur.execute("""
                    INSERT INTO detalle_venta (
                        id_venta, id_producto, id_variante, cantidad, precio_unitario
                    ) VALUES (%s, %s, %s, %s, %s)
                """, (
                    id_venta, item['id_producto'], item['id_variante'],
                    item['cantidad'], item['precio']
                ))

                # Descontar stock
                cur.execute("""
                    UPDATE variantes_producto
                    SET stock = stock - %s
                    WHERE id = %s
                """, (item['cantidad'], item['id_variante']))

            # Generar preferencia Mercado Pago
            preference_data = {
                "items": [
                    {
                        "title": item['nombre'],
                        "quantity": int(item['cantidad']),
                        "unit_price": float(item['precio']),
                        "currency_id": "ARS"
                    } for item in items
                ],
                "back_urls": {
                    "success": f"http://localhost:5000/pago_exitoso?id_venta={id_venta}",
                    "failure": f"http://localhost:5000/pago_fallido?id_venta={id_venta}",
                    "pending": f"http://localhost:5000/pago_pendiente?id_venta={id_venta}"
                }
            }

            preference = sdk.preference().create(preference_data)

            if preference.get("status") == 201 and "init_point" in preference["response"]:
                # Vaciar carrito
                cur.execute("DELETE FROM carrito WHERE id_usuario = %s", (id_usuario,))
                mysql.connection.commit()
                cur.close()
                return redirect(preference["response"]["init_point"])
            else:
                flash("No se pudo generar el link de pago. Verificá los datos o credenciales.", "danger")
                return redirect(url_for('checkout'))

        else:
            # GET → precargar todos los campos del usuario
            cur.execute("SELECT nombre, direccion, codigo_postal, celular FROM usuarios WHERE id = %s", (id_usuario,))
            usuario = cur.fetchone()
            cur.close()
            return render_template('checkout.html', items=items, total=total, usuario=usuario)

    return redirect(url_for('login'))



#PAGO EXITOSO
@app.route('/pago_exitoso')
def pago_exitoso():
    id_venta = request.args.get('id_venta')
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE ventas
        SET estado_pago = 'aprobado', estado_envio = 'preparando'
        WHERE id = %s
    """, (id_venta,))
    mysql.connection.commit()
    cur.close()
    flash("¡Pago aprobado con éxito!", "success")
    return redirect(url_for('usuario_inicio'))  # Ajustá la redirección según tu sitio

@app.route('/pago_fallido')
def pago_fallido():
    id_venta = request.args.get('id_venta')
    flash("El pago fue rechazado. Podés intentarlo nuevamente desde tus pedidos.", "danger")
    return redirect(url_for('usuario_inicio'))

@app.route('/pago_pendiente')
def pago_pendiente():
    id_venta = request.args.get('id_venta')
    flash("Tu pago está pendiente. Te notificaremos cuando se acredite.", "info")
    return redirect(url_for('usuario_inicio'))

# ==============================
# ADMINISTRADOR DE VENTAS
# ==============================
@app.route('/admin/ventas')
def admin_ventas():
    if 'logueado' in session and session['id_rol'] == 1:
        cur = mysql.connection.cursor()

        # Obtener todas las ventas (ahora incluyendo código postal, celular y tipo de envío)
        cur.execute("""
            SELECT v.id, u.correo AS cliente, v.nombre_cliente, v.direccion_envio,
                   v.codigo_postal, v.celular, v.tipo_envio,
                   v.total, v.fecha, v.estado_pago, v.estado_envio
            FROM ventas v
            JOIN usuarios u ON v.id_usuario = u.id
            ORDER BY v.fecha DESC
        """)
        ventas = cur.fetchall()

        # Obtener detalles por venta
        cur.execute("""
            SELECT d.id_venta, p.nombre AS producto, d.cantidad, d.precio_unitario,
                   v.color, v.talle
            FROM detalle_venta d
            JOIN productos p ON d.id_producto = p.id
            JOIN variantes_producto v ON d.id_variante = v.id
        """)
        detalles = cur.fetchall()

        cur.close()

        return render_template('admin_ventas.html', ventas=ventas, detalles=detalles)
    return redirect(url_for('login'))

# ==============================
# IMPRIMIR ORDEN
# ==============================
@app.route('/imprimir_orden/<int:id_venta>')
def imprimir_orden(id_venta):
    cur = mysql.connection.cursor()

    # Traer datos de la venta
    cur.execute("""
        SELECT v.*, u.correo as cliente
        FROM ventas v
        JOIN usuarios u ON v.id_usuario = u.id
        WHERE v.id = %s
    """, (id_venta,))
    venta = cur.fetchone()

    # Traer detalles de la venta, incluyendo color y talle desde variantes_producto
    cur.execute("""
        SELECT dv.*, p.nombre as producto, vp.color, vp.talle
        FROM detalle_venta dv
        JOIN productos p ON dv.id_producto = p.id
        JOIN variantes_producto vp ON dv.id_variante = vp.id
        WHERE dv.id_venta = %s
    """, (id_venta,))
    detalles = cur.fetchall()

    cur.close()

    if not venta:
        return "Orden no encontrada", 404

    return render_template('imprimir_orden.html', venta=venta, detalles=detalles)

#IMPRIMIR VARIAS ORDENES

@app.route('/imprimir_ordenes')
def imprimir_ordenes():
    ids = request.args.get('ids')
    if not ids:
        return "No se recibieron IDs de ventas", 400

    try:
        ids_ventas = [int(idv) for idv in ids.split(',')]
    except ValueError:
        return "IDs inválidos", 400

    cur = mysql.connection.cursor()

    format_strings = ','.join(['%s'] * len(ids_ventas))

    # Obtener ventas
    cur.execute(f"""
        SELECT v.*, u.correo AS cliente
        FROM ventas v
        JOIN usuarios u ON v.id_usuario = u.id
        WHERE v.id IN ({format_strings})
    """, tuple(ids_ventas))
    ventas = cur.fetchall()

    # Obtener detalles con producto + color + talle
    cur.execute(f"""
        SELECT dv.id_venta, dv.cantidad, dv.precio_unitario,
               p.nombre AS producto, vp.color, vp.talle
        FROM detalle_venta dv
        JOIN productos p ON dv.id_producto = p.id
        JOIN variantes_producto vp ON dv.id_variante = vp.id
        WHERE dv.id_venta IN ({format_strings})
    """, tuple(ids_ventas))
    detalles = cur.fetchall()

    cur.close()

    if not ventas:
        return "No se encontraron ventas con esos IDs", 404

    return render_template('imprimir_varias_ordenes.html', ventas=ventas, detalles=detalles)


# ==============================
# EJECUCIÓN DE LA APP
# ==============================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
