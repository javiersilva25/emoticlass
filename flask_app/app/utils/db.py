import sqlite3
import json
from .rut import limpiar_rut, hash_password
from .roles import ROLES, is_valid_role

DB_PATH = "usuarios.db"

# -----------------------------
# Conexión
# -----------------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def _col_exists(cur, tabla, col):
    cur.execute(f"PRAGMA table_info({tabla})")
    return any(r[1] == col for r in cur.fetchall())

# -----------------------------
# Inicialización (usuarios)
# -----------------------------
def init_db():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rut TEXT UNIQUE NOT NULL,
        nombre_completo TEXT NOT NULL,
        correo TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        rol TEXT NOT NULL DEFAULT 'profesor'
    )""")

    # añadir "rol" si faltara (compatibilidad hacia atrás)
    if not _col_exists(cur, "usuarios", "rol"):
        cur.execute("ALTER TABLE usuarios ADD COLUMN rol TEXT NOT NULL DEFAULT 'profesor'")

    # admin por defecto
    cur.execute("SELECT 1 FROM usuarios WHERE rut = ?", ("123456789",))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO usuarios (rut, nombre_completo, correo, password_hash, rol)
            VALUES (?,?,?,?,?)
        """, ("123456789", "Administrador", "admin@sistema.com", hash_password("1234"), "admin"))

    conn.commit(); conn.close()

# -----------------------------
# Inicialización (dominio Emoticlass)
# -----------------------------
def init_db_dominio():
    conn = get_conn(); cur = conn.cursor()

    cur.executescript("""
    -- Configuración de cámara (última por usuario)
    CREATE TABLE IF NOT EXISTS configuracion_camara (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      usuario_id INTEGER NOT NULL,
      indice_camara INTEGER NOT NULL,
      resolucion TEXT NOT NULL,
      actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
    );

    -- Catálogo de asignaturas
    CREATE TABLE IF NOT EXISTS asignaturas (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      codigo TEXT UNIQUE NOT NULL,
      nombre TEXT NOT NULL
    );

    -- Catálogo de grados
    CREATE TABLE IF NOT EXISTS grados (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      nivel TEXT NOT NULL CHECK(nivel IN ('pre-basica','basica','media')),
      codigo TEXT NOT NULL,
      UNIQUE(nivel, codigo)
    );

    -- Configuración académica (última por usuario)
    CREATE TABLE IF NOT EXISTS configuracion_academica (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      usuario_id INTEGER NOT NULL,
      grado_id INTEGER NOT NULL,
      asignatura_id INTEGER NOT NULL,
      actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
      FOREIGN KEY(grado_id) REFERENCES grados(id),
      FOREIGN KEY(asignatura_id) REFERENCES asignaturas(id)
    );

    -- Sesión de análisis
    CREATE TABLE IF NOT EXISTS sesion_analisis (
      id TEXT PRIMARY KEY,
      usuario_id INTEGER NOT NULL,
      iniciado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      finalizado_en TIMESTAMP,
      indice_camara INTEGER,
      resolucion TEXT,
      grado_id INTEGER,
      asignatura_id INTEGER,
      FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
      FOREIGN KEY(grado_id) REFERENCES grados(id),
      FOREIGN KEY(asignatura_id) REFERENCES asignaturas(id)
    );

    -- Métrica grupal periódica
    CREATE TABLE IF NOT EXISTS metrica_grupal (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      sesion_id TEXT NOT NULL,
      ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      conteo_rostros INTEGER NOT NULL,
      emocion_predominante TEXT,
      confianza REAL,
      distribucion TEXT NOT NULL,
      carga_cognitiva REAL,
      FOREIGN KEY(sesion_id) REFERENCES sesion_analisis(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_metrica_grupal_sesion_ts
      ON metrica_grupal(sesion_id, ts);

    -- ===========================
    -- NUEVO: Profesores y Cursos
    -- ===========================
    -- Profesores (1-1 con usuario de rol 'profesor')
    CREATE TABLE IF NOT EXISTS profesores (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      usuario_id INTEGER UNIQUE NOT NULL,
      titulo TEXT,
      especialidad TEXT,
      FOREIGN KEY(usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
    );

    -- Cursos (profesor opcional; relación 1-N profesor->cursos)
    CREATE TABLE IF NOT EXISTS cursos (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      nombre TEXT NOT NULL,                -- p.ej. "3°B"
      grado_id INTEGER NOT NULL,
      asignatura_id INTEGER NOT NULL,
      profesor_id INTEGER,                 -- NULL si no asignado
      FOREIGN KEY(grado_id) REFERENCES grados(id),
      FOREIGN KEY(asignatura_id) REFERENCES asignaturas(id),
      FOREIGN KEY(profesor_id) REFERENCES profesores(id) ON DELETE SET NULL,
      UNIQUE(nombre, grado_id, asignatura_id)
    );

    CREATE INDEX IF NOT EXISTS idx_cursos_profesor ON cursos(profesor_id);
    """)

    # Semillas
    cur.executescript("""
    INSERT OR IGNORE INTO asignaturas(codigo,nombre) VALUES
      ('musica','Música'),('filosofia','Filosofía'),('matematicas','Matemáticas'),
      ('lenguaje','Lenguaje'),('quimica','Química'),('biologia','Biología'),
      ('historia','Historia'),('religion','Religión');

    INSERT OR IGNORE INTO grados(nivel,codigo) VALUES
      ('pre-basica','prekinder'), ('pre-basica','kinder'),
      ('basica','1-basico'),('basica','2-basico'),('basica','3-basico'),('basica','4-basico'),
      ('basica','5-basico'),('basica','6-basico'),('basica','7-basico'),('basica','8-basico'),
      ('media','1-medio'),('media','2-medio'),('media','3-medio'),('media','4-medio');
    """)

    conn.commit(); conn.close()

