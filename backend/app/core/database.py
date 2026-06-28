from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

#Obtener la configuración global cargada desde el .env
settings = get_settings()

#Encargado de administrar el pool de conexiones hacia PostgreSQL. 
engine = create_engine(
    settings.DATABASE_URL,
    #Verificar si la conexion sigue viva antes de usarla
    pool_pre_ping=True,
    #Usar el modo de compatibilidad con la nueva API de SQLAlchemy 2.0
    future=True,
)

#Cada vez que se llame, creará una nueva conexión limpia a la base de datos
SessionLocal = sessionmaker(
    bind=engine,
    #Evitar que los cambios se confirmen automáticamente
    autocommit=False,
    #Evitar que los cambios se sincronicen automáticamente con la base de datos
    autoflush=False,
    future=True,
)


def check_database_connection() -> bool:
    """ 
    Realiza una consula ultraligera a PostgreSQL para confirmar que el 
    servicio está levantado y aceptando conexiones. 
    """
    #Garantizar que la conexión se cierre automáticamente al terminar el bloque
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return True