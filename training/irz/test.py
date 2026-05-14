import struct
import pandas as pd
import os
import math

def radians_to_dms(rad):
    """Convert radians to degrees, minutes, seconds."""
    deg = math.degrees(rad)
    d = int(deg)
    m = int(abs(deg - d) * 60)
    s = (abs(deg - d) - m/60) * 3600
    return d, m, s

def parse_gps(gps_bytes):
    """Parse TGPSData (64 bytes) according to provided structure."""
    # First 10 floats (0-40)
    floats = struct.unpack('<10f', gps_bytes[0:40])
    utc1, ft, lt, hf, vn, ve, vy, ac, ar, ap = floats

    # WORD Ns (2 bytes) at offset 40
    ns = struct.unpack('<H', gps_bytes[40:42])[0]

    # 2 bytes padding (42-44) ignored

    # COMMONDATA (16 bytes) at offset 44-60
    comdata_raw = gps_bytes[44:60].hex()

    # DWORD DMA_buf at offset 60-64
    dma_buf = struct.unpack('<I', gps_bytes[60:64])[0]

    # Convert latitude and longitude to DMS
    ft_deg, ft_min, ft_sec = radians_to_dms(ft)
    lt_deg, lt_min, lt_sec = radians_to_dms(lt)

    return {
        'utc1': utc1,
        'ft_rad': ft,
        'lt_rad': lt,
        'ft_deg': ft_deg,
        'ft_min': ft_min,
        'ft_sec': ft_sec,
        'lt_deg': lt_deg,
        'lt_min': lt_min,
        'lt_sec': lt_sec,
        'hf': hf,
        'vn': vn,
        've': ve,
        'vy': vy,
        'ac_rad': ac,
        'ar_rad': ar,
        'ap_rad': ap,
        'ns': ns,
        'comdata_raw': comdata_raw,
        'dma_buf': dma_buf
    }

def read_prefix(file):
    data = file.read(128)
    if len(data) < 128:
        return None, 0

    # Р Р°СЃРїР°РєРѕРІРєР° РїРµСЂРІС‹С… 60 Р±Р°Р№С‚ (РґРѕ GPS)
    fields = struct.unpack_from('<IIIIHHHHfffffffff', data, 0)
    type_rgg, pasp_rgg, np_giv, n_str, fl_rgg, np_gps, kd, bit_out, fd, df, fs, ts, tp, to, ae, ph_rd, ph_dp = fields

    gps_bytes = data[60:124]
    np_num = struct.unpack_from('<I', data, 124)[0]

    bytes_per_component = (bit_out + 7) // 8
    bytes_per_sample = 2 * bytes_per_component
    data_size = n_str * bytes_per_sample

    result = {
        'TypeRgg': type_rgg,
        'PaspRgg': pasp_rgg,
        'Np_giv': np_giv,
        'N_str': n_str,
        'Fl_Rgg': fl_rgg,
        'Np_gps': np_gps,
        'Kd': kd,
        'Bit_out': bit_out,
        'Fd': fd,
        'dF': df,
        'Fs': fs,
        'Ts': ts,
        'Tp': tp,
        'To': to,
        'Ae': ae,
        'Ph_rd': ph_rd,
        'Ph_dp': ph_dp,
        'Np_num': np_num
    }

    # Р”РѕР±Р°РІР»СЏРµРј СЂР°СЃРїР°РєРѕРІР°РЅРЅС‹Рµ GPS РґР°РЅРЅС‹Рµ
    gps_dict = parse_gps(gps_bytes)
    result.update(gps_dict)

    return result, data_size

def main(input_file='pref.bin', num_pulses=5):
    records = []
    with open(input_file, 'rb') as f:
        for i in range(num_pulses):
            prefix, data_size = read_prefix(f)
            if prefix is None:
                print(f"РљРѕРЅРµС† С„Р°Р№Р»Р° РїРѕСЃР»Рµ {i} РёРјРїСѓР»СЊСЃРѕРІ.")
                break
            records.append(prefix)
            f.seek(data_size, os.SEEK_CUR)

    if not records:
        print("РќРµС‚ РґР°РЅРЅС‹С….")
        return

    df = pd.DataFrame(records)
    print(df)
    df.to_csv('prefixes_with_gps.csv', index=False)
    print("РЎРѕС…СЂР°РЅРµРЅРѕ РІ prefixes_with_gps.csv")

if __name__ == '__main__':
    main()