# -----------------------------
# Usuarios (helpers)
# -----------------------------
def verificar_usuario(rut, password):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT id, nombre_completo, correo, rol
        FROM usuarios
        WHERE rut=? AND password_hash=?
    """, (limpiar_rut(rut), hash_password(password)))
    row = cur.fetchone(); conn.close()
    if row:
        return {
            "id": row["id"],
            "nombre": row["nombre_completo"],
            "correo": row["correo"],
            "rol": row["rol"],
            "rut": rut
        }
    return None

def crear_usuario(rut, nombre, correo, password, rol="profesor"):
    if not is_valid_role(rol):
        return False, "Rol inválido"
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO usuarios (rut, nombre_completo, correo, password_hash, rol)
            VALUES (?,?,?,?,?)
        """, (limpiar_rut(rut), nombre, correo, hash_password(password), rol))
        conn.commit(); return True, "Usuario creado exitosamente"
    except sqlite3.IntegrityError as e:
        msg = str(e).lower()
        if 'rut' in msg: return False, "El RUT ya está registrado"
        if 'correo' in msg: return False, "El correo electrónico ya está registrado"
        return False, "Error al crear el usuario"
    except Exception as e:
        return False, f"Error inesperado: {e}"
    finally:
        conn.close()

# -----------------------------
# Catálogos
# -----------------------------
def listar_asignaturas():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("SELECT id, codigo, nombre FROM asignaturas ORDER BY nombre ASC")
    filas = [dict(r) for r in cur.fetchall()]
    conn.close(); return filas

def listar_grados_por_nivel(nivel):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT id, nivel, codigo
        FROM grados
        WHERE nivel = ?
        ORDER BY id
    """, (nivel,))
    filas = [dict(r) for r in cur.fetchall()]
    conn.close(); return filas

# -----------------------------
# Configuración de cámara (CRUD mínimo)
# -----------------------------
def guardar_configuracion_camara(usuario_id, indice_camara, resolucion):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO configuracion_camara(usuario_id, indice_camara, resolucion)
        VALUES (?,?,?)
    """, (usuario_id, indice_camara, resolucion))
    conn.commit(); conn.close(); return True

def obtener_configuracion_camara(usuario_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT id, usuario_id, indice_camara, resolucion, actualizado_en
        FROM configuracion_camara
        WHERE usuario_id = ?
        ORDER BY actualizado_en DESC, id DESC
        LIMIT 1
    """, (usuario_id,))
    row = cur.fetchone(); conn.close()
    return dict(row) if row else None

# -----------------------------
# Configuración académica (CRUD mínimo)
# -----------------------------
def guardar_configuracion_academica(usuario_id, grado_id, asignatura_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO configuracion_academica(usuario_id, grado_id, asignatura_id)
        VALUES (?,?,?)
    """, (usuario_id, grado_id, asignatura_id))
    conn.commit(); conn.close(); return True

