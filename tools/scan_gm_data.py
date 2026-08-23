#!/usr/bin/env python3
"""Detecta archivos de datos GameMaker (data.win) y evalua compatibilidad con Cinnamon.

Layout de FORM/GEN8/CODE tomado directamente de src/data_win.c en
Project-Sunshine-Native/cinnamon (rama UNDERTALE-3DS), no de documentacion de terceros.
"""
import argparse
import os
import struct

CINNAMON_BYTECODE_VERSIONS = (16, 17)
GEN8_NAME_OFFSET = 40
GEN8_DISPLAYNAME_OFFSET = 100


def read_top_level_chunks(f, form_end):
    chunks = []
    while f.tell() + 8 <= form_end:
        name = f.read(4)
        if len(name) < 4:
            break
        (length,) = struct.unpack("<I", f.read(4))
        data_start = f.tell()
        chunks.append((name.decode("latin1"), data_start, length))
        f.seek(data_start + length)
    return chunks


def read_gm_string(f, offset):
    if offset == 0:
        return None
    f.seek(offset)
    raw = f.read(256)
    end = raw.find(b"\0")
    if end != -1:
        raw = raw[:end]
    return raw.decode("utf-8", errors="replace")


def scan_data_win(path):
    with open(path, "rb") as f:
        if f.read(4) != b"FORM":
            return None
        (form_length,) = struct.unpack("<I", f.read(4))
        form_end = f.tell() + form_length
        chunks = read_top_level_chunks(f, form_end)

        info = {
            "path": path,
            "size": os.path.getsize(path),
            "chunks": [(n, l) for n, _, l in chunks],
            "bytecode_version": None,
            "has_code": False,
            "code_length": 0,
            "name": None,
            "display_name": None,
        }

        gen8_start = next((s for n, s, l in chunks if n == "GEN8" and l > 0), None)
        for name, _start, length in chunks:
            if name == "CODE":
                info["has_code"] = length > 0
                info["code_length"] = length

        if gen8_start is not None:
            f.seek(gen8_start + 1)
            info["bytecode_version"] = f.read(1)[0]

            f.seek(gen8_start + GEN8_NAME_OFFSET)
            (name_ptr,) = struct.unpack("<I", f.read(4))
            info["name"] = read_gm_string(f, name_ptr)

            f.seek(gen8_start + GEN8_DISPLAYNAME_OFFSET)
            (display_ptr,) = struct.unpack("<I", f.read(4))
            info["display_name"] = read_gm_string(f, display_ptr)

        return info


def verdict(info):
    if info["bytecode_version"] is None:
        return "Sin chunk GEN8 valido: no se pudo leer la version de bytecode."
    if not info["has_code"]:
        return ("YYC / codigo nativo detectado (chunk CODE ausente o vacio). "
                "Cinnamon NO puede ejecutar este archivo tal cual; hace falta la build VM de otra plataforma.")
    if info["bytecode_version"] in CINNAMON_BYTECODE_VERSIONS:
        return (f"COMPATIBLE (probable): bytecode v{info['bytecode_version']}, "
                f"CODE presente ({info['code_length']:,} bytes).")
    return (f"Bytecode v{info['bytecode_version']} no soportado por Cinnamon "
            f"(solo soporta v16 y v17).")


def print_report(info):
    print(f"\n=== {info['path']} ===")
    print(f"Tamano: {info['size']:,} bytes")
    print(f"Nombre interno: {info['name']!r}")
    print(f"Nombre mostrado: {info['display_name']!r}")
    print(f"Chunks ({len(info['chunks'])}): " + ", ".join(f"{n}:{l}" for n, l in info["chunks"]))
    print(f"Bytecode version: {info['bytecode_version']}")
    print(f"Veredicto: {verdict(info)}")


def find_embedded_form_offsets(path, chunk_size=8 * 1024 * 1024):
    needle = b"FORM"
    with open(path, "rb") as f:
        prev_tail = b""
        base_offset = 0
        while True:
            block = f.read(chunk_size)
            if not block:
                break
            haystack = prev_tail + block
            search_start = 0
            while True:
                idx = haystack.find(needle, search_start)
                if idx == -1:
                    break
                yield base_offset - len(prev_tail) + idx
                search_start = idx + 1
            prev_tail = block[-3:]
            base_offset += len(block)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="Archivo o carpeta a analizar (p.ej. un VPK descomprimido)")
    parser.add_argument("--deep", action="store_true",
                         help="Busca la firma FORM embebida dentro de binarios grandes (eboot.bin, etc)")
    parser.add_argument("--min-size", type=int, default=1_000_000,
                         help="Tamano minimo en bytes para escanear un archivo en modo --deep (default 1MB)")
    args = parser.parse_args()

    if os.path.isdir(args.path):
        targets = [os.path.join(r, n) for r, _, fs in os.walk(args.path) for n in fs]
    else:
        targets = [args.path]

    found_any = False
    for path in targets:
        try:
            with open(path, "rb") as f:
                head = f.read(4)
        except OSError:
            continue

        if head == b"FORM":
            found_any = True
            print_report(scan_data_win(path))
        elif args.deep and os.path.getsize(path) >= args.min_size:
            offsets = list(find_embedded_form_offsets(path))
            if offsets:
                found_any = True
                print(f"\n=== {path} (firma FORM embebida, no es un data.win independiente) ===")
                for off in offsets:
                    print(f"  Candidato en offset {off} (0x{off:x})")
                print("  Extrae ese rango a un archivo aparte (dd/binwalk) y volve a correr el script sobre el.")

    if not found_any:
        print("No se encontro ningun archivo con firma FORM (data.win de GameMaker).")
        print("Proba con --deep si el juego viene empaquetado dentro de un binario mas grande (eboot.bin, etc).")


if __name__ == "__main__":
    main()
