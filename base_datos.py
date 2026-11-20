
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash



def conectar():
    conexion = sqlite3.connect("regulat.db")
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion



def crear_tablas():
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS estudiantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            correo TEXT NOT NULL UNIQUE,
            grado INTEGER NOT NULL,
            contrasena TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cursos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            materia TEXT NOT NULL,
            grado INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS progreso (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estudiante_id INTEGER NOT NULL,
            curso_id INTEGER NOT NULL,
            calificacion REAL DEFAULT 0,
            completado INTEGER DEFAULT 0,
            FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id),
            FOREIGN KEY (curso_id) REFERENCES cursos(id),
            UNIQUE (estudiante_id, curso_id)
        )
    """)

    cursos_iniciales = [
        (
            "Matemáticas",
            "Practica operaciones, fracciones y álgebra.",
            "Matemáticas",
            1
        ),
        (
            "Español",
            "Practica lectura, ortografía y redacción.",
            "Español",
            1
        ),
        (
            "Ciencias",
            "Aprende sobre los seres vivos y la naturaleza.",
            "Ciencias",
            1
        ),
        (
            "Historia",
            "Conoce los acontecimientos históricos.",
            "Historia",
            1
        ),
        (
            "Inglés",
            "Practica vocabulario y comprensión del idioma.",
            "Inglés",
            1
        )
                ,
        (
            "Matemáticas",
            "Practica fracciones, porcentajes y potencias.",
            "Matemáticas",
            2
        ),
        (
            "Español",
            "Practica verbos, pronombres y comprensión lectora.",
            "Español",
            2
        ),
        (
            "Ciencias",
            "Aprende sobre fuerzas, energía y el espacio.",
            "Ciencias",
            2
        ),
        (
            "Historia",
            "Conoce la Revolución Mexicana y otros acontecimientos.",
            "Historia",
            2
        ),
        (
            "Inglés",
            "Practica vocabulario y tiempos verbales.",
            "Inglés",
            2
        ),
        (
            "Matemáticas",
            "Practica ecuaciones, álgebra y potencias.",
            "Matemáticas",
            3
        ),
        (
            "Español",
            "Practica argumentación, literatura y redacción.",
            "Español",
            3
        ),
        (
            "Ciencias",
            "Aprende sobre genética, electricidad y física.",
            "Ciencias",
            3
        ),
        (
            "Historia",
            "Estudia acontecimientos históricos contemporáneos.",
            "Historia",
            3
        ),
        (
            "Inglés",
            "Practica tiempos verbales y comprensión del inglés.",
            "Inglés",
            3
        )
    ]

    for curso in cursos_iniciales:
        cursor.execute("""
            SELECT id FROM cursos
            WHERE nombre = ? AND grado = ?
        """, (curso[0], curso[3]))

        if cursor.fetchone() is None:
            cursor.execute("""
                INSERT INTO cursos (
                    nombre, descripcion, materia, grado
                )
                VALUES (?, ?, ?, ?)
            """, curso)

    conexion.commit()
    conexion.close()


def registrar_estudiante(nombre, correo, grado, contrasena):
    conexion = conectar()

    try:
        contrasena_segura = generate_password_hash(contrasena)

        conexion.execute("""
            INSERT INTO estudiantes (nombre, correo, grado, contrasena)
            VALUES (?, ?, ?, ?)
        """, (nombre, correo.lower().strip(), grado, contrasena_segura))

        conexion.commit()
        return True

    except sqlite3.IntegrityError:
        return False

    finally:
        conexion.close()


def verificar_estudiante(correo, contrasena):
    conexion = conectar()

    try:
        estudiante = conexion.execute("""
            SELECT * FROM estudiantes
            WHERE correo = ?
        """, (correo.lower().strip(),)).fetchone()

        if estudiante and check_password_hash(
            estudiante["contrasena"], contrasena
        ):
            return estudiante

        return None

    finally:
        conexion.close()


def guardar_progreso(estudiante_id, curso_id, calificacion, completado):
    conexion = conectar()

    try:
        conexion.execute("""
            INSERT INTO progreso (
                estudiante_id, curso_id, calificacion, completado
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(estudiante_id, curso_id)
            DO UPDATE SET
                calificacion = excluded.calificacion,
                completado = excluded.completado
        """, (
            estudiante_id,
            curso_id,
            calificacion,
            completado
        ))

        conexion.commit()

    finally:
        conexion.close()


def obtener_progreso(estudiante_id):
    conexion = conectar()

    try:
        progreso = conexion.execute("""
             SELECT
                cursos.nombre AS curso,
                cursos.materia AS materia,
                cursos.grado AS grado,
                progreso.calificacion AS calificacion,
                progreso.completado AS completado
            FROM progreso
            INNER JOIN cursos ON cursos.id = progreso.curso_id
            WHERE progreso.estudiante_id = ?
            ORDER BY cursos.nombre
        """, (estudiante_id,)).fetchall()

        return progreso

    finally:
        conexion.close()

def obtener_promedio(estudiante_id):
    conexion = conectar()

    try:
        resultado = conexion.execute("""
            SELECT AVG(calificacion) AS promedio
            FROM progreso
            WHERE estudiante_id = ?
              AND completado = 1
        """, (estudiante_id,)).fetchone()

        if resultado["promedio"] is None:
            return 0

        return round(resultado["promedio"], 2)

    finally:
        conexion.close()

def obtener_promedio_por_grado(estudiante_id, grado):
    conexion = conectar()

    try:
        resultado = conexion.execute("""
            SELECT AVG(progreso.calificacion) AS promedio
            FROM progreso
            INNER JOIN cursos
                ON cursos.id = progreso.curso_id
            WHERE progreso.estudiante_id = ?
              AND cursos.grado = ?
              AND progreso.completado = 1
        """, (estudiante_id, grado)).fetchone()

        if resultado["promedio"] is None:
            return 0

        return round(resultado["promedio"], 2)

    finally:
        conexion.close()

def contar_actividades_completadas(estudiante_id):
    conexion = conectar()

    try:
        resultado = conexion.execute("""
            SELECT COUNT(*) AS total
            FROM progreso
            WHERE estudiante_id = ?
              AND completado = 1
        """, (estudiante_id,)).fetchone()

        return resultado["total"]

    finally:
        conexion.close()

if __name__ == "__main__":
    crear_tablas()
    print("Tablas de RegulaT listas.")