import psycopg2
import os

def get_connection():
    return psycopg2.connect(
        host="db.nubcevnyvltdmnwwwprh.supabase.co",
        port=5432,
        database="postgres",
        user="postgres",
        password="TU_PASSWORD_AQUI"
    )