def obtener_configuracion_academica(usuario_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT ca.id, ca.usuario_id, ca.grado_id, ca.asignatura_id, ca.actualizado_en,
               g.nivel, g.codigo AS grado_codigo,
               a.codigo AS asignatura_codigo, a.nombre AS asignatura_nombre
        FROM configuracion_academica ca
        JOIN grados g ON g.id = ca.grado_id
        JOIN asignaturas a ON a.id = ca.asignatura_id
        WHERE ca.usuario_id = ?
        ORDER BY ca.actualizado_en DESC, ca.id DESC
        LIMIT 1
    """, (usuario_id,))
    row = cur.fetchone(); conn.close()
    return dict(row) if row else None

# -----------------------------
# Sesiones de análisis
# -----------------------------
def iniciar_sesion_analisis(usuario_id, indice_camara=None, resolucion=None, grado_id=None, asignatura_id=None):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO sesion_analisis(usuario_id, indice_camara, resolucion, grado_id, asignatura_id)
        VALUES (?,?,?,?,?)
    """, (usuario_id, indice_camara, resolucion, grado_id, asignatura_id))
    # recuperar id (TEXT uuid-like esperado en esquema original)
    cur.execute("SELECT id FROM sesion_analisis ORDER BY rowid DESC LIMIT 1")
    sid = cur.fetchone()["id"]
    conn.commit(); conn.close()
    return sid

def finalizar_sesion_analisis(sesion_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        UPDATE sesion_analisis
        SET finalizado_en = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (sesion_id,))
    conn.commit(); conn.close()
    return True

# -----------------------------
# Métrica grupal (ticks)
# -----------------------------
def agregar_metrica_grupal(sesion_id, conteo_rostros, emocion_predominante, confianza, distribucion_dict, carga_cognitiva):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO metrica_grupal (sesion_id, conteo_rostros, emocion_predominante, confianza, distribucion, carga_cognitiva)
        VALUES (?,?,?,?,?,?)
    """, (sesion_id, conteo_rostros, emocion_predominante, float(confianza) if confianza is not None else None,
          json.dumps(distribucion_dict or {}), float(carga_cognitiva) if carga_cognitiva is not None else None))
    conn.commit(); conn.close()
    return True

def obtener_metricas_por_sesion(sesion_id, limite=500):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT id, ts, conteo_rostros, emocion_predominante, confianza, distribucion, carga_cognitiva
        FROM metrica_grupal
        WHERE sesion_id = ?
        ORDER BY ts ASC
        LIMIT ?
    """, (sesion_id, limite))
    filas = []
    for r in cur.fetchall():
        d = dict(r)
        try:
            d["distribucion"] = json.loads(d.get("distribucion") or "{}")
        except Exception:
            d["distribucion"] = {}
        filas.append(d)
    conn.close(); return filas

# -----------------------------
# Profesores (CRUD mínimo)
# -----------------------------
def crear_profesor(usuario_id, titulo=None, especialidad=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id, rol FROM usuarios WHERE id = ?", (usuario_id,))
        u = cur.fetchone()
        if not u:
            conn.close(); return False, "Usuario no existe"
        if u["rol"] != "profesor":
            conn.close(); return False, "El usuario no tiene rol 'profesor'"

        cur.execute("""
            INSERT INTO profesores (usuario_id, titulo, especialidad)
            VALUES (?,?,?)
        """, (usuario_id, titulo, especialidad))
        conn.commit(); conn.close()
        return True, "Profesor creado"
    except sqlite3.IntegrityError as e:
        conn.close()
        if "UNIQUE constraint failed: profesores.usuario_id" in str(e):
            return False, "Ya existe un profesor para este usuario"
        return False, "Error de integridad al crear profesor"
    except Exception as e:
        conn.close(); return False, f"Error inesperado: {e}"

def listar_profesores():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT p.id AS profesor_id, u.id AS usuario_id, u.rut, u.nombre_completo, u.correo,
               p.titulo, p.especialidad
        FROM profesores p
        JOIN usuarios u ON u.id = p.usuario_id
        ORDER BY u.nombre_completo ASC
    """)
    filas = [dict(r) for r in cur.fetchall()]
    conn.close(); return filas

def obtener_profesor_por_usuario(usuario_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT p.id AS profesor_id, p.usuario_id, p.titulo, p.especialidad
        FROM profesores p
        WHERE p.usuario_id = ?
        LIMIT 1
    """, (usuario_id,))
    row = cur.fetchone(); conn.close()
    return dict(row) if row else None

