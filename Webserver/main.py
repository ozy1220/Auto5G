from cgitb import reset
from distutils.filelist import translate_pattern
from fastapi import FastAPI, Response, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.encoders import jsonable_encoder
import uvicorn
import asyncio
import aiofiles
import datetime
import uuid
import random
import time
from starlette.responses import RedirectResponse
from coord import coordenadas
import auxiliares
from auxiliares import SIN_CONEXION, carros, cx_seccion, cy_calle, ang_calle
import math
import timeit
import logging



# -------- Inicia codigo para SSE
from sse_starlette.sse import EventSourceResponse
# -------- Fin codigo para SSE

app = FastAPI()
#del 0-2 van a ser los sensores de el frente
#del 3-5 van a ser los sensores traseros

qPosiciones = asyncio.Queue(maxsize = 5000)

# ---------- Termina codigo para SSE
STREAM_DELAY = 1  # second
RETRY_TIMEOUT = 15000  # milisecond


# ------------  AUXILIARES

def actualizaEstadoCarro(carro):
    estado = auxiliares.validaEstadoCarro(carro)
    if estado != auxiliares.carros[carro].estatus_conexion:
        # Genera estado conexion
        auxiliares.carros[carro].estatus_conexion = estado
        qobj = {
            'tipo': 'connect',
            'carro': carro,
            'status': carros[carro].ocupado,
            'conexion': estado
        }
        qPosiciones.put_nowait(qobj)


def validaCarros():
    actualizaEstadoCarro('Rojo')
    actualizaEstadoCarro('Verde')
    actualizaEstadoCarro('Azul')

# ------------  FIN AUXILIARES



@app.get('/stream')
async def message_stream(request: Request):
    async def event_generator():
        while True:
            # If client closes connection, stop sending events
            if await request.is_disconnected():
                break

            # Checks for new messages and return them to client if any
            try:
                qobj = await asyncio.wait_for(qPosiciones.get(), 300)
            except:
                # Si no hubo eventos, no mandes nada.
                continue

            print(qobj)
            color = qobj['carro']
            tipo = qobj['tipo']

            if tipo == 'message':
                front = qobj['front']
                back = qobj['back']
                coordx = int(qobj['coordx'])
                coordy = int(qobj['coordy'])
                rad = qobj['rad'] 
                datastr = '{"color": "' + color + '", "front": ' + str(front) + ', "back": ' + str(back) + ', "coordx": ' + str(coordx) +', "coordy": ' + str(coordy) +', "rad": ' + str(rad) + '}'
            elif tipo == 'connect':
                status = qobj['status']
                conexion = qobj['conexion']
                datastr = '{"color": "' + color + '", "status": ' + status + ', "conexion": ' + str(conexion) + '}'
            
            eobj = {
                    'event': tipo,
                    'id': 'message_id',
                    'retry': RETRY_TIMEOUT,
                    'data': datastr
            }
            yield eobj

    return EventSourceResponse(event_generator())
# ---------- Fin codigo para SSE


@app.get("/", response_class=HTMLResponse)
async def root():

    if carros['Rojo'].ocupado == 'true': linkRojo = '#'
    else: linkRojo = '/control/Rojo'
    if carros['Azul'].ocupado == 'true': linkAzul = '#'
    else: linkAzul = '/control/Azul'
    if carros['Verde'].ocupado == 'true': linkVerde = '#'
    else: linkVerde = '/control/Verde'

    async with aiofiles.open("./archivosHTML/inicio.html", mode="r") as f:
        html = await f.read()

    html = html.format(ocupadoRojo = carros['Rojo'].ocupado, 
                       ocupadoAzul = carros['Azul'].ocupado,
                       ocupadoVerde = carros['Verde'].ocupado,
                       linkRojo = linkRojo,
                       linkAzul = linkAzul,
                       linkVerde = linkVerde)
    return HTMLResponse(content=html, status_code=200)


@app.get("/admin", response_class=HTMLResponse)
async def pagAdmin():
    async with aiofiles.open('./archivosHTML/principal.html', mode='r') as f:
    # f = open("./archivosHTML/principal.html", "r")
        html = await f.read()

    return HTMLResponse(content=html, status_code=200)


