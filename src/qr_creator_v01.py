from __future__ import annotations
from pathlib import Path
from typing import Optional, Tuple, Union
import argparse
import logging

from PIL import Image, ImageDraw, ImageColor
import qrcode
from qrcode.constants import ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H

# Optional pyzbar for QR validation
try:
    from pyzbar.pyzbar import decode as _zbar_decode
    _PYZBAR_OK = True
except Exception:
    _PYZBAR_OK = False

VCARD_EOL = "\r\n"

ColorLike = Union[str, Tuple[int, int, int], Tuple[int, int, int, int]]

logger = logging.getLogger("qrlogo")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def _escape_vcard(s: Optional[str]) -> str:
    if not s:
        return ""
    return (s.replace("\\", "\\\\")
             .replace("\r\n", "\\n")
             .replace("\n", "\\n")
             .replace(";", r"\;")
             .replace(",", r"\,"))


def _normalize_color(c: ColorLike) -> Tuple[int, int, int]:
    """Normalize color to RGB tuple; alpha (if any) is ignored for QR modules."""
    try:
        rgb = ImageColor.getrgb(c)  # supports names, hex, tuples
        return rgb[:3] if isinstance(rgb, tuple) and len(rgb) > 3 else rgb  # type: ignore
    except Exception as e:
        raise ValueError(f"Invalid color '{c}': {e}") from e


def _max_safe_logo_ratio(ec_level: int, modules_count: int) -> float:
    """
    Heuristic 'safe' cap for central overlay.
    - Higher EC allows larger center cover.
    - Denser codes (larger modules_count) reduce cap slightly.
    Typical conservative caps (center square equivalent):
      L≈0.12, M≈0.15, Q≈0.18, H≈0.22  (converted to linear ratio on min side)
    """
    base = {ERROR_CORRECT_L: 0.12, ERROR_CORRECT_M: 0.15,
            ERROR_CORRECT_Q: 0.18, ERROR_CORRECT_H: 0.22}.get(ec_level, 0.18)
    penalty = 0.0
    if modules_count >= 45:       # ~version 10+
        penalty = 0.03
    elif modules_count >= 33:     # ~version 6–9
        penalty = 0.02
    return max(0.08, base - penalty)


