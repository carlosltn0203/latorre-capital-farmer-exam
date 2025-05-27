from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime
import uuid
import os
import openai
from dotenv import load_dotenv
import re

#cargar API Key 

load_dotenv()
client = api_key=os.getenv("OPENAI_API_KEY")

def analizar_con_ia(descripcion, tipo_servicio):
    prompt=f"""
    Analiza el siguiente caso legal: 

        Tipo de servicio: {tipo_servicio}
    Descripción: {descripcion}

    Evalúa:
    1. Nivel de complejidad (Baja, Media o Alta)
    2. Recomendación de ajuste de precio (0%, 25% o 50%)
    3. Servicios adicionales sugeridos si aplica
    4. Propuesta profesional (2-3 párrafos, tono formal)
    """

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # o "gpt-4" si tienes acceso
        messages=[{"role": "user", "content": prompt}]
    )

    texto_respuesta = response.choices[0].message.content

    # Puedes usar una técnica simple de extracción (mejor usar JSON si puedes formatear la respuesta en el prompt)
    return {
        'complejidad': extraer_valor(texto_respuesta, "Complejidad"),
        'ajuste_precio': extraer_valor(texto_respuesta, "Ajuste"),
        'servicios_adicionales': extraer_valor(texto_respuesta, "Servicios adicionales"),
        'propuesta_texto': texto_respuesta
    }

def extraer_valor(texto, campo):
    for linea in texto.split('\n'):
        if campo.lower() in linea.lower():
            return linea.split(':',1)[-1].strip()
    return  ""

def extraer_numero(ajuste_str):
    match=re.match(r"(\d+)", ajuste_str)
    if match:
        return int (match.group(1))
    else:
        raise ValueError("No se encontro un numero valido")


def iniciar_bd():
    conn= sqlite3.connect("base.bd")
    cursor= conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_cotizacion TEXT,
        nombre TEXT,
        email TEXT,
        servicio TEXT,
        precio REAL,
        fecha TEXT
    )'''
    )
    conn.commit()
    conn.close()

app=Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True


PRECIOS = {
    "Constitución de empresa" : 1500.00,
    "Defensa Laboral" : 2000.00,
    "Consultoría tributaria" : 800.00
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cotizar', methods=['POST'])
def cotizar():
    nombre = request.form['nombre']
    email = request.form['email']
    servicio = request.form['servicio']
    descripcion = request.form['descripcion']

    precio = PRECIOS.get(servicio, 0)
    fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    numero =f"COT-2025-{str(uuid.uuid4())[:8].upper()}"

    #llamar a la ia

    resultado_ia=analizar_con_ia(descripcion,servicio)
    ajuste= resultado_ia['ajuste_precio']

    #Ajuste precio
    if isinstance(ajuste, str) and '%' in ajuste:
        ajuste= extraer_numero(ajuste.replace('%', '').strip())
    precio_final=precio * (1+ajuste/100)

    #Guardar en la base de datos

    conn = sqlite3.connect("base.bd")
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO usuarios (numero_cotizacion, nombre, email, servicio, precio, fecha)
    VALUES(?,?,?,?,?,?)''', (numero, nombre, email, servicio, precio, fecha))
    conn.commit()
    conn.close()



    return jsonify({
        "numero_cotizacion" : numero,
        "nombre": nombre,
        "email" : email, 
        "servicio" :servicio,
        "precio" : f"S/ {precio:.2f}",
        "fecha" : fecha,
        "descripcion" : descripcion,
        "complejidad": resultado_ia['complejidad'],
        "ajuste_precio": f"{ajuste}%",
        "servicios_adicionales": resultado_ia['servicios_adicionales'],
        "propuesta_texto": resultado_ia['propuesta_texto'],
        "precion_final": precio_final
    })

if __name__ == '__main__':
    iniciar_bd()
    app.run(debug=True)


