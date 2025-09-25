# Sicurezza dei QR Code: Linee guida per Aziende e Utenti

I QR code sono oggi ovunque: pagamenti, pubblicità, logistica, packaging, eventi. 
Sono strumenti potenti, ma anche un vettore semplice per phishing, frodi e malware.

Questo documento raccoglie le best practice operative sia per **aziende** (che creano e distribuiscono QR) sia per **utenti**.

---

## Rischi principali

- **Sostituzione fisica / QR-jacking**: adesivi fraudolenti coprono QR originali.  
- **Phishing**: il QR porta a un sito clone che ruba credenziali o dati di pagamento.  
- **Manomissione link**: URL abbreviati che reindirizzano a payload o frodi.  
- **Malware**: download di app/file malevoli.  
- **Configurazioni automatiche**: QR che imposta Wi-Fi, invia SMS, crea contatti.  
- **Tracciamento illecito**: raccolta dati senza consenso.  

---

## Linee guida per le Aziende (lato marketing / distribuzione)

### Prima della stampa
- Usare sempre un **redirect layer** controllato: `qr.azienda.it/<id>`  
- Generare **QR univoci per lotto/posizione**, revocabili in tempo reale.  
- Applicare **expiry e rate limiting** sui link.  
- Usare **HTTPS + HSTS** e mostrare il dominio vicino al QR in chiaro.  
- Incorporare **microtesto/logo** o elementi grafici anti-clonazione.  
- Effettuare **security review** delle landing e dei fornitori di pagamento.  
- Prevedere un **canale di segnalazione pubblico** per utenti che notano anomalie.  

### Landing e infrastruttura
- Landing minimale: nessuna richiesta di credenziali subito.  
- Autenticazione a due fattori se necessario il login.  
- **Input validation, CSP, WAF** attivi.  
- Logging e alerting su anomalie di traffico.  
- Per pagamenti: usare **gateway certificati** con callback firmati.  

### Difese fisiche / operative
- Stampa controllata, distribuzione tracciata.  
- Sigilli, lamine olografiche, superfici difficili da coprire.  
- Ispezioni fisiche programmate nei luoghi ad alto rischio.  


### Policy breve da inserire in brief marketing
Tutti i QR destinati a distribuzione fisica devono essere generati tramite il sistema aziendale di QR dinamici, assegnati ad un ID univoco per lotto/posizione, avere scadenza prefissata e poter essere revocati immediatamente. La pagina di destinazione deve essere minimizzata, servita via HTTPS con controllo CSP e non richiedere credenziali al primo accesso. È vietata la stampa di QR con URL finale non gestito dal redirect layer aziendale.

### Incident Response (se abuso)
1. Revocare il QR compromesso.  
2. Bloccare o modificare la landing.  
3. Avvisare utenti tramite canali ufficiali.  
4. Effettuare audit fisico e raccolta prove.  
5. Report e revisione procedure.  

---

## Linee guida per gli Utenti.

### Rischi concreti
- Phishing e siti clone.  
- Frodi di pagamento.  
- Malware o app sospette.  
- Configurazioni automatiche non richieste.  

### Buone pratiche
1. **Controllare l’URL** prima di aprirlo (anteprima della fotocamera).  
2. **Diffidare di QR adesivi** o messi in posti sospetti.  
3. **Non inserire credenziali** subito dopo la scansione.  
4. Usare app di scansione sicure (fotocamera integrata).  
5. Nei pagamenti: verificare sempre beneficiario e importo.  
6. Non installare app da link QR → solo da store ufficiali.  
7. Tenere telefono e antivirus aggiornati.  
8. Attivare conferma manuale per apertura link esterni.  

### Regola d’oro
> “Il QR è come un link accorciato stampato. Prima guarda dove porta, poi decidi se fidarti.”  

---

## Conclusione

- Per le aziende: un QR ben gestito è un canale di marketing efficace e sicuro.  
- Per gli utenti: uno sguardo critico e due secondi in più evitano una trappola.  

La **comodità non deve far dimenticare la sicurezza**.  

---

