# QR Code Generator con Logo e Supporto vCard

Script Python per la generazione di QR code personalizzati con logo, compatibile con link, testi e contatti digitali in formato vCard (business card QR). Progettato per l'utilizzo da parte sia di utenti esperti che non esperti, grazie a un'interfaccia guidata.

---

## 📁 File inclusi

| File                | Descrizione                                 |
|---------------------|---------------------------------------------|
| `qr_creator_v01.py` | Script principale CLI e interfaccia guidata |
| `qr_link.py`        | generazione QR code con link                |

---

## 🔧 Requisiti

Installa i moduli necessari con:

```bash
pip install qrcode[pil] pillow
```

### Example:
```
python qr_creator_v01.py --data "https://esempio.com" --logo logo.png

python qr_creator_v01.py --vcard \
  --first-name "Mario" --last-name "Rossi" \
  --phone "+39333111222" \
  --email "mario.rossi@email.it" \
  --url "https://mariorossi.it" \
  --logo logo.png

# 🧩 QR Code Generator con Logo e Supporto vCard

Sistema completo per la generazione di QR code personalizzati con logo sovrapposto, compatibile sia con link che con dati vCard (biglietto da visita digitale). Include modalità interattiva guidata per utenti non esperti.

---

## 📦 File inclusi

| File                | Descrizione                                                      |
|---------------------|------------------------------------------------------------------|
| `qr_creator_v01.py` | Script CLI completo: link, vCard, modalità interattiva           |
| `qr_link.py`        | Script base per QR code da link con logo                         |
| `logo.png`          | Esempio di logo da utilizzare nei QR code                        |
| `requirements.txt`  | Dipendenze minime da installare con `pip`                        |

---

## ⚙️ Requisiti

Installa i moduli richiesti con:

```bash
pip install -r requirements.txt
```

---

## 🚀 Utilizzo rapido

### ➤ QR code da link:

```bash
python qr_creator_v01.py --data "https://esempio.com" --logo logo.png
```

### ➤ QR code vCard (biglietto da visita):

```bash
python qr_creator_v01.py --vcard \
  --first-name "Mario" --last-name "Rossi" \
  --phone "+39333111222" \
  --email "mario.rossi@email.it" \
  --url "https://mariorossi.it" \
  --logo logo.png
```

---

## 💡 Modalità interattiva

Se non fornisci argomenti da CLI, lo script `qr_creator_v01.py` avvierà automaticamente una procedura guidata che ti chiederà:

- Nome, Cognome, Telefono, Email, URL (obbligatori per vCard)
- Altri dati opzionali (Azienda, Ruolo, Indirizzo, Note)
- Scelta file logo
- Nome file di output

---

## ✅ Output

- File PNG con QR code generato
- Logo centrato e visibile
- Compatibilità con lettori QR moderni (vCard o link)

---

## 📄 Licenza

Questo progetto è distribuito con licenza MIT.