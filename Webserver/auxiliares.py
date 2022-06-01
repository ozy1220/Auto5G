import asyncio
from cmath import sqrt
from curses import def_shell_mode
from dis import dis
from faulthandler import cancel_dump_traceback_later
import math
from operator import truediv
from ssl import DER_cert_to_PEM_cert
import time

from pydantic import TupleError
from coord import coordenadas
import logging

DIR_PARA = 'V'
DIR_F = 'N'
DIR_B = 'S'
DIR_R = 'E'
DIR_L = 'O'
DIR_FL = 'W'
DIR_BL = 'X'
DIR_BR = 'Y'
DIR_FR = 'Z'
VEL_LOW = 'D'
VEL_HIGH = 'U'

#Distancias para checarse entre carros y ver si chocan o no
DIS_DETEC = 240
DIS_PARALELA = 180

direcciones = [DIR_PARA, DIR_F, DIR_B, DIR_R, DIR_L, DIR_FL, DIR_BL, DIR_BR, DIR_FR]
direccionesFrente = [DIR_F, DIR_FL, DIR_FR]
direccionesAtras = [DIR_B, DIR_BL, DIR_BR]
direccionesAjuste = [DIR_FL, DIR_BL, DIR_FR, DIR_BR]

MAX_AJUSTES = 3

SIN_CONEXION = 0
CONECTADO_MOTORES = 1
CONECTADO_POSICION = 2
CONECTADO_LISTO = 3

NORTE = 0
ESTE = 1
SUR = 2
OESTE = 3
LIMBO = 4

brujulaHorizontal = [ESTE, OESTE]
brujulaVertical = [NORTE, SUR]

cy_calle = [12, 48, 72, 108]
ang_calle = [math.pi, 0, math.pi, 0]
cx_seccion = [0, 7, 14, 21, 29, 36, 43, 50, 57, 64, 71, 79, 86, 93, 100, 107, 114, 121, 129, 136, 143, 150, 157, 165, 171, 179, 186, 193, 200, 210]

#variables de programacion
numcarros = ['Azul','Verde','Rojo']

class Carro:
    def __init__(self):
        self.frente = -1            # Ultimo tag leido por el lector frontal
        self.atras = -1             # Ultimo tag leido por el lector posterior
        self.dirControl = 'V'       # Direccion apretada actualmente en el control
        self.ultDir = 'V'           # Ultima direccion que se ha enviado al carro
        self.llave = ''             # Hash de control
        self.ocupado = 'false'      # Indicador de si el auto esta ocupado o no
        self.xf = 0                 # Coordenada X del lector frontal obtenida del ultimo tag leido
        self.yf = 0                 # Coordenada Y del lector frontal
        self.xa = 0                 # Coordenada X del lector posterior
        self.ya = 0                 # Coordenada Y del lector posterior
        self.x = 0                  # Coordenada X estimada del centro del carro
        self.y = 0                  # Coordenada Y estimada del centro del carro
        self.angulo = 0             # Angulo en radianes del auto
        self.queue = asyncio.Queue(maxsize=8) # Cola de comandos del auto
        self.estatus_conexion = SIN_CONEXION
        self.dirBrujula = 0         # Direccion gruesa de brújula del auto N, S, E, O
        self.velocidad = 0          # Velocidad actual del auto
        self.ultCarril = 3          # Ultimo carril de la calle por la que paso el auto
        self.ajustesSeguidos = 0    # Numero de ajustes seguido
        self.ultQueue = DIR_PARA    # El ultimo comando que se inserto en la cola

class Bloque:
    def __init__(self, xl, xr, yu, yd):
        self.xl = xl
        self.xr = xr
        self.yu = yu
        self.yd = yd
        self.estado = 0

vel = {
    'vh': '130',
    'vl': '080',
    'vn': '120',
}

TIEMPO_MAX_OVERRIDE = 1.5
TIEMPO_MAX_SIN_MOTORES = 3000
TIEMPO_MAX_SIN_POSICION = 3000

