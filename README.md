# Gestione condominio

Piccolo programma Python per gestire un condominio con un modello a oggetti:

- `Condominio`: contiene gli appartamenti.
- `Appartamento`: contiene dati dell'unita immobiliare, condomino residente, note e movimenti.
- `Condomino`: contiene i dati anagrafici del residente.
- `Movimento`: rappresenta spese e pagamenti.

## Avvio

Esegui:

```bash
/home/mattegiorgi/docs/tassi_istat/.venv/bin/python condominio.py
```

Il programma salva automaticamente i dati in `condominio_data.json` nella stessa cartella.

## Funzioni principali

- inserimento degli appartamenti
- assegnazione del condomino all'appartamento
- registrazione di addebiti e pagamenti
- visualizzazione del saldo per appartamento e del totale del condominio
- consultazione del dettaglio completo di un appartamento