def _rounded_rect(draw: ImageDraw.ImageDraw, xy, radius: int, fill, outline=None, width: int = 1):
    x0, y0, x1, y1 = xy
    w, h = x1 - x0, y1 - y0
    r = max(0, min(radius, min(w, h) // 2))
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill, outline=outline, width=width)


def build_vcard(
    given_name: str = "",
    family_name: str = "",
    org: str = "",
    title: str = "",
    phones: Optional[list[str]] = None,
    emails: Optional[list[str]] = None,
    url: str = "",
    street: str = "",
    city: str = "",
    region: str = "",
    postal: str = "",
    country: str = "",
    note: str = "",
    version: str = "3.0",
) -> str:
    """
    Build a vCard payload (default: v3.0) with CRLF line endings.
    Returns the full string ready for QR encoding.
    """
    phones = phones or []
    emails = emails or []

    gn = _escape_vcard(given_name)
    fn = _escape_vcard(family_name)
    org_e = _escape_vcard(org)
    title_e = _escape_vcard(title)
    street_e = _escape_vcard(street)
    city_e = _escape_vcard(city)
    region_e = _escape_vcard(region)
    postal_e = _escape_vcard(postal)
    country_e = _escape_vcard(country)
    url_e = _escape_vcard(url)
    note_e = _escape_vcard(note)

    lines = [
        "BEGIN:VCARD",
        f"VERSION:{version}",
        f"N:{fn};{gn};;;",
        f"FN:{gn} {fn}".strip(),
    ]
    if org_e:
        lines.append(f"ORG:{org_e}")
    if title_e:
        lines.append(f"TITLE:{title_e}")
    for p in phones:
        p = (p or "").strip()
        if p:
            lines.append(f"TEL;TYPE=CELL,VOICE:{p}")
    for e in emails:
        e = (e or "").strip()
        if e:
            lines.append(f"EMAIL;TYPE=INTERNET:{e}")
    if any([street_e, city_e, region_e, postal_e, country_e]):
        adr = f";;{street_e};{city_e};{region_e};{postal_e};{country_e}"
        lines.append(f"ADR;TYPE=WORK:{adr}")
    if url_e:
        lines.append(f"URL:{url_e}")
    if note_e:
        lines.append(f"NOTE:{note_e}")
    lines.append("END:VCARD")
    return VCARD_EOL.join(lines) + VCARD_EOL  # trailing CRLF improves compatibility


# Helper for QR validation via pyzbar
def _can_decode(img: Image.Image) -> bool:
    """Return True if we can decode the QR content from the given PIL image."""
    if not _PYZBAR_OK:
        logger.warning("pyzbar non disponibile: salto validazione QR.")
        return True  # cannot validate, don't block
    try:
        res = _zbar_decode(img)
        return bool(res and res[0] and res[0].data)
    except Exception as e:
        logger.warning(f"Errore decodifica per validazione: {e}")
        return False


def create_qr_with_logo(
    data: str,
    logo_path: Union[str, Path],
    output_filename: Optional[Union[str, Path]] = "qr_with_logo.png",
    fill_color: ColorLike = "black",
    back_color: ColorLike = "white",
    logo_size_ratio: float = 0.18,
    box_size: int = 12,
    border_size: int = 4,
    error_correction: int = ERROR_CORRECT_H,
    logo_pad_px: int = 8,
    logo_bg_opacity: int = 255,
    logo_bg_radius: int = 12,
    logo_bg_outline: Optional[ColorLike] = (0, 0, 0),
    logo_bg_outline_width: int = 2,
    open_after: bool = False,
) -> Image.Image:
    """
    Create a QR code with a centrally overlaid logo and return the PIL Image.
    Saves to disk if output_filename is provided.

    Parameters are validated; logo size is clamped to a conservative 'safe' cap
    derived from error correction level and code density.
    box_size controls the pixel size per QR module (higher = higher resolution).
    """
    if not data:
        raise ValueError("No data provided for QR code.")
    logo_path = Path(logo_path)
    if not logo_path.exists():
        raise FileNotFoundError(f"Logo file not found: {logo_path}")

    # Normalize colors
    fill_rgb = _normalize_color(fill_color)
    back_rgb = _normalize_color(back_color)

    # Pre-clamp for dense contact payloads (before constructing the QR so border applies)
    dat_upper = data.strip().upper()
    if dat_upper.startswith("BEGIN:VCARD"):
        if logo_size_ratio > 0.16:
            logger.info("vCard detected: clamping logo_size_ratio to 0.16 for better readability.")
            logo_size_ratio = 0.16
        border_size = max(border_size, 4)
    elif dat_upper.startswith("MECARD:"):
        if logo_size_ratio > 0.18:
            logger.info("MECARD detected: clamping logo_size_ratio to 0.18 for better readability.")
            logo_size_ratio = 0.18
        border_size = max(border_size, 4)

    # Build QR (let 'fit=True' pick version based on data)
    qr = qrcode.QRCode(
        version=None,  # auto
        error_correction=error_correction,
        box_size=box_size,
        border=border_size,
    )
    qr.add_data(data)
    qr.make(fit=True)

    modules_count = qr.modules_count  # number of modules on a side
    safe_cap = _max_safe_logo_ratio(error_correction, modules_count)
    # Extra safety cap for central overlay
    safe_cap = min(safe_cap, 0.20)
    if logo_size_ratio > safe_cap:
        logger.warning(f"Logo ratio {logo_size_ratio:.2f} exceeds safe cap {safe_cap:.2f}; clamping.")
    logo_size_ratio = max(0.08, min(logo_size_ratio, safe_cap))

    # Create image
    qr_image = qr.make_image(fill_color=fill_rgb, back_color=back_rgb).convert("RGBA")
    qr_w, qr_h = qr_image.size

    # Load logo (RGBA)
    try:
        logo = Image.open(logo_path).convert("RGBA")
    except Exception as e:
        raise RuntimeError(f"Error loading logo: {e}") from e

    # Resize logo keeping aspect ratio
    max_side = int(min(qr_w, qr_h) * logo_size_ratio)
    lw, lh = logo.size
    aspect = lw / lh
    if aspect >= 1.0:
        new_w = max_side
        new_h = int(round(max_side / aspect))
    else:
        new_h = max_side
        new_w = int(round(max_side * aspect))
    logo = logo.resize((new_w, new_h), Image.Resampling.LANCZOS)

    # Compute centered box for background + logo
    cx = (qr_w - new_w) // 2
    cy = (qr_h - new_h) // 2
    bg_x0 = max(0, cx - max(0, logo_pad_px))
    bg_y0 = max(0, cy - max(0, logo_pad_px))
    bg_x1 = min(qr_w, cx + new_w + max(0, logo_pad_px))
    bg_y1 = min(qr_h, cy + new_h + max(0, logo_pad_px))

    # Draw rounded white background with optional outline
    overlay = Image.new("RGBA", (qr_w, qr_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    fill_rgba = (*_normalize_color("white"), max(0, min(255, logo_bg_opacity)))
    outline_rgb = _normalize_color(logo_bg_outline) if logo_bg_outline is not None else None
    _rounded_rect(d, (bg_x0, bg_y0, bg_x1, bg_y1), radius=logo_bg_radius, fill=fill_rgba,
                  outline=outline_rgb, width=logo_bg_outline_width)

    # Composite background first (preserves QR alpha)
    qr_image = Image.alpha_composite(qr_image, overlay)
    # Paste logo using its alpha
    qr_image.paste(logo, (cx, cy), logo)

    final_img = qr_image.convert("RGB")

    # Save if requested
    if output_filename:
        out = Path(output_filename)
        final_img.save(out, "PNG", optimize=True)
        logger.info(f"Saved: {out}  | QR {qr_w}x{qr_h}  | Logo {new_w}x{new_h}  | Ratio {logo_size_ratio:.2f}")

        if open_after:
            import os, sys
            try:
                if sys.platform.startswith('darwin'):
                    os.system(f'open "{out}"')
                elif sys.platform.startswith('win'):
                    os.system(f'start "" "{out}"')
                elif sys.platform.startswith('linux'):
                    os.system(f'xdg-open "{out}"')
            except Exception as e:
                logger.warning(f"Auto-open failed: {e}")

    return final_img


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="QR Code Generator with centered logo/watermark")
    p.add_argument("--data", required=False, default=None, help="Data (URL/testo) da codificare")
    p.add_argument("--logo", required=False, default=None, help="Percorso file logo (PNG consigliato)")
    p.add_argument("--out", default="qr_with_logo.png", help="Output PNG")
    p.add_argument("--fill", default="black", help="Colore moduli (es. black, #000000)")
    p.add_argument("--back", default="white", help="Colore sfondo")
    p.add_argument("--ratio", type=float, default=0.18, help="Logo size ratio (0.08–0.22 tipico con H)")
    p.add_argument("--box", type=int, default=12, help="Pixel size per modulo (aumenta la risoluzione)")
    p.add_argument("--border", type=int, default=4, help="Quiet zone in moduli (default 4)")
    p.add_argument("--ec", choices=["L", "M", "Q", "H"], default="H", help="Error correction level")
    p.add_argument("--pad", type=int, default=8, help="Padding (px) attorno al logo")
    p.add_argument("--bg_opacity", type=int, default=255, help="Opacità sfondo logo (0–255)")
    p.add_argument("--bg_radius", type=int, default=12, help="Raggio angoli sfondo")
    p.add_argument("--no_outline", action="store_true", help="Disabilita bordo sfondo logo")
    p.add_argument("--open", action="store_true", help="Apri il file a fine generazione")
    p.add_argument("--interactive", action="store_true", help="Avvia procedura guidata interattiva")
    p.add_argument("--vcard", action="store_true", help="Attiva modalità vCard (ignora --data)")
    p.add_argument("--first_name", default=None, help="Nome (vCard)")
    p.add_argument("--last_name", default=None, help="Cognome (vCard)")
    p.add_argument("--org", default=None, help="Azienda (vCard)")
    p.add_argument("--title", default=None, help="Ruolo/Titolo (vCard)")
    p.add_argument("--phone", default=None, help="Telefono (obbligatorio in modalità vCard)")
    p.add_argument("--email", default=None, help="Email (obbligatoria in modalità vCard)")
    p.add_argument("--url", default=None, help="URL sito (vCard)")
    p.add_argument("--street", default=None, help="Indirizzo (via) (vCard)")
    p.add_argument("--city", default=None, help="Città (vCard)")
    p.add_argument("--region", default=None, help="Provincia/Regione (vCard)")
    p.add_argument("--postal", default=None, help="CAP (vCard)")
    p.add_argument("--country", default=None, help="Paese (vCard)")
    p.add_argument("--note", default=None, help="Nota (vCard)")
    p.add_argument("--from_file", default=None, help="Legge il payload da file (sovrascrive --data)")
    # Validation/auto-tune flags
    p.add_argument("--validate", action="store_true", help="Valida il QR decodificandolo dopo la generazione")
    p.add_argument("--auto_tune", action="store_true", help="Se la validazione fallisce, riduce il logo ratio a step di 0.02 fino a 0.12")
    return p.parse_args()


def interactive_wizard() -> argparse.Namespace:
    print("=== QR Code Generator (procedura guidata) ===\n")
    mode = input("Modalità [1=Link/Testo, 2=vCard]: ").strip() or "1"

    if mode == "2":
        print("\n-- vCard -- (Obbligatori: Nome, Cognome, Telefono, Email, URL)")
        first_name = input("Nome (obbligatorio): ").strip()
        last_name = input("Cognome (obbligatorio): ").strip()
        while not (first_name and last_name):
            print("⚠️  Nome e Cognome sono obbligatori.")
            first_name = input("Nome (obbligatorio): ").strip()
            last_name = input("Cognome (obbligatorio): ").strip()

        org = input("Azienda (facoltativo): ").strip()
        title = input("Ruolo/Titolo (facoltativo): ").strip()

        phone = input("Telefono (obbligatorio): ").strip()
        while not phone:
            print("⚠️  Telefono obbligatorio.")
            phone = input("Telefono (obbligatorio): ").strip()
        phones = [phone]

        email = input("Email (obbligatoria): ").strip()
        while not email:
            print("⚠️  Email obbligatoria.")
            email = input("Email (obbligatoria): ").strip()
        emails = [email]

        urlv = input("URL (obbligatorio): ").strip()
        while not urlv:
            print("⚠️  URL obbligatorio.")
            urlv = input("URL (obbligatorio): ").strip()

        street = input("Indirizzo (via) [facoltativo]: ").strip()
        city = input("Città [facoltativo]: ").strip()
        region = input("Provincia/Regione [facoltativo]: ").strip()
        postal = input("CAP [facoltativo]: ").strip()
        country = input("Paese [facoltativo]: ").strip()
        note = input("Nota (una riga) [facoltativo]: ").strip()

        # Costruisci payload vCard
        data = build_vcard(
            given_name=first_name, family_name=last_name, org=org, title=title,
            phones=phones, emails=emails, url=urlv, street=street, city=city,
            region=region, postal=postal, country=country, note=note, version="3.0"
        )
    else:
        data = input("Dati da codificare (URL/testo): ").strip()
        while not data:
            print("⚠️  Campo obbligatorio.")
            data = input("Dati da codificare (URL/testo): ").strip()

    logo = input("Percorso file logo (PNG consigliato): ").strip()
    while not logo:
        print("⚠️  Campo obbligatorio.")
        logo = input("Percorso file logo (PNG consigliato): ").strip()

    out = input("Nome file output [qr_with_logo.png]: ").strip() or "qr_with_logo.png"
    fill = input("Colore moduli [black]: ").strip() or "black"
    back = input("Colore sfondo [white]: ").strip() or "white"

    def _ask_float(prompt, default, lo, hi):
        raw = input(f"{prompt} [{default}]: ").strip()
        if not raw:
            return default
        try:
            val = float(raw)
        except ValueError:
            print(f"Valore non valido, uso default {default}")
            return default
        return max(lo, min(hi, val))

    ratio = _ask_float("Logo size ratio (0.08–0.22 tipico con H)", 0.18, 0.08, 0.30)

    def _ask_int(prompt, default, lo, hi):
        raw = input(f"{prompt} [{default}]: ").strip()
        if not raw:
            return default
        try:
            val = int(raw)
        except ValueError:
            print(f"Valore non valido, uso default {default}")
            return default
        return max(lo, min(hi, val))

    box = _ask_int("Pixel per modulo (box size)", 12, 4, 32)
    border = _ask_int("Quiet zone (moduli)", 4, 1, 16)
    pad = _ask_int("Padding (px) attorno al logo", 8, 0, 128)
    bg_opacity = _ask_int("Opacità sfondo logo (0-255)", 255, 0, 255)
    bg_radius = _ask_int("Raggio angoli sfondo", 12, 0, 128)

    ec = input("Error correction [H/L/M/Q]: ").strip().upper() or "H"
    if ec not in {"L","M","Q","H"}:
        print("Valore non valido, uso H")
        ec = "H"

    no_outline_ans = input("Bordo sfondo logo? (s/N): ").strip().lower()
    no_outline = (no_outline_ans == "n")  # default bordo ON; 'n' per disabilitare

    open_ans = input("Aprire il file a fine generazione? (S/n): ").strip().lower()
    open_flag = (open_ans != "n")

    val_ans = input("Validare il QR dopo la generazione? (S/n): ").strip().lower()
    validate = (val_ans != "n")
    at_ans = input("Auto-tune del logo se la validazione fallisce? (S/n): ").strip().lower()
    auto_tune = (at_ans != "n")

    # Costruisce un namespace compatibile con argparse
    ns = argparse.Namespace(
        data=data, logo=logo, out=out, fill=fill, back=back, ratio=ratio,
        box=box,
        border=border, ec=ec, pad=pad, bg_opacity=bg_opacity, bg_radius=bg_radius,
        no_outline=no_outline, open=open_flag, interactive=True, vcard=(mode == "2"),
        first_name=(first_name if mode == "2" else None),
        last_name=(last_name if mode == "2" else None),
        org=(org if mode == "2" else None),
        title=(title if mode == "2" else None),
        phone=(phones if mode == "2" else None),
        email=(emails if mode == "2" else None),
        url=(urlv if mode == "2" else None),
        street=(street if mode == "2" else None),
        city=(city if mode == "2" else None),
        region=(region if mode == "2" else None),
        postal=(postal if mode == "2" else None),
        country=(country if mode == "2" else None),
        note=(note if mode == "2" else None),
        from_file=None,
        validate=validate, auto_tune=auto_tune,
    )
    return ns


def main():
    args = _parse_args()

    # Wizard solo se richiesto esplicitamente o se manca input essenziale (non in vCard CLI completa)
    if args.interactive or (((not args.logo) and not args.vcard) or ((not args.data) and not args.vcard)):
        args = interactive_wizard()

    ec_map = {"L": ERROR_CORRECT_L, "M": ERROR_CORRECT_M, "Q": ERROR_CORRECT_Q, "H": ERROR_CORRECT_H}
    outline = None if args.no_outline else "black"

    # vCard mode: se mancano i 5 obbligatori e non c'è già un payload vCard, attiva wizard
    if args.vcard and not (args.data and isinstance(args.data, str) and args.data.strip().upper().startswith("BEGIN:VCARD")):
        required_missing = not all([args.first_name, args.last_name, args.phone, args.email, args.url])
        if required_missing:
            print("Modalità vCard: raccolgo i dati obbligatori mancanti…")
            args = interactive_wizard()
            outline = None if args.no_outline else "black"

    # Determina il payload finale
    payload = None
    if args.from_file:
        path = Path(args.from_file)
        if not path.exists():
            raise FileNotFoundError(f"File non trovato: {path}")
        payload = path.read_text(encoding="utf-8")
    elif args.vcard:
        if args.data and isinstance(args.data, str) and args.data.strip().upper().startswith("BEGIN:VCARD"):
            payload = args.data  # vCard già pronta
        else:
            phones = ([args.phone] if isinstance(args.phone, str) else (args.phone or []))
            emails = ([args.email] if isinstance(args.email, str) else (args.email or []))
            payload = build_vcard(
                given_name=args.first_name or "",
                family_name=args.last_name or "",
                org=args.org or "",
                title=args.title or "",
                phones=phones,
                emails=emails,
                url=args.url or "",
                street=args.street or "",
                city=args.city or "",
                region=args.region or "",
                postal=args.postal or "",
                country=args.country or "",
                note=args.note or "",
                version="3.0",
            )
    else:
        # Se --data punta a un file esistente, leggilo
        if args.data and Path(args.data).exists():
            payload = Path(args.data).read_text(encoding="utf-8")
        else:
            payload = args.data

    # Validation/auto-tune support
    ratio = args.ratio
    ok = False
    last_img = None
    while True:
        last_img = create_qr_with_logo(
            data=payload,
            logo_path=args.logo,
            output_filename=args.out,
            fill_color=args.fill,
            back_color=args.back,
            logo_size_ratio=ratio,
            box_size=args.box,
            border_size=args.border,
            error_correction=ec_map[args.ec],
            logo_pad_px=args.pad,
            logo_bg_opacity=args.bg_opacity,
            logo_bg_radius=args.bg_radius,
            logo_bg_outline=outline,
            open_after=args.open and not getattr(args, "validate", False),  # apri dopo se non validi
        )
        if getattr(args, "validate", False):
            ok = _can_decode(last_img)
            if ok or not getattr(args, "auto_tune", False) or ratio <= 0.12:
                break
            # ritenta con ratio inferiore
            ratio = max(0.12, round(ratio - 0.02, 2))
            logger.warning(f"Validazione fallita, nuovo tentativo con ratio={ratio:.2f}")
        else:
            ok = True
            break
    if getattr(args, "validate", False):
        if ok:
            logger.info("✅ Validazione OK: QR decodificabile.")
            if args.open:
                # apri ora se richiesto
                try:
                    import os, sys
                    if sys.platform.startswith('darwin'):
                        os.system(f'open "{args.out}"')
                    elif sys.platform.startswith('win'):
                        os.system(f'start "" "{args.out}"')
                    elif sys.platform.startswith('linux'):
                        os.system(f'xdg-open "{args.out}"')
                except Exception as e:
                    logger.warning(f"Auto-open fallito: {e}")
        else:
            logger.error("❌ Validazione fallita anche dopo auto-tune. Prova a ridurre il logo o aumentare box/border.")


if __name__ == "__main__":
    main()


'''
python qr_creator.py --vcard \
  --first_name "Mario" --last_name "Rossi" \
  --phone "+39333111222" --email "m.rossi@acme.it" --url "https://acme.it" \
  --logo logo.png --ratio 0.16 --box 14 --border 4 --ec H --validate --auto_tune
  
  Wizard:
  python qr_creator.py --interactive
# scegli 2=vCard – chiede Nome, Cognome, Telefono, Email, URL una sola volta
'''