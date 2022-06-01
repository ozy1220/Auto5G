import asyncio
from cmath import sqrt
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
DIS_DETEC = 200
DIS_COLISION = 180

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

cy_calle = [12, 48, 72, 108]
ang_calle = [math.pi, 0, math.pi, 0]
cx_seccion = [0, 7, 14, 21, 29, 36, 43, 50, 57, 64, 71, 79, 86, 93, 100, 107, 114, 121, 129, 136, 143, 150, 157, 165, 171, 179, 186, 193, 200, 210]

#variables de programacion
numcarros = ['Azul','Verde','Rojo']

# La clase carro lleva el control de:
    # Ultima lectura del sticker front
    # Ultima lectura del sticker back
    # 

class Carro:
    def __init__(self):
        self.frente = -1
        self.atras = -1
        self.dire = 'V'
        self.dirControl = 'V'
        self.ultDir = 'V'
        self.llave = ''
        self.ocupado = 'false'
        self.xf = 0
        self.yf = 0
        self.xa = 0
        self.ya = 0
        self.x = 0
        self.y = 0
        self.angulo = 0
        self.ts_posicion = 0
        self.queue = asyncio.Queue(maxsize=4)

        self.prohibidos = {
            'N': False,
            'S': False,
            'E': False,
            'O': False,
            'W': False,
            'X': False,
            'Y': False,
            'Z': False,
            'V': False
        }
        
        self.mov_frente = 0

        self.seccion_f = -1
        self.seccion_a = -1
        self.sentido = LIMBO
        self.calle = 0
        self.ts_motores = 0
        self.ts_posicion = 0
        self.estatus_conexion = SIN_CONEXION

        self.dirBrujula = 0

        self.vpas = 0
        
        self.ultcarril = 3
        self.ultcol = 50
        self.ajustesSeguidos = 0

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
    'v1': '050',
    'v2': '100',
    'v3': '150',
    'v4': '200',
    'v5': '250' 
}

TIEMPO_MAX_OVERRIDE = 1.5
TIEMPO_MAX_SIN_MOTORES = 3000
TIEMPO_MAX_SIN_POSICION = 3000

BAN_HORIZONTAL = 8
BAN_VERTICAL = 128
BAN_SECCION = 1024
BAN_ENTRADA_SUR = 2048
BAN_ENTRADA_MEDIA = 4096

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


def eliminaProhibidos(carro):
    for direccion in direcciones:
        carros[carro].prohibidos[direccion] = False


def validaEstadoCarro(carro):
    ahora = time.time()
    trans_motores = ahora - carros[carro].ts_motores
    trans_posicion = ahora - carros[carro].ts_posicion

    res = SIN_CONEXION
    if trans_motores <= TIEMPO_MAX_SIN_MOTORES: res += CONECTADO_MOTORES
    if trans_posicion <= TIEMPO_MAX_SIN_POSICION: res += CONECTADO_POSICION

    return res

def heartbeatMotores(carro):
    ahora = time.time()
    carros[carro].ts_motores = ahora


def heartbeatPosicion(carro):
    ahora = time.time()
    carros[carro].ts_posicion = ahora


def prohibeMovimientos(carro, previaf, actualf, previaa, actuala):
    pf = previaf in secciones_prohibidas
    af = actualf in secciones_prohibidas
    pa = previaa in secciones_prohibidas
    aa = actuala in secciones_prohibidas

    res = False

    print(f'previaf = {previaf}, pf = {pf}')
    print(f'actualf = {actualf}, pf = {af}')
    print(f'previaa = {previaa}, pf = {pa}')
    print(f'actuala = {actuala}, pf = {aa}')
    print(f'Sentido coche = {carros[carro].sentido}, direccion actual = {carros[carro].dire}')

    if carros[carro].sentido == LIMBO:
        eliminaProhibidos(carro)
    elif af:
        carros[carro].prohibidos[DIR_F] = True
        carros[carro].prohibidos[DIR_FL] = True
        carros[carro].prohibidos[DIR_FR] = True
        if carros[carro].dire == DIR_F or carros[carro].dire == DIR_FL or carros[carro].dire == DIR_FR: res = True
    elif pf and not af:
        carros[carro].prohibidos[DIR_F] = False
        carros[carro].prohibidos[DIR_FL] = False
        carros[carro].prohibidos[DIR_FR] = False

    if aa:
        carros[carro].prohibidos[DIR_B] = True
        carros[carro].prohibidos[DIR_BL] = True
        carros[carro].prohibidos[DIR_BR] = True
        if carros[carro].dire == DIR_B or carros[carro].dire == DIR_BL or carros[carro].dire == DIR_BR: res = True
    elif pa and not aa:
        carros[carro].prohibidos[DIR_B] = False
        carros[carro].prohibidos[DIR_BL] = False
        carros[carro].prohibidos[DIR_BR] = False
    
    return res



