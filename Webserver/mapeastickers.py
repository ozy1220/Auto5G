
coord = {}
BAN_HORIZONTAL = 8
BAN_VERTICAL = 128
BAN_SECCION = 1024
BAN_ENTRADA_SUR = 2048
BAN_ENTRADA_MEDIA = 4096

for i in range(721):
    coord[str(i)] = {}

# Dummy
coord['0']['banderas'] = 0

# Lineas horizontales
offset = [1, 4, 25, 28, 30, 33, 50, 53]
numoffset = 8
secciones = [4, 11, 18, 25, 29, 33, 39, 45, 50, 54]
numsecciones = 10
ini = 1
linea_y = 0
vuelta = 0
for linea in range(8):
    bandera = BAN_HORIZONTAL + linea
    for i in range(53):
        coord[str(i + ini)]['banderas'] = bandera
    
    for o in range(8):
        coord[str(ini + offset[o] - 1)]['banderas'] += BAN_VERTICAL + (o << 4)

    ind = 0
    for i in range(53):
        if (i + 1) == secciones[ind]: ind += 1

        snorte = linea_y + ind + 1
        ssur = linea_y - 10 + ind + 1
        if snorte > 70: snorte = -1
        if ssur < 1: ssur = - 1

        coord[str(i + ini)]['norte'] = snorte
        coord[str(i + ini)]['sur'] = ssur
    
    linea_y = linea_y + 10

    ini += 53
    if ini > 324: ini = 381

# Lineas verticales
ini = 434
sec_e = [-1, 1, 4, 5, 5, 6, 9, 10]
sec_o = [1, 2, 5, 6, 6, 7, 10, -1]
sini = [0, 3, 10, 13, 15, 18, 26]
sfin = [3, 10, 13, 15, 18, 26, 29]

for linea in range(8):
    bandera = BAN_VERTICAL + (linea << 4)
    for i in range(29):
        coord[str(i + ini)]['banderas'] = bandera
    
    for salto in range(7):
        for i in range(sini[salto], sfin[salto], 1):
            if sec_e[linea] != -1:
                coord[str(i + ini)]['oeste'] = sec_e[linea] + (salto * 10)
            else:
                coord[str(i + ini)]['oeste'] = sec_e[linea]

            if sec_o[linea] != -1:
                coord[str(i + ini)]['este'] = sec_o[linea] + (salto * 10)
            else:
                coord[str(i + ini)]['este'] = sec_o[linea]

    ini += 29

# Secciones
ini = 666
sec_e = [2, 3, 7, 8]
sec_o = [3, 4, 8, 9]
sini = [0, 3, 6, 9]
sfin = [3, 6, 9, 12]
soff = [0, 20, 40, 60]
for seccion in range(4):
    bandera = BAN_SECCION + (seccion << 8)
    for i in range(12):
        coord[str(ini + i)]['banderas'] = bandera

    for tramo in range(4):
        for i in range(sini[tramo], sfin[tramo], 1):
            coord[str(i + ini)]['oeste'] = sec_e[seccion] + soff[tramo]
            coord[str(i + ini)]['este'] = sec_o[seccion] + soff[tramo]

    ini += 12

# Entrada
ini = 637
for i in range(3):
    coord[str(ini + i)]['banderas'] += BAN_ENTRADA_SUR

ini = 652
for i in range(3):
    coord[str(ini + i)]['banderas'] += BAN_ENTRADA_MEDIA

file = open("mapeo.obj", "w")
file.write("coordenadas = ")
file.write(str(coord))
file.close()