@app.get("/avanzaMotores/{carro}")
async def _avanza(carro):

    logging.warning(f'{time.time()} - Se recibio peticion /avanzaMotores/{carro}')

    # seccion de heartbeats
    auxiliares.heartbeatMotores(carro)
    validaCarros()

    try:
        if carros[carro].queue.empty() and carros[carro].dirControl != auxiliares.DIR_PARA and carros[carro].dirControl != carros[carro].ultDir:
            logging.warning(f'{time.time()} - Mandando comando ficticio por cola vacia y control apretado {carros[carro].dirControl}')
            carros[carro].ultDir = carros[carro].dirControl
            res = carros[carro].dirControl
        else:
            res = await asyncio.wait_for(auxiliares.carros[carro].queue.get(), timeout = 5.0)
            auxiliares.carros[carro].dire = res
            auxiliares.carros[carro].queue.task_done()
        
        dir_nueva = auxiliares.overrideDireccion(carro, res)
        logging.warning(f'{time.time()} Res /avanzaMotores/{carro} :  res = {res}, dir_final = {dir_nueva}')
        carros[carro].ultDir = dir_nueva
        if dir_nueva not in auxiliares.direccionesAjuste:
            carros[carro].ajustesSeguidos = 0

        logging.warning(f'{time.time()} - Se envia respuesta para /avanzaMotores/{carro}: {dir_nueva}')
        return Response(content = str(dir_nueva), media_type = "text/plain") 

    except asyncio.TimeoutError:
        auxiliares.carros[carro].dire = 'V'
        logging.warning(f'{time.time()} - Timeout para /avanzaMotores/{carro}: V')
        return Response(content=str('V'), media_type="text/plain")


@app.get("/control/{carro}", response_class=HTMLResponse)
async def _carrito(carro):
    x = str(uuid.uuid4())
    carros[carro].llave = x
    carros[carro].ocupado = 'true'
    qobj = {
        'tipo': 'connect',
        'carro': carro,
        'status': 'true',
        'conexion': carros[carro].estatus_conexion
    }
    qPosiciones.put_nowait(qobj)
    while not carros[carro].queue.empty(): 
        carros[carro].queue.get_nowait()
        carros[carro].queue.task_done()

    carros[carro].seccion_f = -1
    carros[carro].seccion_a = -1
    carros[carro].sentido = auxiliares.LIMBO
    auxiliares.eliminaProhibidos(carro)

    async with aiofiles.open("./archivosHTML/control.html", mode="r") as f:
        html = await f.read()
    html = html.format(carro = carro,
                       hash = x)
    return HTMLResponse(content = html, status_code=200)


@app.get("/desconecta/{carro}")
async def _desconecta(carro, status_code = 200):
    carros[carro].ocupado = 'false'
    carros[carro].llave = str(uuid.uuid4())
    qobj = {
        'tipo': 'connect',
        'carro': carro,
        'status': 'false',
        'conexion': carros[carro].estatus_conexion
    }
    qPosiciones.put_nowait(qobj)
    
    return RedirectResponse(url="/",status_code=302)


@app.get("/direccion/{param_dir}/{carro}/{hash}")
async def direccion(response: Response, param_dir, carro, hash):
    response.headers["access-control-allow-origin"] = "*"

    if (hash != 'admin' and hash != auxiliares.carros[carro].llave): 
        return "Error(no eres quien lo controla)"
    else:
        carros[carro].dirControl = param_dir
        if not auxiliares.carros[carro].queue.full():
            auxiliares.carros[carro].queue.put_nowait(param_dir)
            print(f'{time.time()} Enviando a cola de carro {carro} direccion {param_dir}')
            return 'OK'
        else:
            logging.warning(f'La cola de instrucciones del carro {carro} esta llena')

@app.get("/img/{archivo}", response_class=FileResponse)
async def _sirvearchivo(archivo):
    return FileResponse(f"./img/{archivo}")