def calculaSeccion(carro, front, back):
    dir_carro = carros[carro].sentido
    ban_front = coordenadas[front]['banderas']
    ban_back = coordenadas[back]['banderas']
    previa_f = carros[carro].seccion_f
    previa_a = carros[carro].seccion_a

    # Dirección LIMBO
    if dir_carro == LIMBO:
        # El carro solo sale del limbo si el frente pasa por alguna entrada
        if (ban_front & BAN_ENTRADA_SUR) == BAN_ENTRADA_SUR:
            carros[carro].seccion_f = 10
            carros[carro].seccion_a = -1
            carros[carro].calle = 0
            carros[carro].sentido = OESTE

        elif (ban_front & BAN_ENTRADA_MEDIA) == BAN_ENTRADA_MEDIA:
            carros[carro].seccion_f = 40
            carros[carro].seccion_a = -1
            carros[carro].calle = 2
            carros[carro].sentido = OESTE
    
    else:
        # Checa a que seccion pasa
        if front != str(0) and carros[carro].frente != front:
            if (ban_front & BAN_HORIZONTAL) == BAN_HORIZONTAL:
                a = coordenadas[front]['norte']
                b = coordenadas[front]['sur']
                if carros[carro].seccion_f == a: carros[carro].seccion_f = b
                else: carros[carro].seccion_f = a
            else:
                a = coordenadas[front]['este']
                b = coordenadas[front]['oeste']
                if carros[carro].seccion_f == a: carros[carro].seccion_f = b
                else: carros[carro].seccion_f = a

        if back != str(0) and carros[carro].atras != back:
            if (ban_back & BAN_HORIZONTAL) == BAN_HORIZONTAL:
                a = coordenadas[back]['norte']
                b = coordenadas[back]['sur']
                if carros[carro].seccion_a == a: carros[carro].seccion_a = b
                else: carros[carro].seccion_a = a
            else:
                a = coordenadas[back]['este']
                b = coordenadas[back]['oeste']
                if carros[carro].seccion_a == a: carros[carro].seccion_a = b
                else: carros[carro].seccion_a = a

    carros[carro].frente = front
    carros[carro].atras = back

    seccion_f = carros[carro].seccion_f
    seccion_a = carros[carro].seccion_a

    prohibe = prohibeMovimientos(carro, previa_f, seccion_f, previa_a, seccion_a)

    if carros[carro].sentido == NORTE:
        angulo = math.pi / 2
    elif carros[carro].sentido == OESTE:
        angulo = math.pi
        if carros[carro].seccion_f == carros[carro].seccion_a:
            posx = ((carros[carro].seccion_f - 1) % 10) * 20 + 16
        else:
            posx = ((carros[carro].seccion_f - 1) % 10) * 20 + 26
        posy = y_calle[int((seccion_f - 1) / 10)]
    elif carros[carro].sentido == SUR:
        angulo = math.pi * 1.5
    else:
        angulo = 0
        if carros[carro].seccion_f == carros[carro].seccion_a:
            posx = ((carros[carro].seccion_f - 1) % 10) * 20 + 16
        else:
            posx = ((carros[carro].seccion_f - 1) % 10) * 20 + 6
        posy = y_calle[int((seccion_f - 1) / 10)]

    return posx, posy, angulo, prohibe

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

#def checamov(x1,y1,x2,y2,f,b):

