
import os
import uuid
from datetime import datetime
from functools import wraps

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, current_app,
    send_from_directory, abort
)

from werkzeug.utils import secure_filename

from base_datos import conectar


bp = Blueprint("aula", __name__)


def estudiante_requerido(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("estudiante_id"):
            flash("Inicia sesión como estudiante para acceder al aula.")
            return redirect(url_for("acceso_pagina"))

        return func(*args, **kwargs)

    return wrapper


def profesor_requerido(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("profesor_autenticado"):
            flash("Inicia sesión como profesor para continuar.", "error")
            return redirect(url_for("acceso_profesor"))

        return func(*args, **kwargs)

    return wrapper


def inicializar_aula():
    con = conectar()

    con.executescript("""
    CREATE TABLE IF NOT EXISTS materiales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        materia TEXT NOT NULL,
        grado INTEGER NOT NULL,
        descripcion TEXT,
        archivo TEXT NOT NULL,
        fecha TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS actividades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        materia TEXT NOT NULL,
        grado INTEGER NOT NULL,
        instrucciones TEXT NOT NULL,
        fecha_entrega TEXT,
        fecha_creacion TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS entregas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actividad_id INTEGER NOT NULL,
        estudiante_id INTEGER NOT NULL,
        respuesta TEXT NOT NULL,
        fecha_entrega TEXT NOT NULL,
        comentario_profesor TEXT DEFAULT '',
        calificacion REAL,
        UNIQUE(actividad_id, estudiante_id),
        FOREIGN KEY(actividad_id) REFERENCES actividades(id),
        FOREIGN KEY(estudiante_id) REFERENCES estudiantes(id)
    );

    CREATE TABLE IF NOT EXISTS preguntas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estudiante_id INTEGER NOT NULL,
        materia TEXT NOT NULL,
        mensaje TEXT NOT NULL,
        respuesta TEXT DEFAULT '',
        fecha TEXT NOT NULL,
        fecha_respuesta TEXT,
        FOREIGN KEY(estudiante_id) REFERENCES estudiantes(id)
    );
    """)

    con.commit()
    con.close()


# DATOS DE PRUEBA PARA LA CUENTA DE VALE

def insertar_datos_prueba():

    correo_demo = "vale@gmail.com"

    con = conectar()

    # Buscar la cuenta que ya está registrada.
    estudiante = con.execute(
        "SELECT id, nombre, grado FROM estudiantes WHERE correo=?",
        (correo_demo,)
    ).fetchone()

    # Si la cuenta todavía no existe, no se crean datos ficticios.
    if not estudiante:
        con.close()
        print("No se encontró la cuenta vale@gmail.com.")
        return

    estudiante_id = estudiante["id"]
    grado = estudiante["grado"]

    # Actividades de ejemplo para el grado de Vale.
    actividades_demo = [
        (
            "Ejercicios de fracciones",
            "Matemáticas",
            "Resuelve cinco ejercicios de fracciones y explica tus procedimientos.",
            "2026-11-15"
        ),
        (
            "Resumen de comprensión lectora",
            "Español",
            "Lee un texto y escribe un resumen con las ideas principales.",
            "2026-11-17"
        ),
        (
            "Cuestionario del sistema solar",
            "Ciencias",
            "Contesta cinco preguntas sobre los planetas y sus características.",
            "2026-11-19"
        )
    ]

    for actividad in actividades_demo:

        existe = con.execute("""
            SELECT id FROM actividades
            WHERE titulo=? AND grado=?
        """, (actividad[0], grado)).fetchone()

        if not existe:
            con.execute("""
                INSERT INTO actividades (
                    titulo, materia, grado, instrucciones,
                    fecha_entrega, fecha_creacion
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                actividad[0],
                actividad[1],
                grado,
                actividad[2],
                actividad[3],
                "2026-11-10 18:00"
            ))

    con.commit()

    # Buscar las actividades para registrar las entregas.
    actividad_matematicas = con.execute("""
        SELECT id FROM actividades
        WHERE titulo=? AND grado=?
    """, ("Ejercicios de fracciones", grado)).fetchone()

    actividad_espanol = con.execute("""
        SELECT id FROM actividades
        WHERE titulo=? AND grado=?
    """, ("Resumen de comprensión lectora", grado)).fetchone()

    # Entrega de Matemáticas con calificación.
    if actividad_matematicas:
        con.execute("""
            INSERT OR IGNORE INTO entregas (
                actividad_id, estudiante_id, respuesta,
                fecha_entrega, comentario_profesor, calificacion
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            actividad_matematicas["id"],
            estudiante_id,
            "Resolví los ejercicios utilizando denominadores comunes.",
            "2026-11-11 16:30",
            "Buen trabajo. Tus procedimientos son correctos.",
            9
        ))

    # Entrega de Español pendiente de calificación.
    if actividad_espanol:
        con.execute("""
            INSERT OR IGNORE INTO entregas (
                actividad_id, estudiante_id, respuesta,
                fecha_entrega, comentario_profesor, calificacion
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            actividad_espanol["id"],
            estudiante_id,
            "El texto trata sobre la importancia de cuidar el medio ambiente.",
            "2026-11-12 17:00",
            "",
            None
        ))

    # Preguntas de ejemplo para la cuenta de Vale.
    preguntas_demo = [
        (
            "Matemáticas",
            "¿Puedo entregar la actividad mañana?",
            "Sí, puedes entregarla mañana. Recuerda revisar tus procedimientos."
        ),
        (
            "Español",
            "¿El resumen debe llevar portada?",
            "Sí, debe incluir una portada y una conclusión."
        ),
        (
            "Ciencias",
            "¿Dónde puedo consultar el material de estudio?",
            ""
        )
    ]

    for materia, mensaje, respuesta in preguntas_demo:

        existe = con.execute("""
            SELECT id FROM preguntas
            WHERE estudiante_id=? AND materia=? AND mensaje=?
        """, (estudiante_id, materia, mensaje)).fetchone()

        if not existe:

            fecha_respuesta = (
                "2026-11-10 19:00" if respuesta else None
            )

            con.execute("""
                INSERT INTO preguntas (
                    estudiante_id, materia, mensaje,
                    respuesta, fecha, fecha_respuesta
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                estudiante_id,
                materia,
                mensaje,
                respuesta,
                "2026-11-10 18:30",
                fecha_respuesta
            ))

    con.commit()
    con.close()


# AULA DEL ESTUDIANTE

@bp.route("/aula")
@estudiante_requerido
def aula_estudiante():

    con = conectar()

    alumno = con.execute(
        "SELECT grado FROM estudiantes WHERE id=?",
        (session["estudiante_id"],)
    ).fetchone()

    if not alumno:
        con.close()
        session.clear()
        return redirect(url_for("acceso_pagina"))

    grado = alumno["grado"]

    materiales = con.execute("""
        SELECT * FROM materiales
        WHERE grado=?
        ORDER BY id DESC
    """, (grado,)).fetchall()

    actividades = con.execute("""
        SELECT
            a.*,
            e.id AS entrega_id,
            e.respuesta,
            e.comentario_profesor,
            e.calificacion
        FROM actividades a
        LEFT JOIN entregas e
            ON e.actividad_id=a.id
            AND e.estudiante_id=?
        WHERE a.grado=?
        ORDER BY a.id DESC
    """, (session["estudiante_id"], grado)).fetchall()

    preguntas = con.execute("""
        SELECT * FROM preguntas
        WHERE estudiante_id=?
        ORDER BY id DESC
    """, (session["estudiante_id"],)).fetchall()

    con.close()

    return render_template(
        "aula_estudiante.html",
        materiales=materiales,
        actividades=actividades,
        preguntas=preguntas,
        grado=grado
    )


@bp.route("/aula/entregar/<int:actividad_id>", methods=["POST"])
@estudiante_requerido
def entregar_actividad(actividad_id):

    respuesta = request.form.get("respuesta", "").strip()

    if not respuesta:
        flash("Escribe tu respuesta antes de entregar.")
        return redirect(
            url_for("aula.aula_estudiante") + "#actividades"
        )

    con = conectar()

    alumno = con.execute(
        "SELECT grado FROM estudiantes WHERE id=?",
        (session["estudiante_id"],)
    ).fetchone()

    actividad = con.execute("""
        SELECT id FROM actividades
        WHERE id=? AND grado=?
    """, (
        actividad_id,
        alumno["grado"] if alumno else -1
    )).fetchone()

    if not actividad:
        con.close()
        abort(404)

    con.execute("""
        INSERT INTO entregas (
            actividad_id, estudiante_id, respuesta, fecha_entrega
        )
        VALUES (?, ?, ?, ?)
        ON CONFLICT(actividad_id, estudiante_id)
        DO UPDATE SET
            respuesta=excluded.respuesta,
            fecha_entrega=excluded.fecha_entrega,
            comentario_profesor='',
            calificacion=NULL
    """, (
        actividad_id,
        session["estudiante_id"],
        respuesta,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))

    con.commit()
    con.close()

    flash("Tu actividad se entregó correctamente.")

    return redirect(
        url_for("aula.aula_estudiante") + "#actividades"
    )


@bp.route("/aula/preguntar", methods=["POST"])
@estudiante_requerido
def preguntar_profesor():

    materia = request.form.get("materia", "").strip()
    mensaje = request.form.get("mensaje", "").strip()

    if not materia or not mensaje or len(mensaje) > 1500:
        flash("Escribe la materia y una duda de máximo 1500 caracteres.")
        return redirect(
            url_for("aula.aula_estudiante") + "#preguntas"
        )

    con = conectar()

    con.execute("""
        INSERT INTO preguntas (
            estudiante_id, materia, mensaje, fecha
        )
        VALUES (?, ?, ?, ?)
    """, (
        session["estudiante_id"],
        materia,
        mensaje,
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))

    con.commit()
    con.close()

    flash("Tu pregunta fue enviada al profesor.")

    return redirect(
        url_for("aula.aula_estudiante") + "#preguntas"
    )


# PANEL DEL PROFESOR

@bp.route("/profesor/aula", methods=["GET", "POST"])
@profesor_requerido
def aula_profesor():

    con = conectar()

    if request.method == "POST":

        accion = request.form.get("accion")

        # PUBLICAR MATERIAL
        if accion == "material":

            titulo = request.form.get("titulo", "").strip()
            materia = request.form.get("materia", "").strip()
            descripcion = request.form.get("descripcion", "").strip()
            grado = request.form.get("grado", "")
            archivo = request.files.get("archivo")

            if (
                not titulo or not materia
                or grado not in ("1", "2", "3")
                or not archivo or not archivo.filename
            ):
                flash("Completa los datos y selecciona un PDF.", "error")

            elif (
                not archivo.filename.lower().endswith(".pdf")
                or archivo.mimetype not in (
                    "application/pdf",
                    "application/octet-stream"
                )
            ):
                flash("Solo se permiten archivos PDF.", "error")

            else:

                archivo.stream.seek(0, os.SEEK_END)
                tamano = archivo.stream.tell()
                archivo.stream.seek(0)

                if tamano > 10 * 1024 * 1024:
                    flash("El PDF no puede superar 10 MB.", "error")

                else:

                    nombre = secure_filename(archivo.filename)
                    nombre_final = f"{uuid.uuid4().hex}_{nombre}"

                    carpeta = os.path.join(
                        current_app.root_path,
                        "static",
                        "materiales"
                    )

                    os.makedirs(carpeta, exist_ok=True)

                    archivo.save(
                        os.path.join(carpeta, nombre_final)
                    )

                    con.execute("""
                        INSERT INTO materiales (
                            titulo, materia, grado,
                            descripcion, archivo, fecha
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        titulo,
                        materia,
                        int(grado),
                        descripcion,
                        nombre_final,
                        datetime.now().strftime("%Y-%m-%d %H:%M")
                    ))

                    con.commit()

                    flash("Material publicado correctamente.", "success")

        # CREAR ACTIVIDAD
        elif accion == "actividad":

            titulo = request.form.get("titulo", "").strip()
            materia = request.form.get("materia", "").strip()
            instrucciones = request.form.get("instrucciones", "").strip()
            grado = request.form.get("grado", "")
            fecha = request.form.get("fecha_entrega", "").strip() or None

            if titulo and materia and instrucciones and grado in ("1", "2", "3"):

                con.execute("""
                    INSERT INTO actividades (
                        titulo, materia, grado, instrucciones,
                        fecha_entrega, fecha_creacion
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    titulo,
                    materia,
                    int(grado),
                    instrucciones,
                    fecha,
                    datetime.now().strftime("%Y-%m-%d %H:%M")
                ))

                con.commit()

                flash("Actividad publicada correctamente.", "success")

            else:
                flash("Completa todos los datos de la actividad.", "error")

        # RESPONDER PREGUNTAS
        elif accion == "respuesta":

            pregunta_id = request.form.get("pregunta_id", type=int)
            respuesta = request.form.get("respuesta", "").strip()

            if pregunta_id and respuesta:

                con.execute("""
                    UPDATE preguntas
                    SET respuesta=?, fecha_respuesta=?
                    WHERE id=?
                """, (
                    respuesta,
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    pregunta_id
                ))

                con.commit()

                flash("Respuesta enviada al estudiante.", "success")

        # CALIFICAR ENTREGAS
        elif accion == "revision":

            entrega_id = request.form.get("entrega_id", type=int)
            comentario = request.form.get("comentario", "").strip()
            nota_texto = request.form.get("calificacion", "").strip()

            try:
                nota = float(nota_texto) if nota_texto else None
            except ValueError:
                nota = -1

            if entrega_id and nota == -1:
                flash("Escribe una calificación válida.", "error")

            elif entrega_id and nota is not None and not 0 <= nota <= 10:
                flash("La calificación debe estar entre 0 y 10.", "error")

            elif entrega_id:

                con.execute("""
                    UPDATE entregas
                    SET comentario_profesor=?, calificacion=?
                    WHERE id=?
                """, (comentario, nota, entrega_id))

                if nota is not None:

                    datos = con.execute("""
                        SELECT
                            en.estudiante_id,
                            a.materia,
                            a.grado
                        FROM entregas en
                        JOIN actividades a
                            ON a.id=en.actividad_id
                        WHERE en.id=?
                    """, (entrega_id,)).fetchone()

                    if datos:

                        curso = con.execute("""
                            SELECT id FROM cursos
                            WHERE materia=? AND grado=?
                            LIMIT 1
                        """, (
                            datos["materia"],
                            datos["grado"]
                        )).fetchone()

                        if curso:

                            con.execute("""
                                INSERT INTO progreso (
                                    estudiante_id, curso_id,
                                    calificacion, completado
                                )
                                VALUES (?, ?, ?, 1)
                                ON CONFLICT(estudiante_id, curso_id)
                                DO UPDATE SET
                                    calificacion=excluded.calificacion,
                                    completado=1
                            """, (
                                datos["estudiante_id"],
                                curso["id"],
                                nota
                            ))

                con.commit()

                flash("Retroalimentación guardada.", "success")

        con.close()

        return redirect(url_for("aula.aula_profesor"))

    # CONSULTAR INFORMACIÓN PARA EL PROFESOR

    materiales = con.execute("""
        SELECT * FROM materiales
        ORDER BY id DESC
    """).fetchall()

    actividades = con.execute("""
        SELECT * FROM actividades
        ORDER BY id DESC
    """).fetchall()

    preguntas = con.execute("""
        SELECT p.*, e.nombre
        FROM preguntas p
        JOIN estudiantes e ON e.id=p.estudiante_id
        ORDER BY p.id DESC
    """).fetchall()

    entregas = con.execute("""
        SELECT
            en.*,
            a.titulo,
            a.materia,
            e.nombre,
            e.correo
        FROM entregas en
        JOIN actividades a ON a.id=en.actividad_id
        JOIN estudiantes e ON e.id=en.estudiante_id
        ORDER BY en.id DESC
    """).fetchall()

    con.close()

    return render_template(
        "aula_profesor.html",
        materiales=materiales,
        actividades=actividades,
        preguntas=preguntas,
        entregas=entregas
    )


# DESCARGAR O CONSULTAR MATERIALES

@bp.route("/materiales/<path:nombre>")
@estudiante_requerido
def descargar_material(nombre):

    con = conectar()

    alumno = con.execute(
        "SELECT grado FROM estudiantes WHERE id=?",
        (session["estudiante_id"],)
    ).fetchone()

    material = con.execute("""
        SELECT archivo FROM materiales
        WHERE archivo=? AND grado=?
    """, (
        nombre,
        alumno["grado"] if alumno else -1
    )).fetchone()

    con.close()

    if not material:
        abort(404)

    carpeta = os.path.join(
        current_app.root_path,
        "static",
        "materiales"
    )

    return send_from_directory(
        carpeta,
        material["archivo"],
        as_attachment=False
    )
