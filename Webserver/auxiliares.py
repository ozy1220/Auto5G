import asyncio
import math
import time
from coord import coordenadas

DIR_PARA = 'V'
DIR_F = 'N'
DIR_B = 'S'
DIR_R = 'E'
DIR_L = 'O'
DIR_FL = 'W'
DIR_BL = 'X'
DIR_BR = 'Y'
DIR_FR = 'Z'

direcciones = [DIR_PARA, DIR_F, DIR_B, DIR_R, DIR_L, DIR_FL, DIR_BL, DIR_BR, DIR_FR]

SIN_CONEXION = 0
CONECTADO_MOTORES = 1
CONECTADO_POSICION = 2
CONECTADO_LISTO = 3

NORTE = 0
ESTE = 1
SUR = 2
OESTE = 3
LIMBO = 4


class Carro:
    def __init__(self):
        self.frente = -1
        self.atras = -1
        self.dire = 'V'
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

        self.ipPosiciones = ""
        self.ipMotores = ""
        self.uuidEnlace = ""

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

vel = {
    'vh': '200',
    'vl': '100',
    'vn': '150',
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


def overrideDireccion(carro, direccion):
    print(direccion)
    print(carros[carro].prohibidos[direccion])
    if carros[carro].prohibidos[direccion]:
        res = DIR_PARA

    else:
        res = direccion

    print(f'Se recibio direccion {direccion}, se envia {res}')
    return res