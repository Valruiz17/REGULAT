
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, session
)

from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash

import os

from base_datos import (
    crear_tablas,
    conectar,
    registrar_estudiante,
    verificar_estudiante,
    guardar_progreso,
    obtener_progreso,
    obtener_promedio,
    obtener_promedio_por_grado,
    contar_actividades_completadas
)

from aula_extra import (
    bp as aula_bp,
    inicializar_aula,
    insertar_datos_prueba
)


app = Flask(__name__)
app.register_blueprint(aula_bp)

# Acceso inicial del profesor para el proyecto escolar
PROFESOR_USUARIO = os.environ.get(
    "REGULAT_PROFESOR_USUARIO", "profesor"
)

PROFESOR_CLAVE_HASH = generate_password_hash(
    os.environ.get("REGULAT_PROFESOR_CLAVE", "RegulaT2026!")
)

app.secret_key = os.environ.get("REGULAT_SECRET_KEY") or os.urandom(32)


MATERIAS = [
    {
        "nombre": "Matemáticas",
        "descripcion": "Practica operaciones, álgebra y resolución de problemas."
    },
    {
        "nombre": "Español",
        "descripcion": "Mejora tu lectura, escritura y comprensión de textos."
    },
    {
        "nombre": "Ciencias",
        "descripcion": "Aprende sobre la naturaleza y el mundo que te rodea."
    },
    {
        "nombre": "Historia",
        "descripcion": "Conoce los acontecimientos que marcaron el pasado."
    },
    {
        "nombre": "Inglés",
        "descripcion": "Practica vocabulario y comprensión del idioma."
    }
]


@app.route("/")
def inicio():
    return render_template("index.html", materias=MATERIAS)


@app.route("/cursos")
def cursos_pagina():
    if "estudiante_id" not in session:
        flash("Inicia sesión para acceder a los cursos.")
        return redirect(url_for("acceso_pagina"))

    return render_template("cursos.html")


@app.route("/registro", methods=["GET", "POST"])
def registro_pagina():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip().lower()
        grado = request.form.get("grado", "")
        contrasena = request.form.get("contrasena", "")
        confirmar = request.form.get("confirmar", "")

        if not nombre or not correo or not grado or not contrasena:
            flash("Completa todos los campos.")
            return redirect(url_for("registro_pagina"))

        if contrasena != confirmar:
            flash("Las contraseñas no coinciden.")
            return redirect(url_for("registro_pagina"))

        if len(contrasena) < 8:
            flash("La contraseña debe tener al menos 8 caracteres.")
            return redirect(url_for("registro_pagina"))

        try:
            grado = int(grado)
        except ValueError:
            flash("Selecciona un grado escolar válido.")
            return redirect(url_for("registro_pagina"))

        if grado not in (1, 2, 3):
            flash("Selecciona un grado escolar válido.")
            return redirect(url_for("registro_pagina"))

        registrado = registrar_estudiante(
            nombre, correo, grado, contrasena
        )

        if registrado:
            flash("¡Cuenta creada correctamente! Ya puedes iniciar sesión.")
            return redirect(url_for("acceso_pagina"))

        flash("Ese correo ya está registrado. Intenta iniciar sesión.")

    return render_template("registro.html")


@app.route("/acceso", methods=["GET", "POST"])
def acceso_pagina():
    if request.method == "POST":
        correo = request.form.get("correo", "").strip().lower()
        contrasena = request.form.get("contrasena", "")

        # Cerrar la sesión del profesor si se inicia como estudiante
        session.pop("profesor_autenticado", None)
        session.pop("profesor_usuario", None)

        estudiante = verificar_estudiante(correo, contrasena)

        if estudiante:
            session["estudiante_id"] = estudiante["id"]
            session["estudiante_nombre"] = estudiante["nombre"]

            flash(f"¡Bienvenido/a, {estudiante['nombre']}!")
            return redirect(url_for("perfil_pagina"))

        flash("Correo o contraseña incorrectos.")

    return render_template("acceso.html")


