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


def parse_commondata(common_bytes):
    """
    Parse COMMONDATA union (16 bytes)
    """

    values = struct.unpack('<8H', common_bytes)

    server_year = values[2]
    server_month = values[3]
    server_day = values[4]
    server_hour = values[5]
    server_minute = values[6]
    server_second = values[7]

    server_time = f"{server_year:04d}-{server_month:02d}-{server_day:02d} " \
                  f"{server_hour:02d}:{server_minute:02d}:{server_second:02d}"

    bins = struct.unpack('<4f', common_bytes)

    return {
        "server_year": server_year,
        "server_month": server_month,
        "server_day": server_day,
        "server_hour": server_hour,
        "server_minute": server_minute,
        "server_second": server_second,
        "server_datetime": server_time,

        "bins_f1": bins[0],
        "bins_f2": bins[1],
        "bins_f3": bins[2],
        "bins_f4": bins[3],
    }


def parse_gps(gps_bytes):
    """Parse TGPSData (64 bytes)."""

    floats = struct.unpack('<10f', gps_bytes[0:40])

    utc1, ft, lt, hf, vn, ve, vy, ac, ar, ap = floats

    ns = struct.unpack('<H', gps_bytes[40:42])[0]

    common_bytes = gps_bytes[44:60]
    commondata = parse_commondata(common_bytes)

    dma_buf = struct.unpack('<I', gps_bytes[60:64])[0]

    ft_deg, ft_min, ft_sec = radians_to_dms(ft)
    lt_deg, lt_min, lt_sec = radians_to_dms(lt)

    result = {
        "UTC1": utc1,

        "Ft_rad": ft,
        "Lt_rad": lt,

        "Ft_deg": ft_deg,
        "Ft_min": ft_min,
        "Ft_sec": ft_sec,

        "Lt_deg": lt_deg,
        "Lt_min": lt_min,
        "Lt_sec": lt_sec,

        "Hf": hf,

        "Vn": vn,
        "Ve": ve,
        "Vy": vy,

        "Ac_rad": ac,
        "Ar_rad": ar,
        "Ap_rad": ap,

        "Ns": ns,
        "DMA_buf": dma_buf
    }

    result.update(commondata)

    return result


def decode_pasp_rgg(pasp_rgg):
    """Decode passport structure."""

    prefix_length = (pasp_rgg & 0xFF) * 4
    pages = (pasp_rgg >> 8) & 0xFF
    page_size = (pasp_rgg >> 16) & 0xFFFF

    return prefix_length, pages, page_size


def decode_fl_rgg(fl_rgg):
    """Decode bit flags."""

    return {
        "bench_signal": bool(fl_rgg & 1),
        "balance_channels": bool(fl_rgg & 2),
        "average_compensation": bool(fl_rgg & 4),
        "sync_mode": bool(fl_rgg & 8),
        "azimuth_measurement": bool(fl_rgg & 16),
        "delay_selection": bool(fl_rgg & 32),
        "mnav2x_receiver": bool(fl_rgg & 64),
        "nav_fmc": bool(fl_rgg & 128),
    }


def read_prefix(file):

    data = file.read(128)

    if len(data) < 128:
        return None, 0

    fields = struct.unpack_from('<IIIIHHHHfffffffff', data, 0)

    (
        type_rgg,
        pasp_rgg,
        np_giv,
        n_str,
        fl_rgg,
        np_gps,
        kd,
        bit_out,
        fd,
        df,
        fs,
        ts,
        tp,
        to,
        ae,
        ph_rd,
        ph_dp
    ) = fields

    np_num = struct.unpack_from('<I', data, 124)[0]

    prefix_length, pages, page_size = decode_pasp_rgg(pasp_rgg)

    flags = decode_fl_rgg(fl_rgg)

    gps_bytes = data[60:124]
    gps_dict = parse_gps(gps_bytes)

    bytes_per_component = (bit_out + 7) // 8
    bytes_per_sample = 2 * bytes_per_component
    data_size = n_str * bytes_per_sample

    result = {
        "Np_num": np_num,

        "prefix_length": prefix_length,
        "passport_pages": pages,
        "passport_page_size": page_size,

        "Np_giv": np_giv,
        "N_str": n_str,

        "Np_gps": np_gps,
        "Kd": kd,
        "Bit_out": bit_out,

        "Fd_MHz": fd,
        "dF_MHz": df,
        "Fs_MHz": fs,

        "Ts_us": ts,
        "Tp_us": tp,
        "To_us": to,

        "Ae_rad": ae,
        "Ph_rd_rad": ph_rd,
        "Ph_dp_rad": ph_dp
    }

    result.update(flags)
    result.update(gps_dict)

    return result, data_size


def main(input_file="irz/270721_1306_X_.bin", output_csv="prefix_data.parquet"):

    records = []

    with open(input_file, "rb") as f:

        pulse = 0

        while True:

            prefix, data_size = read_prefix(f)

            if prefix is None:
                print("End of file reached")
                break

            records.append(prefix)

            f.seek(data_size, os.SEEK_CUR)

            pulse += 1

            if pulse % 1000 == 0:
                print(f"Processed {pulse} pulses")

    if not records:
        print("No data parsed")
        return

    df = pd.DataFrame(records)

    print(df.head())

    df.to_parquet(output_csv, index=False)

    print(f"Saved to {output_csv}")


if __name__ == "__main__":
    main()