@app.get("/posicion/{carro}/{front}/{back}")
async def _posicion(carro,front,back):
    # logging
    logging.warning(f'{time.time()} - Posicion {carro}. Frente de {carros[carro].frente} -> {front}. Atras de {carros[carro].atras} -> {back}')

    # seccion de heartbeats
    auxiliares.heartbeatPosicion(carro)
    validaCarros()

    dirControl = carros[carro].dirControl
    calle = carros[carro].calle
    carril = carros[carro].ultcarril
    columna = carros[carro].ultcol

    # Toma la decision dependiendo de si vas avanzando hacia adelante o atras
    dirNueva = ""
    if dirControl in auxiliares.direccionesFrente:
        # El coche va al frente, fijate en el lector del frente unicamente
        try:
            if carros[carro].frente != front:
                carril = int(coordenadas[int(front)]['carril'])
                columna = int(coordenadas[int(front)]['col'])
            else:
                carril = int(coordenadas[int(back)]['carril'])
        except:
            carril = 3
        logging.warning(f'{time.time()} Se leyo sticker frontal {front} que se consdiera del carril {carril}')
        if carril == 5:
            # El carril 5 siempre cierra al centro
            dirNueva = auxiliares.DIR_FL
        elif carril == 4 and carros[carro].ultcarril != 5:
            # El carril 4 gira a menos que venga del 5, lo cual significa que ya esta cerrando 
            dirNueva = auxiliares.DIR_FL
        elif carril == 3 and columna != carros[carro].ultcol:
            # El giro del 3 debe ser para compensar adecuaciones, si viene de la parte de abajo, de arriba o del centro
            if carros[carro].ultcarril > 3:
                dirNueva = auxiliares.DIR_FR
            elif carros[carro].ultcarril < 3:
                dirNueva = auxiliares.DIR_FL
        elif carril == 2 and carros[carro].ultcarril != 1:
            # El carril 2 gira a menos que venga del 1 en cuyo caso no hay que aumentar la compensacion
            dirNueva = auxiliares.DIR_FR
        elif carril == 1:
            # El carril 1 gira siempre
            dirNueva = auxiliares.DIR_FR            
    elif dirControl in auxiliares.direccionesAtras and carros[carro].atras != back:
        # El coche va hacia atras, los giros son inversos a cuando va al frente
        try:
            if carros[carro].atras != back:
                carril = int(coordenadas[int(back)]['carril'])
                columna = int(coordenadas[int(back)]['col'])
            else:
                carril = int(coordenadas[int(front)]['carril'])
        except:
            carril = 3
        logging.warning(f'{time.time()} Se leyo sticker trasero {back} que se consdiera del carril {carril}')
        if carril == 5:
            dirNueva = auxiliares.DIR_BL
        elif carril == 4 and carros[carro].ultcarril != 5:
            dirNueva = auxiliares.DIR_BL
        elif carril == 3 and columna != carros[carro].ultcol:
            if carros[carro].ultcarril > 3:
                dirNueva = auxiliares.DIR_BR
            elif carros[carro].ultcarril < 3:
                dirNueva = auxiliares.DIR_BL
        elif carril == 2 and carros[carro].ultcarril != 1:
            dirNueva = auxiliares.DIR_BR
        elif carril == 1:
            dirNueva = auxiliares.DIR_BR            
    
    # Actualiza los valores del carro
    carros[carro].ultcarril = carril
    carros[carro].frente = front
    carros[carro].atras = back
    carros[carro].ultcol = columna

    # Si hay una direccion nueva, insertala en la cola
    if dirNueva != "":
        # saca los comandos que haya de mas en la cola
        while carros[carro].queue.full():
            eliminada = carros[carro].queue.get_nowait()
            logging.warning(f'Se elimino comando de la cola de {carro} por saturacion: {eliminada}')
            carros[carro].queue.task_done()
        
        # Envia el nuevo comando a menos que exceda el numero de ajustes seguidos
        if dirNueva in auxiliares.direccionesAjuste and carros[carro].ajustesSeguidos < auxiliares.MAX_AJUSTES:
            carros[carro].queue.put_nowait(dirNueva)
            carros[carro].ajustesSeguidos += 1
        else:
            logging.warning(f'Eliminando ajuste por exceso de ajustes consecutivos')
    else:
        dirNueva = auxiliares.overrideDireccion(carro, dirControl)
        if dirNueva != dirControl:
            logging.warning(f'Insertando comando ficticio por prohibicion de pista {dirControl}, {dirNueva}')
            carros[carro].queue.put_nowait(dirNueva)

    # Determina la seccion en la que esta el auto
    if calle <= 3:
        # Es una calle horizontal
        if (calle & 1) == 0:
            # Es una calle con sentido OESTE
            if dirControl not in auxiliares.direccionesAtras: 
                seccion_f = coordenadas[int(front)]['seccion_a']
                seccion_b = coordenadas[int(back)]['seccion_a']
            else: 
                seccion_f = coordenadas[int(front)]['seccion_b']
                seccion_b = coordenadas[int(back)]['seccion_b']

        else:
            # Es calle con sentido ESTE
            if dirControl not in auxiliares.direccionesAtras:
                seccion_f = coordenadas[int(front)]['seccion_b']
                seccion_b = coordenadas[int(back)]['seccion_b']
            else:
                seccion_f = coordenadas[int(front)]['seccion_a']
                seccion_b = coordenadas[int(back)]['seccion_a']

    logging.error(f'Se calculo nueva seccion para carro {carro}. Calle = {calle}, seccion f = {seccion_f}, seccion b = {seccion_b}')

    carros[carro].seccion_f = seccion_f
    carros[carro].seccion_a = seccion_b

    # Envia la nueva posicion para la interfaz grafica
    qobj = {
        'tipo': 'message',
        'carro': carro,
        'front': seccion_f,
        'back': seccion_b,
        'calle': carros[carro].calle,
        'coordx': cx_seccion[int((seccion_f + seccion_b) / 2)],
        'coordy': cy_calle[calle],
        'rad': ang_calle[calle]
    }
    qPosiciones.put_nowait(qobj)

    return "Acabe posicion"


@app.get("/velocidad/{carro}")
async def velocidad(carro):
    st = auxiliares.vel['vh'] + auxiliares.vel['vl'] + auxiliares.vel['vn']
    return Response(content=st, media_type="text/plain")


if __name__ == '__main__':
    logging.basicConfig(filename = "logfile.log", level = logging.DEBUG)
    uvicorn.run(app, host='0.0.0.0', port='8080')