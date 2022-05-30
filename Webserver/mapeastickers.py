
coord = {}
BAN_HORIZONTAL = 8
BAN_VERTICAL = 128
BAN_SECCION = 1024
BAN_ENTRADA_SUR = 2048
BAN_ENTRADA_MEDIA = 4096

calles = [
    # Calle 0
    [
        [1, 434, 435, 436, 54],
        [2, 3, 5, 6, 8],
        [4, 463, 464, 465, 5],
        [9, 10, 12, 13, 14],
        [15, 16, 17, 19, 20],
        [21, 22, 24, 26, 27],
        [11, 666, 667, 668, 64],
        [29, 30, 32, 33, 35],
        [36, 37, 38, 39, 41],
        [18, 678, 679, 680, 71],
        [42, 43, 44, 46, 47],
        [48, 49, 51, 52, 55],
        [56, 58, 59, 60, 61],
        [25, 492, 493, 494, 78],
        [62, 63, 65, 66, 67],
        [28, 521, 522, 523, 81],
        [31, 550, 551, 552, 84],
        [68, 69, 70, 72, 73],
        [34, 579, 580, 581, 87],
        [74, 75, 76, 77, 79],
        [80, 82, 83, 85, 86],
        [40, 690, 691, 692, 93],
        [88, 89, 90, 91, 92],
        [45, 702, 703, 704, 98],
        [94, 95, 96, 97, 99],
        [50, 608, 609, 610, 103],
        [100, 101, 102, 104, 105],
        [53, 637, 638, 639, 106]
    ]
]

seccion_inicial = [0]

for calle in range(len(calles)):
    seccion = seccion_inicial[calle]
    for tramo in range(len(calles[calle])):
        for carril in range(len(calles[calle][tramo])):
            sticker = calles[calle][tramo][carril]
            coord[sticker] = {}
            coord[sticker]['calle'] = calle
            coord[sticker]['carril'] = carril + 1
            coord[sticker]['col'] = tramo
            coord[sticker]['seccion_a'] = seccion
            coord[sticker]['seccion_b'] = seccion + 1
        seccion += 1

file = open("mapeo.obj", "w")
file.write("coordenadas = ")
file.write(str(coord))
file.close()