def overrideDireccion(carro, direccion):
    if direccion not in direccionesFrente and direccion not in direccionesAtras: return direccion

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

        #calculo en base a las trayectorias
        #checar y hacer pruebas con DIS_DETEC y DIS_COLISION
        #checar caso donde angulo es casi 0 pegado a nada
        a = carros[act].xf
        b = carros[act].yf
        c = carros[act].xa
        d = carros[act].ya
        if distancia(colf,filf,a,b) < DIS_DETEC or distancia(colf,filf,c,d) < DIS_DETEC or distancia(colb,filb,a,b) < DIS_DETEC or distancia(colb,filb,c,d) < DIS_DETEC:
            pend2 = math.tan(carros[act].angulo)
            ord2 = carros[act].yf - carros[act].xf*pend2

            if pend == pend2:
                if distancia(colf,filf,a,b) < distancia(colb,filf,a,b):
                    #va hacia adelante
                    if distancia(colf,filf,a,b) < distancia(colf,filf,c,d):
                        #chocar por adelante
                        resx = a
                        resy = b
                    else:
                        resx = c
                        resy = d
                else:
                    if distancia(colb,filb,a,b) < distancia(colb,filb,c,d):
                        #chocar por adelante
                        resx = a
                        resy = b
                    else:
                        resx = c
                        resy = d
            else:
                resx = (ord2-ord)/(pend-pend2)
                resy = pend*resx + ord

            #checar caso el punto se encuentra dentro de el front y back
            a = max(filf,filb)
            b = max(colf,colb)
            c = min(filf,filb) 
            d = min(colf,colb)
            #if (d <= resx and resx <= b) and (c <= resy and resy <= a) 
            #comentado para probar

            a = distancia(resx,resy,colf,filf)
            b = distancia(resx,resy,colb,filb)
            #if a <= DIS_COLISION or b < DIS_COLISION:
            #comentdo para probar

        #Terminar de hacer los casos, yas sea directamente entre puntos o contra la evaluacion de las rectas

    if direccion == DIR_PARA: return direccion
    
    #compara contra los muros
    #falta checar el error de que un carro se encuentre encerrado al momento de pasarlo a 2 (cercarlo)
    for i in range(1,20):
        if bloques[str(i)].estado != 2: continue

        #sensor front
        if (bloques[str(i)].yd <= filf and filf <= bloques[str(i)].yu) and (bloques[str(i)].xl <= colf and colf <= bloques[str(i)].xr):
            if direccion in direccionesFrente: 
                    direccion = DIR_PARA
                    logging.warning(f'Se recibio carro {carro}, frente del carro se encuentra dentro de la zona')

        elif bloques[str(i)].yd <= filf and filf <= bloques[str(i)].yu: 
            a = abs(colf-bloques[str(i)].xl) 
            b = abs(colf-bloques[str(i)].xr)
            if a <= 60 or b <= 60:
                if direccion in direccionesFrente: 
                    direccion = DIR_PARA
                    logging.warning(f'Se recibio carro {carro}, se bloquea por zona ocupada adelante')
        elif bloques[str(i)].xl <= colf and colf <= bloques[str(i)].xr: 
            a = abs(filf-bloques[str(i)].yu) 
            b = abs(filf-bloques[str(i)].yd)
            if a <= 60 or b <= 60:
                if direccion in direccionesFrente: 
                    direccion = DIR_PARA
                    logging.warning(f'Se recibio carro {carro}, se bloquea por zona ocupada adelante')
        
        #sensor back
        if (bloques[str(i)].yd <= filb and filb <= bloques[str(i)].yu) and (bloques[str(i)].xl <= colb and colb <= bloques[str(i)].xr):
                if direccion in direccionesAtras: 
                    direccion = DIR_PARA
                    logging.warning(f'Se recibio carro {carro}, se bloquea por zona ocupada atras')
        if bloques[str(i)].yd <= filb and filb <= bloques[str(i)].yu: 
            a = abs(colb-bloques[str(i)].xl) 
            b = abs(colb-bloques[str(i)].xr)
            if a <= 60 or b <= 60:
                if direccion in direccionesAtras: 
                    direccion = DIR_PARA
                    logging.warning(f'Se recibio carro {carro}, parte trasera del autp se encuentra dentro de la zona')
        elif bloques[str(i)].xl <= colb and colb <= bloques[str(i)].xr: 
            a = abs(filb-bloques[str(i)].yu) 
            b = abs(filb-bloques[str(i)].yd)
            if a <= 60 or b <= 60:
                if direccion in direccionesAtras: 
                    direccion = DIR_PARA
                    logging.warning(f'Se recibio carro {carro}, se bloquea por zona ocupada atras')


    return direccion