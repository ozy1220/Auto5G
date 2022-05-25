import asyncio
import math
from coord import coordenadas

carros = {
    'Azul':{
        'frente': -1,
        'atras': -1,
        'dire': 'V',
        'overrides': 0,
        'ocupado': 'false',
        'llave' : '123456',
        'queue': asyncio.Queue(),
        'x': -1,
        'y': -1,
        'angulo': 0
    },
    'Verde':{
        'frente': -1,
        'atras': -1,
        'dire': 'V',
        'overrides': 0,
        'ocupado': 'false',
        'llave' : '123456',
        'queue': asyncio.Queue(),
        'x': -1,
        'y': -1,
        'angulo': 0
    },
    'Rojo':{
        'frente': -1,
        'atras': -1,
        'dire': 'V',
        'overrides': 0,
        'ocupado': 'false',
        'llave' : '123456',
        'queue': asyncio.Queue(),
        'x': -1,
        'y': -1,
        'angulo': 0
    }
}

# Triangulo en los lectores del coche
tc_ca = 10.7
tc_co = 2.1
tc_h = 10.9
tc_ang = 0.1929193140080
tc_inc_ang = math.pi / 6

def posLector(etiqueta, centro_x, centro_y, angulo, direccion, es_frontal):
    lx = coordenadas[etiqueta]['x']
    ly = coordenadas[etiqueta]['y']

    # Calcula el centro del coche basado en la lectura y la pendiente previa

    # Si la direccion es norte o sur, el angulo no cambia
    if direccion == 'N' or direccion == 'S':
        # Suma el angulo que traia con el del lector contra el centro
        ang_real = angulo + tc_ang
        dx = tc_h * math.acos(ang_real)
        dy = tc_h * math.asin(ang_real)
        if es_frontal: return lx - dx, ly - dy, angulo
        else: return lx + dx, ly + dy, angulo

    # Si la direccion es este u oeste, asume que el centro anterior no cambia y mas bien hubo un cambio de angulo
    elif direccion == 'E' or direccion == 'O':
        dy = ly - centro_y
        dx = lx - centro_x
        if dx == 0:
            if es_frontal and dy >= 0: ang_real = math.pi / 2
            elif es_frontal: ang_real = math.pi * 3 / 2
            elif not es_frontal and dy >= 0: ang_real = math.pi * 3 / 2
            else: ang_real = math.pi / 2
            ang_real -= tc_ang
        else:
            ang_real = math.atan(dy / dx)
            if not es_frontal: 
                ang_real += 2 * math.pi
                if ang_real > 2 * math.pi: ang_real -= 2 * math.pi
            ang_real -= tc_ang
        
        return centro_x, centro_y, ang_real

    # Si la direccion es NO, NE, SO o SE, debe asumir cambio de centro y cambio de angulo
    else:
        # Haz lo mismo que si avanza recto y asume un cambio de angulo
        if direccion == 'NE' or direccion == 'SO': delta_ang = -tc_inc_ang
        else: delta_ang = tc_inc_ang

        ang_real = angulo + tc_ang + delta_ang
        print(ang_real)
        dx = tc_h * math.acos(ang_real)
        dy = tc_h * math.asin(ang_real)
        if es_frontal: return lx - dx, ly - dy, angulo
        else: return lx + dx, ly + dy, angulo


def promediaLectores(etiqueta_frente, etiqueta_atras):
    if etiqueta_frente == 0: etiqueta_frente = etiqueta_atras
    elif etiqueta_atras == 0: etiqueta_atras = etiqueta_frente

    fx = coordenadas[etiqueta_frente]['x']
    fy = coordenadas[etiqueta_frente]['y']
    ax = coordenadas[etiqueta_atras]['x']
    ay = coordenadas[etiqueta_atras]['y']
    dy = fy - ay
    dx = fx - ax
    if dx == 0:
        if dy >= 0: ang_real = math.pi / 2
        else: ang_real = math.pi * 3 / 2
    else:
        ang_real = math.atan2(dy, dx)
    ang_real -= tc_ang
    cx = (fx + ax) / 2
    cy = (fy + ay) / 2
    return cx, cy, ang_real


def estimaNuevaPosicion(carro, front, back):
    # Toma en cuenta solo el lector que haya cambiado
    frente_previo = carros[carro]['frente']
    atras_previo = carros[carro]['atras']
    angulo_previo = carros[carro]['angulo']
    dir_actual = carros[carro]['dire']
    centro_x = carros[carro]['x']
    centro_y = carros[carro]['y']
    if frente_previo != front and atras_previo != back:
        posx, posy, angulo = promediaLectores(front, back)
        # actualiza
        carros[carro]['frente'] = front
        carros[carro]['atras'] = back

    #elif frente_previo != front:
        #posx, posy, angulo = posLector(front, centro_x, centro_y, angulo_previo, dir_actual, True)
        #carros[carro]['frente'] = front

    #elif atras_previo != back:
        #posx, posy, angulo = posLector(back, centro_x, centro_y, angulo_previo, dir_actual, False)
        #carros[carro]['atras'] = back

    else: 
        posx, posy, angulo = promediaLectores(front, back)
        # actualiza
        carros[carro]['frente'] = front
        carros[carro]['atras'] = back
        #posx = centro_x
        #posy = centro_y
        #angulo = angulo_previo

    # Actualiza las posiciones
    carros[carro]['x'] = posx
    carros[carro]['y'] = posy
    carros[carro]['angulo'] = angulo

    return posx, posy, angulo


def overrideDireccion(carro, direccion):
    px = carros[carro]['x']
    py = carros[carro]['y']
    ang = carros[carro]['angulo']

    # Determina en la calle en la que va, las calles son:
    # [0 - 3]: Horizontal de sur a norte
    # [4 - 7]: Vertical de oeste a este


    if direccion == 'N':
        if ang > 10 or py > 14: res = 'E'
        elif carros[carro]['angulo'] < -10 or py < 9: res = 'O'
        else: res = 'N'
    else: res = direccion
    print(f'Se recibio direccion {direccion}, se envia {res}, angulo = {ang}, py = {py}')
    return res