@app.route("/perfil")
def perfil_pagina():
    if "estudiante_id" not in session:
        return redirect(url_for("acceso_pagina"))

    estudiante_id = session["estudiante_id"]
    progreso = obtener_progreso(estudiante_id)

    promedio_primero = obtener_promedio_por_grado(estudiante_id, 1)
    promedio_segundo = obtener_promedio_por_grado(estudiante_id, 2)
    promedio_tercero = obtener_promedio_por_grado(estudiante_id, 3)

    promedio = obtener_promedio(estudiante_id)

    actividades_completadas = contar_actividades_completadas(estudiante_id)

    logros = {
        "primeros_pasos": actividades_completadas >= 1,
        "buen_estudiante": promedio >= 9,
        "constancia": actividades_completadas >= 10,
        "excelencia": promedio >= 10
    }

    return render_template(
        "perfil.html",
        nombre=session["estudiante_nombre"],
        progreso=progreso,
        promedio=promedio,
        promedio_primero=promedio_primero,
        promedio_segundo=promedio_segundo,
        promedio_tercero=promedio_tercero,
        actividades_completadas=actividades_completadas,
        logros=logros
    )


@app.route("/cerrar-sesion")
def cerrar_sesion():
    session.clear()
    flash("Has cerrado sesión correctamente.")
    return redirect(url_for("acceso_pagina"))


@app.route("/guardar-progreso", methods=["POST"])
def guardar_progreso_pagina():
    if "estudiante_id" not in session:
        return {"error": "Debes iniciar sesión."}, 401

    try:
        curso_id = int(request.form.get("curso_id", ""))
        calificacion = float(request.form.get("calificacion", ""))
    except (ValueError, TypeError):
        return {"error": "Datos de calificación inválidos."}, 400

    if not 0 <= calificacion <= 10:
        return {"error": "La calificación debe estar entre 0 y 10."}, 400

    conexion = conectar()

    try:
        curso = conexion.execute(
            "SELECT id FROM cursos WHERE id = ?",
            (curso_id,)
        ).fetchone()
    finally:
        conexion.close()

    if curso is None:
        return {"error": "El curso no existe."}, 404

    guardar_progreso(
        session["estudiante_id"],
        curso_id,
        calificacion,
        1
    )

    return {"mensaje": "Progreso guardado correctamente."}, 200


def profesor_requerido(funcion):
    @wraps(funcion)
    def decorada(*args, **kwargs):
        if not session.get("profesor_autenticado"):
            return redirect(url_for("acceso_profesor"))

        return funcion(*args, **kwargs)

    return decorada


@app.route("/profesor/acceso", methods=["GET", "POST"])
def acceso_profesor():
    if session.get("profesor_autenticado"):
        return redirect(url_for("panel_profesor"))

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        contrasena = request.form.get("contrasena", "")

        if (
            usuario == PROFESOR_USUARIO
            and check_password_hash(PROFESOR_CLAVE_HASH, contrasena)
        ):
            session.pop("estudiante_id", None)
            session.pop("estudiante_nombre", None)

            session["profesor_autenticado"] = True
            session["profesor_usuario"] = usuario
            session.permanent = True

            return redirect(url_for("panel_profesor"))

        flash("Usuario o contraseña incorrectos.", "error")

    return render_template("acceso_profesor.html")


@app.route("/profesor")
@profesor_requerido
def panel_profesor():
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT id, nombre, correo, grado
        FROM estudiantes
        ORDER BY nombre
    """)
    estudiantes = cursor.fetchall()

    cursor.execute("""
        SELECT
            e.nombre,
            e.correo,
            e.grado,
            c.nombre,
            c.materia,
            p.calificacion,
            p.completado
        FROM progreso p
        JOIN estudiantes e ON e.id = p.estudiante_id
        JOIN cursos c ON c.id = p.curso_id
        ORDER BY e.nombre, c.grado, c.materia
    """)
    calificaciones = cursor.fetchall()

    cursor.execute("""
        SELECT COUNT(*)
        FROM progreso
        WHERE completado = 1
    """)
    cursos_completados = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM estudiantes
    """)
    total_estudiantes = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM cursos
    """)
    total_cursos = cursor.fetchone()[0]

    conexion.close()

    return render_template(
        "panel_profesor.html",
        estudiantes=estudiantes,
        calificaciones=calificaciones,
        total_estudiantes=total_estudiantes,
        total_cursos=total_cursos,
        cursos_completados=cursos_completados
    )


@app.route("/profesor/cerrar-sesion")
def cerrar_sesion_profesor():
    session.pop("profesor_autenticado", None)
    session.pop("profesor_usuario", None)

    return redirect(url_for("acceso_profesor"))


if __name__ == "__main__":
    crear_tablas()
    inicializar_aula()
    insertar_datos_prueba()

    app.run(host="0.0.0.0", port=5000, debug=True)
