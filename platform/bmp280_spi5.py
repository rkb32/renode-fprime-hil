# BMP280 stand-in on SPI5 (register level, M0 only; not a real sensor model).
# Verified SPI offsets (CMSIS): CR1 0x00 (CSTART = bit 9), SR 0x14, TXDR 0x20, RXDR 0x30.
# A transfer starts when firmware sets CSTART. The first TXDR byte is the BMP280 command:
# bit 7 = read, bits 6..0 = register address. Later bytes read or write registers, auto-incrementing.

if 'st' not in globals():
    st = {'expect_cmd': False, 'addr': 0, 'read': False, 'pending': 0}
    REG = {
        0xD0: 0x58,  # chip id (BMP280)
        0xF4: 0x00, 0xF5: 0x00,
        # calibration (BMP280 datasheet example values, little endian)
        0x88: 0x70, 0x89: 0x6B, 0x8A: 0x43, 0x8B: 0x67, 0x8C: 0x18, 0x8D: 0xFC,
        0x8E: 0x7D, 0x8F: 0x8E, 0x90: 0xC3, 0x91: 0xD6, 0x92: 0xD0, 0x93: 0x0B,
        0x94: 0x27, 0x95: 0x0B, 0x96: 0x8C, 0x97: 0x00, 0x98: 0xF9, 0x99: 0xFF,
        0x9A: 0x8C, 0x9B: 0x3C, 0x9C: 0xF8, 0x9D: 0xC7, 0x9E: 0x70, 0x9F: 0x17,
        0xA1: 0x4B,
        # raw pressure (0xF7..0xF9) and temperature (0xFA..0xFC), fixed values
        0xF7: 0x50, 0xF8: 0x00, 0xF9: 0x00, 0xFA: 0x80, 0xFB: 0x00, 0xFC: 0x00,
    }

if request.isWrite:
    if request.offset == 0x00:  # CR1
        if (request.value >> 9) & 1:
            st['expect_cmd'] = True
    elif request.offset == 0x20:  # TXDR
        b = request.value & 0xFF
        if st['expect_cmd']:
            st['expect_cmd'] = False
            st['addr'] = b & 0x7F
            st['read'] = (b & 0x80) != 0
            st['pending'] = 0
        elif st['read']:
            st['pending'] = REG.get(st['addr'], 0)
            st['addr'] = (st['addr'] + 1) & 0x7F
        else:
            REG[st['addr']] = b
            st['addr'] = (st['addr'] + 1) & 0x7F
            st['pending'] = 0
else:
    if request.offset == 0x14:  # SR: RXP | TXP | EOT | TXC always ready
        request.value = 0x100B
    elif request.offset == 0x30:  # RXDR
        request.value = st['pending']
    else:
        request.value = 0