BAN_HORIZONTAL = 8
BAN_VERTICAL = 128
BAN_SECCION = 1024
BAN_ENTRADA_SUR = 2048
BAN_ENTRADA_MEDIA = 4096

offset_front = 85
offset_back = 290

y_calle = [12, 31, 49, 60, 71, 90, 110]
secciones_prohibidas = [-1, 12, 13, 14, 17, 18, 19, 52, 53, 54, 57, 58, 59]

carros = {
    'Azul': Carro(),
    'Verde': Carro(),
    'Rojo': Carro()
}

bloques = {
    '1': Bloque(100,400,785,635),
    '2': Bloque(100,400,585,435),
    '3': Bloque(460, 820,785,635),
    '4': Bloque(460, 820,585,435),
    '5': Bloque(1600, 1960,785,635),
    '6': Bloque(1600,1960,585,435),
    '7': Bloque(2020, 2320,785,635),
    '8': Bloque(2020,2320,585,435),
    '9': Bloque(1000, 1150, 1120, 940),
    '10': Bloque(1000, 1150, 280, 100),
    '11': Bloque(1240, 1390, 1120, 940),
    '12': Bloque(1240, 1390, 280, 100),
    '13': Bloque(1000, 1150,785,635),
    '14': Bloque(1000, 1150,585,435),
    '15': Bloque(1240, 1390,785,635),
    '16': Bloque(1240, 1390,585,435),
    '17': Bloque(880,940,785,435),
    '18': Bloque(1480,1540,785,435),
    '19': Bloque(1000,1390,880,820),
    '20': Bloque(1000,1390,400,340)
}


def validaEstadoCarro(carro):
    ahora = time.time()
    trans_motores = ahora - carros[carro].ts_motores
    trans_posicion = ahora - carros[carro].ts_posicion

    res = SIN_CONEXION
    if trans_motores <= TIEMPO_MAX_SIN_MOTORES: res += CONECTADO_MOTORES
    if trans_posicion <= TIEMPO_MAX_SIN_POSICION: res += CONECTADO_POSICION

    return res


def queuePush(carro, comando, limpia):

    # Si debe limpiar la cola elimina todos los comandos
    if limpia:
        carros[carro].ultQueue = ""
        while not carros[carro].queue.empty():
            carros[carro].queue.get_nowait()
            carros[carro].queue.task_done()

    # Si la cola esta llena, elimina un comando
    while carros[carro].queue.full():
        eliminada = carros[carro].queue.get_nowait()
        carros[carro].queue.task_done()
        logging.warning(f'Se elimino comando de la cola de {carro} por saturacion: {eliminada}')

    # Si el comando es uno de ajuste, debe tratarse de forma especial
    if comando in direccionesAjuste:
        if carros[carro].ajustesSeguidos < MAX_AJUSTES:
            carros[carro].queue.put_nowait(comando)
            carros[carro].ajustesSeguidos += 1
            carros[carro].ultQueue = comando
        else:
            logging.warning(f'Eliminando ajuste por exceso de ajustes consecutivos')
    
    # Si no es de ajuste, entonces hay que agregarlo unicamente si no es igual que el ultimo comando de la cola
    elif comando != carros[carro].ultQueue:
        carros[carro].queue.put_nowait(comando)
        carros[carro].ultQueue = comando


def heartbeatMotores(carro):
    ahora = time.time()
    carros[carro].ts_motores = ahora


def heartbeatPosicion(carro):
    ahora = time.time()
    carros[carro].ts_posicion = ahora


def cambiaVel(carro):
    if carros[carro].dire != DIR_F and carros[carro].dire != DIR_B: return

    if carros[carro].dire == DIR_F:
        x = carros[carro].xf
        y = carros[carro].yf
    else:
        x = carros[carro].xa
        y = carros[carro].ya

    for i in range(1,21):
        if bloques[str(i)].yd > y or bloques[str(i)].yu < y: continue
        if bloques[str(i)].xl > x or bloques[str(i)].xr < x: continue

        if carros[carro].vpas != bloques[str(i)].estado:
            if bloques[str(i)].estado == 1: 
                logging.warning(f'{time.time()} - Se inserta a la cola del carro {carro}, bloque de velocidad {bloques[str(i)].estado}')
                carros[carro].queue.put_nowait(VEL_LOW)
                carros[carro].vpas = 1
            elif bloques[str(i)].estado == 0: 
                logging.warning(f'{time.time()} - Se inserta a la cola del carro {carro}, bloque de velocidad {bloques[str(i)].estado}')
                carros[carro].queue.put_nowait(VEL_HIGH)
                carros[carro].vpas = 0