# -----------------------------
# Cursos (CRUD mínimo)
# -----------------------------
def crear_curso(nombre, grado_id, asignatura_id, profesor_id=None):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM grados WHERE id=?", (grado_id,))
        if not cur.fetchone():
            conn.close(); return False, "Grado no existe"
        cur.execute("SELECT id FROM asignaturas WHERE id=?", (asignatura_id,))
        if not cur.fetchone():
            conn.close(); return False, "Asignatura no existe"

        if profesor_id is not None:
            cur.execute("SELECT id FROM profesores WHERE id=?", (profesor_id,))
            if not cur.fetchone():
                conn.close(); return False, "Profesor no existe"

        cur.execute("""
            INSERT INTO cursos (nombre, grado_id, asignatura_id, profesor_id)
            VALUES (?,?,?,?)
        """, (nombre, grado_id, asignatura_id, profesor_id))
        conn.commit(); conn.close()
        return True, "Curso creado"
    except sqlite3.IntegrityError as e:
        conn.close()
        if "UNIQUE constraint failed: cursos.nombre, cursos.grado_id, cursos.asignatura_id" in str(e):
            return False, "Ya existe un curso con ese nombre/grado/asignatura"
        return False, "Error de integridad al crear curso"
    except Exception as e:
        conn.close(); return False, f"Error inesperado: {e}"

def listar_cursos():
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT c.id, c.nombre,
               g.id AS grado_id, g.nivel, g.codigo AS grado_codigo,
               a.id AS asignatura_id, a.codigo AS asignatura_codigo, a.nombre AS asignatura_nombre,
               c.profesor_id,
               u.nombre_completo AS profesor_nombre, u.correo AS profesor_correo
        FROM cursos c
        JOIN grados g ON g.id = c.grado_id
        JOIN asignaturas a ON a.id = c.asignatura_id
        LEFT JOIN profesores p ON p.id = c.profesor_id
        LEFT JOIN usuarios u ON u.id = p.usuario_id
        ORDER BY c.id DESC
    """)
    filas = [dict(r) for r in cur.fetchall()]
    conn.close(); return filas

def listar_cursos_por_profesor(profesor_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        SELECT c.id, c.nombre,
               g.nivel, g.codigo AS grado_codigo,
               a.codigo AS asignatura_codigo, a.nombre AS asignatura_nombre
        FROM cursos c
        JOIN grados g ON g.id = c.grado_id
        JOIN asignaturas a ON a.id = c.asignatura_id
        WHERE c.profesor_id = ?
        ORDER BY c.id DESC
    """, (profesor_id,))
    filas = [dict(r) for r in cur.fetchall()]
    conn.close(); return filas

def asignar_profesor_a_curso(curso_id, profesor_id):
    conn = get_conn(); cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM cursos WHERE id=?", (curso_id,))
        if not cur.fetchone():
            conn.close(); return False, "Curso no existe"
        cur.execute("SELECT id FROM profesores WHERE id=?", (profesor_id,))
        if not cur.fetchone():
            conn.close(); return False, "Profesor no existe"
        cur.execute("UPDATE cursos SET profesor_id = ? WHERE id = ?", (profesor_id, curso_id))
        conn.commit(); conn.close()
        return True, "Profesor asignado al curso"
    except Exception as e:
        conn.close(); return False, f"Error inesperado: {e}"

def eliminar_curso(curso_id):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("DELETE FROM cursos WHERE id = ?", (curso_id,))
    cambios = cur.rowcount
    conn.commit(); conn.close()
    return cambios > 0
