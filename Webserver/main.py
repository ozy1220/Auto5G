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
from auxiliares import SIN_CONEXION, Bloque, carros, cx_seccion, cy_calle, ang_calle
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
            if not carros[carro].queue.empty():
                res = carros[carro].queue.get_nowait()
            else:
                res = await asyncio.wait_for(carros[carro].queue.get(), timeout=5)
            carros[carro].dire = res
            carros[carro].queue.task_done()
        
        dir_nueva = auxiliares.overrideDireccion(carro, res)
        logging.warning(f'{time.time()} Res /avanzaMotores {carro} :  res = {res}, dir_final = {dir_nueva}')
        carros[carro].ultDir = dir_nueva
        if dir_nueva not in auxiliares.direccionesAjuste:
            carros[carro].ajustesSeguidos = 0

        respuesta=str(dir_nueva) 

    except asyncio.TimeoutError:
        auxiliares.carros[carro].dire = 'V'
        logging.warning(f'{time.time()} - Timeout para /avanzaMotores/{carro}: V')
        respuesta='V'
        
    if respuesta == 'V': code = 200
    elif respuesta == 'N': code = 201
    elif respuesta == 'S': code = 202
    elif respuesta == 'E': code = 203
    elif respuesta == 'O': code = 204
    elif respuesta == 'W': code = 205
    elif respuesta == 'X': code = 206
    elif respuesta == 'Y': code = 207
    elif respuesta == 'Z': code = 208
    return Response(status_code=code)


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
            logging.warning(f'{time.time()} Se agrego direccion {param_dir} a la cola del carro {carro}')
            return 'OK'
        else:
            logging.warning(f'{time.time()} La cola de instrucciones del carro {carro} esta llena')

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

    calle = 2

    dirControl = carros[carro].dirControl
    filf = coordenadas[front]['y']
    colf = coordenadas[front]['x']
    filb = coordenadas[back]['y']
    colb = coordenadas[back]['x']

    # Calcula la orientacion y la calle del carro
    if colf == colb:
        if filf > filb: ang = math.pi / 2
        else: ang = math.pi * 3 / 2
    else:
        pend = (filf - filb) / (colf - colb)
        ang = math.atan(pend)
        
        # Python regresa el angulo entre 90 y 270 grados, asi que hay que ver si el carro iba o venia sobre esa pendiente
        if ang == 0 and colf < colb: ang += math.pi
        elif ang < 0 and (filf - filb) > 0: ang += math.pi
        elif ang > 0 and (filf - filb) < 0: ang += math.pi
    
    if ang < 0:
        ang += 2.0 * math.pi

    if ang >= math.pi * 7 / 4.0 or ang < math.pi / 4.0:
        dirBrujula = 0
    elif ang >= math.pi / 4.0 and ang < math.pi * 3.0 / 4.0:
        dirBrujula = 90
    elif ang >= math.pi * 3.0 / 4.0 and ang < math.pi * 5.0 / 4.0:
        dirBrujula = 180
    else:
        dirBrujula = 270
    logging.warning(f'{time.time()} - Se calculo angulo {ang}, brujula {dirBrujula}, xf {colf}, yf {filf}, xb {colb}, yb {filb}')

    # Ubica en que calle esta y en base a eso decide los carriles
    chf = coordenadas[front]['ch']
    cvf = coordenadas[front]['cv']
    chb = coordenadas[back]['ch']
    cvb = coordenadas[back]['cv']

    if cvf == 0 and cvb == 0:
        carrilf = (int(chf)-1)%7
        carrilb = (int(chb)-1)%7
    elif chf == 0 and chb == 0:
        carrilf = (int(cvf)-1)%7
        carrilb = (int(cvb)-1)%7
    else:
        dfil = abs(filf - filb)
        dcol = abs(colf - colb)
        if dfil > dcol:
            carrilf = (int(cvf)-1)%7
            carrilb = (int(cvb)-1)%7
        else: 
            carrilf = (int(chf)-1)%7
            carrilb = (int(chb)-1)%7             
    


    # Seccion de detonados por posicion
    dirNueva = ""
    limpiaCola = False

    # Revisa si es necesario detener el auto porque va a salir de la pista
    if dirNueva == "" and dirControl in auxiliares.direccionesFrente:
        if (dirBrujula == 0 and colf > 2100) or (dirBrujula == 90 and filf > 1000) or (dirBrujula == 180 and colf < 150) or (dirBrujula == 270 and filf < 150):
            dirNueva = auxiliares.DIR_PARA
            limpiaCola = True
    elif dirNueva == "" and dirControl in auxiliares.direccionesAtras:            
        if (dirBrujula == 180 and colb > 2100) or (dirBrujula == 270 and filb > 1000) or (dirBrujula == 0 and colb < 150) or (dirBrujula == 90 and filb < 150):
            dirNueva = auxiliares.DIR_PARA
            limpiaCola = True
    if dirNueva != "":
        logging.warning(f'{time.time()} - Ajustando comando por limite de pista.  Nueva dir {dirNueva}')

    # Revisa si debe detenerse por semaforo
    if dirNueva == "" and dirControl in auxiliares.direccionesFrente:
        if (dirBrujula == 0 and colf > 2100) or (dirBrujula == 90 and filf > 1000) or (dirBrujula == 180 and colf < 150) or (dirBrujula == 270 and filf < 150):
            dirNueva = auxiliares.DIR_PARA
            limpiaCola = True
    elif dirNueva == "" and dirControl in auxiliares.direccionesAtras:            
        if (dirBrujula == 180 and colb > 2100) or (dirBrujula == 270 and filb > 1000) or (dirBrujula == 0 and colb < 150) or (dirBrujula == 90 and filb < 150):
            dirNueva = auxiliares.DIR_PARA
            limpiaCola = True
    if dirNueva != "":
        logging.warning(f'{time.time()} - Ajustando comando por limite de pista.  Nueva dir {dirNueva}')



    # Revisa si debe detenerse por que haya un coche delante
        

    # Decide si es necesario ajustar para centrar en el carril
    if dirNueva == "" and dirControl in auxiliares.direccionesFrente:

        if carrilf == 0: 
            # El carril 0 siempre cierra al centro
            dirNueva = auxiliares.DIR_FL
        elif carrilf == 6:
            dirNueva = auxiliares.DIR_FR
        elif carrilf == 1:
            if (carrilb >= 1): dirNueva = auxiliares.DIR_FL
        elif carrilf == 5: 
            if (carrilb <= 5): dirNueva = auxiliares.DIR_FR
        elif carrilf > 3 and carrilb < 3:
            dirNueva = auxiliares.DIR_FR
        elif carrilf < 3 and carrilb > 3:
            dirNueva = auxiliares.DIR_FL

    elif dirControl in auxiliares.direccionesAtras:
        if carrilb == 0: 
            # El carril 0 siempre cierra al centro
            dirNueva = auxiliares.DIR_BL
        elif carrilb == 6:
            dirNueva = auxiliares.DIR_BR
        elif carrilb == 1:
            if (carrilf >= 1): dirNueva = auxiliares.DIR_BL
        elif carrilb == 5: 
            if (carrilf <= 5): dirNueva = auxiliares.DIR_BR
        elif carrilb > 3 and carrilf < 3:
            dirNueva = auxiliares.DIR_BR
        elif carrilb < 3 and carrilf > 3:
            dirNueva = auxiliares.DIR_BL            
    
    logging.warning(f'Se proceso posicion. Carril F {carrilf}, Carril B {carrilb}, Dir nueva {dirNueva}, Dir control {dirControl}')

    # Actualiza los valores del carro
    carros[carro].yf = filf
    carros[carro].xf = colf
    carros[carro].ya = filb
    carros[carro].xa = colb
    carros[carro].calle = calle
    carros[carro].dirBrujula = dirBrujula

    # Si hay una direccion nueva, insertala en la cola
    if dirNueva != "":
        # Si habia que limpiar la cola, elimina todos los mensajes
        if limpiaCola:
            while not carros[carro].queue.empty():
                carros[carro].queue.get_nowait()
                carros[carro].queue.task_done()

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

    # Envia la nueva posicion para la interfaz grafica
    qobj = {
        'tipo': 'message',
        'carro': carro,
        'front': front,
        'back': back,
        'calle': carros[carro].calle,
        'coordy': int((filf + filb) / 2),
        'coordx': int((colf + colb) / 2),
        'rad': ang
    }
    qPosiciones.put_nowait(qobj)

    return "Acabe posicion"


@app.get("/velocidad/{carro}")
async def velocidad(carro):
    st = auxiliares.vel['vh'] + auxiliares.vel['vl'] + auxiliares.vel['vn'] + '$'
    return Response(content=st, media_type="text/plain")

@app.get("/updatezona/{bloque}/{estado}")
async def _updatezona(bloque,estado):
    #lo manda como int o string
    bloques[bloque].estado = estado
    return "ok"

if __name__ == '__main__':
    logging.basicConfig(filename = "logfile.log", level = logging.WARNING)
    uvicorn.run(app, host='0.0.0.0', port='8080', timeout_keep_alive = 60)