def distancia(x1,y1,x2,y2):
    a = abs(x1-x2)
    a *= a
    b=  abs(y1-y2)
    b *= b
    c = math.sqrt(a+b)
    return c


def overrideDireccion(carro, direccion):
    # Permite pasar todo lo que sean vueltas, stop y cambios de velocidad
    if direccion not in direccionesFrente and direccion not in direccionesAtras: return direccion

    yf = carros[carro].yf
    xf = carros[carro].xf
    yb = carros[carro].ya
    xb = carros[carro].xa
    
    # Obten las coordenadas de ambos lectores del carro
    dirOrig = direccion
    filf = carros[carro].yf
    colf = carros[carro].xf
    filb = carros[carro].ya
    colb = carros[carro].xa

    pend = math.tan(carros[carro].angulo)
    ord = carros[carro].yf - carros[carro].xf*pend 
    
    #compara contra los otros carros
    for i in [0,1,2]:
        act = numcarros[i]
        if act == carro: continue

        a = carros[act].xf
        b = carros[act].yf
        c = carros[act].xa
        d = carros[act].ya
        pend2 = math.tan(carros[act].angulo)
        ord2 = carros[act].yf - carros[act].xf*pend2
        
        if pend == pend2: 
            lineaDireta = distancia(xf,yf,a,b)
            prohibido = 'N'
            if distancia(xf,yf,c,d) < lineaDireta: lineaDireta = distancia(xf,yf,c,d)
            if distancia(xb,yb,a,b) < lineaDireta:
                lineaDireta = distancia(xb,yb,a,b)
                prohibido = 'S'
            if distancia(xb,yb,c,d) < lineaDireta:
                lineaDireta = distancia(xb,yb,a,b)
                prohibido = 'S'

            if lineaDireta < DIS_PARALELA and direccion == prohibido: direccion = DIR_PARA

        else:
            resx = (ord2-ord)/(pend-pend2)
            resy = pend*resx + ord

            #caso donde la colision esta en medio del carro que pregunta (es indiferetne para el)

            if (resx < xf and resx < xb) or (resx > xf and resx > xb):

                if distancia(xf,yf,resx,resy) < distancia(xb,yb,resx,resy):
                    #mas cercano de la colision el sonser delantelro
                    prohibido = DIR_F
                    disTrayectoria = distancia(xf,yf,resx,resy)

                    if (resx < a and resx < c) or (resx > a and resx > c):
                        #no choca contra el medio de el carro contrario
                        if distancia(a,b,resx,resy) < distancia(c,d,resx,resy):
                            #frente frente
                            lineaDireta = distancia(a,b,xf,yf)
                            menor = min(lineaDireta,disTrayectoria)
                            if menor <= DIS_DETEC:
                                if carros[act].ultDir == DIR_F and direccion == prohibido:
                                    logging.warning(f'{time.time()} - Se detubo porque el chocaba carro {act} que iba moviendose hacia {carros[act].ultDir}')
                                    direccion = DIR_PARA
                        else:
                            #frente atras
                            lineaDireta = distancia(c,d,xf,yf)
                            menor = min(lineaDireta,disTrayectoria)
                            if menor <= DIS_DETEC:
                                if carros[act].ultDir == DIR_B and direccion == prohibido:
                                    logging.warning(f'{time.time()} - Se detubo porque el chocaba carro {act} que iba moviendose hacia {carros[act].ultDir}')
                                    direccion = DIR_PARA
                    else:
                        if disTrayectoria < DIS_DETEC and direccion == prohibido: 
                            logging.warning(f'{time.time()} - Se detubo porque el chocaba contra el medio de otro carro')
                            direccion = DIR_PARA

                else:
                    #mas cercano a chocar el sensor trasero 
                    prohibido = DIR_B
                    disTrayectoria = distancia(xb,yb,resx,resy)

                    if (resx < a and resx < c) or (resx > a and resx > c):
                        if distancia(a,b,resx,resy) < distancia(c,d,resx,resy):
                            #atras frente
                            lineaDireta = distancia(a,b,xb,yb)
                            menor = min(lineaDireta,disTrayectoria)
                            if menor <= DIS_DETEC:
                                if carros[act].ultDir == DIR_F and direccion == prohibido:
                                    logging.warning(f'{time.time()} - Se detubo porque el chocaba carro {act} que iba moviendose hacia {carros[act].ultDir}')
                                    direccion = DIR_PARA
                        else:
                            #atras atras
                            lineaDireta = distancia(c,d,xb,yb)
                            menor = min(lineaDireta,disTrayectoria)
                            if menor <= DIS_DETEC:
                                if carros[act].ultDir == DIR_B and direccion == prohibido:
                                    logging.warning(f'{time.time()} - Se detubo porque el chocaba carro {act} que iba moviendose hacia {carros[act].ultDir}')
                                    direccion = DIR_PARA
                    else:
                        if disTrayectoria < DIS_DETEC and direccion == prohibido: 
                            logging.warning(f'{time.time()} - Se detubo porque el chocaba contra el medio de otro carro')
                            direccion = DIR_PARA


    if direccion == DIR_PARA: return direccion
   
    #compara contra los muros

    # Si el coche va hacia adelante, calcula su punto virtual frontal
    if direccion in direccionesFrente:
        if carros[carro].dirBrujula == NORTE:
            xPuntoVirtual = colf
            yPuntoVirtual = max(filf + offset_front, filb + offset_back)
        elif carros[carro].dirBrujula == ESTE:
            xPuntoVirtual = max(colf + offset_front, colb + offset_back)
            yPuntoVirtual = filf
        elif carros[carro].dirBrujula == SUR:
            xPuntoVirtual = colf
            yPuntoVirtual = min(filf - offset_front, filb - offset_back)
        else:   
            xPuntoVirtual = min(colf - offset_front, colb - offset_back)
            yPuntoVirtual = filf
    # Si el coche va en reversa, calcula el punto virtual trasero
    else:
        if carros[carro].dirBrujula == NORTE:
            xPuntoVirtual = colf
            yPuntoVirtual = min(filf - offset_back, filb - offset_front)
        elif carros[carro].dirBrujula == ESTE:
            xPuntoVirtual = min(colf - offset_back, colb - offset_front)
            yPuntoVirtual = filf
        elif carros[carro].dirBrujula == SUR:
            xPuntoVirtual = colf
            yPuntoVirtual = max(filf + offset_back, filb + offset_front)
        else:   
            xPuntoVirtual = max(colf + offset_back, colb + offset_front)
            yPuntoVirtual = filf

    #falta checar el error de que un carro se encuentre encerrado al momento de pasarlo a 2 (cercarlo)
    for i in range(1,21):

        # Revisa si el punto virtual de interes esta dentro del bloque
        sti = str(i)
        if (bloques[sti].yd <= yPuntoVirtual <= bloques[sti].yu) and (bloques[sti].xl <= xPuntoVirtual <= bloques[sti].xr):
            if bloques[sti].estado == 2:
                direccion = DIR_PARA
            elif bloques[sti].estado == 1 and carros[carro].velocidad == VEL_HIGH:
                direccion = VEL_LOW
            elif bloques[sti].estado == 0 and carros[carro].velocidad == VEL_LOW:
                direccion = VEL_HIGH

            logging.warning(f'{time.time()} - El punto virtual del carro {carro} esta dentro del bloque {sti}. Direccion recibida {dirOrig}, se devuelve {direccion}')

            break

    return direccion