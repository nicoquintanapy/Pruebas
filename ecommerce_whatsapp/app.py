import json
from flask import Flask, render_template, abort, session, redirect, url_for, request
import os # Para generar una SECRET_KEY más adelante si es necesario

app = Flask(__name__)
# Configuración de la SECRET_KEY para las sesiones
# En producción, esto debería ser un valor aleatorio y seguro, y no estar hardcodeado.
# Por ejemplo, podrías usar os.urandom(24) o cargarlo desde una variable de entorno.
app.config['SECRET_KEY'] = 'una-clave-secreta-muy-segura-para-el-carrito'

# Filtro Jinja2 personalizado para sumar cantidades en el carrito
def sum_cart_quantities(cart_dict):
    if isinstance(cart_dict, dict):
        return sum(cart_dict.values())
    return 0

app.jinja_env.filters['sum_quantities'] = sum_cart_quantities

# Cargar productos desde el archivo JSON
def cargar_productos():
    try:
        with open('data/productos.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Error: El archivo 'data/productos.json' no fue encontrado.")
        return []
    except json.JSONDecodeError:
        print("Error: El archivo 'data/productos.json' tiene un formato JSON inválido.")
        return []

productos_lista = cargar_productos()

@app.route('/')
def index():
    return render_template('index.html', productos=productos_lista)

@app.route('/producto/<string:id_producto>')
def producto(id_producto):
    producto_encontrado = None
    for p in productos_lista:
        if p['id'] == id_producto:
            producto_encontrado = p
            break

    if producto_encontrado is None:
        abort(404) # Producto no encontrado

    return render_template('producto.html', producto=producto_encontrado)

if __name__ == '__main__':
    # Se usará un puerto diferente al por defecto para evitar conflictos si hay otros servicios.
    # En un entorno de producción, esto se manejaría con un servidor WSGI como Gunicorn.
    app.run(debug=True, port=5001)

# --- Rutas y lógica del Carrito ---

@app.route('/agregar_al_carrito/<string:id_producto>', methods=['POST'])
def agregar_al_carrito(id_producto):
    # Inicializar carrito en sesión si no existe
    if 'carrito' not in session:
        session['carrito'] = {}

    # Cargar todos los productos para validar que el id_producto existe
    productos = cargar_productos()
    producto_existe = any(p['id'] == id_producto for p in productos)

    if not producto_existe:
        # Podríamos manejar esto con un mensaje flash o simplemente no hacer nada
        # Por ahora, si el producto no existe, no se añade nada.
        return redirect(request.referrer or url_for('index'))

    # Incrementar cantidad si el producto ya está en el carrito, sino añadirlo con cantidad 1
    if id_producto in session['carrito']:
        session['carrito'][id_producto] += 1
    else:
        session['carrito'][id_producto] = 1

    session.modified = True # Marcar la sesión como modificada

    # Redirigir a la página anterior o al index si no hay referrer
    return redirect(request.referrer or url_for('index'))


@app.route('/carrito')
def ver_carrito():
    # La plantilla carrito.html se creará en el siguiente paso
    # Aquí pasaremos los datos del carrito a la plantilla
    # Necesitaremos cargar los detalles de los productos basados en los IDs del carrito

    carrito_actual = session.get('carrito', {})
    productos_en_carrito_detalles = []
    total_carrito = 0

    if carrito_actual:
        todos_los_productos = cargar_productos()
        for id_prod, cantidad in carrito_actual.items():
            producto_info = next((p for p in todos_los_productos if p['id'] == id_prod), None)
            if producto_info:
                subtotal = producto_info['precio'] * cantidad
                productos_en_carrito_detalles.append({
                    'id': id_prod,
                    'nombre': producto_info['nombre'],
                    'precio': producto_info['precio'],
                    'moneda': producto_info['moneda'],
                    'cantidad': cantidad,
                    'subtotal': subtotal,
                    'imagen': producto_info.get('imagen', 'default.jpg')
                })
                total_carrito += subtotal
            else:
                # Si un producto en el carrito ya no existe en productos.json,
                # podríamos eliminarlo del carrito aquí o manejarlo de otra forma.
                # Por ahora, se omitirá.
                pass

    return render_template('carrito.html',
                           productos_carrito=productos_en_carrito_detalles,
                           total_carrito=total_carrito)


@app.route('/actualizar_carrito/<string:id_producto>', methods=['POST'])
def actualizar_carrito(id_producto):
    if 'carrito' not in session or id_producto not in session['carrito']:
        return redirect(url_for('ver_carrito')) # O manejar error

    try:
        cantidad = int(request.form.get('cantidad', 1))
    except ValueError:
        cantidad = 1 # Default si el valor no es un entero

    if cantidad <= 0:
        # Si la cantidad es 0 o negativa, eliminar el producto
        session['carrito'].pop(id_producto, None)
    else:
        session['carrito'][id_producto] = cantidad

    session.modified = True
    return redirect(url_for('ver_carrito'))


@app.route('/eliminar_del_carrito/<string:id_producto>', methods=['POST'])
def eliminar_del_carrito(id_producto):
    if 'carrito' in session and id_producto in session['carrito']:
        session['carrito'].pop(id_producto, None) # Elimina el producto del carrito
        session.modified = True

    return redirect(url_for('ver_carrito'))
