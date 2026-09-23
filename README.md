# Voorraadwacht

Volgt de voorraad van elektronicacomponenten op bij Europese distributeurs, mailt als die
verandert, en houdt je eigen bestellingen bij (waar, hoeveel, kostprijs, levertermijn,
verwachte leverdatum).

## Hoe het werkt

```
 Webinterface (Flask)  ──►  SQLite-database  ◄──  Planner (elk uur)
   componenten                                       │
   bestellingen                                      ▼
                                          Leveranciers-API's ──► wijziging? ──► e-mail
                                          Mouser · Farnell · TME · DigiKey
```

- **Voorraad ophalen gebeurt via de officiële API's** van de leveranciers, niet door
  webpagina's te scrapen. Scrapen breekt bij elke website-update en is meestal verboden
  door de gebruiksvoorwaarden; de API's zijn gratis en geven voorraad, prijs en levertermijn.
- Een e-mail wordt verstuurd wanneer een component **uitverkocht** raakt, **terug op
  voorraad** komt, onder je **alarmdrempel** zakt, of meer dan `NOTIFY_MIN_CHANGE_PCT` %
  wijzigt. Alle wijzigingen van één controle komen in één mail, samen met je openstaande
  bestellingen voor dat component.
- Bestellingen: de verwachte leverdatum = besteldatum + levertermijn (of zelf in te vullen).
  Het overzicht toont wat eraan komt en wat te laat is.

## Installeren

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # en vul in
flask --app voorraadwacht run --host 0.0.0.0 --port 8000
```

Open http://localhost:8000. Zonder API-sleutels kan je alles uitproberen met de
*Demo-leverancier*.

Of met Docker:

```bash
docker build -t voorraadwacht .
docker run -d --env-file .env -p 8000:8000 -v voorraadwacht-data:/data voorraadwacht
```

Laat het draaien op een pc/server/NAS die altijd aan staat, binnen het bedrijfsnetwerk,
en stel `BASIC_AUTH_USER`/`BASIC_AUTH_PASSWORD` in.

Handmatig of via cron/Taakplanner controleren kan ook (zet dan `SCHEDULER_ENABLED=false`):

```bash
flask --app voorraadwacht check
```

## API-sleutels aanvragen

| Leverancier | Waar | In `.env` |
|---|---|---|
| Mouser | mouser.be → *My Mouser* → *APIs* → Search API | `MOUSER_API_KEY` |
| Farnell | partner.element14.com (registreren, key aanmaken) | `FARNELL_API_KEY`, `FARNELL_STORE` |
| TME | developers.tme.eu → applicatie aanmaken | `TME_TOKEN`, `TME_SECRET` |
| DigiKey | developer.digikey.com → organisatie + app (Product Information v4) | `DIGIKEY_CLIENT_ID`, `DIGIKEY_CLIENT_SECRET` |

Zonder leveranciersnummer wordt op het fabrikant-artikelnummer (MPN) gezocht. Geef bij TME
best het TME-symbool op, en bij meerdere verpakkingen (tape/reel, cut tape) het exacte
bestelnummer.

Een extra leverancier toevoegen (bv. RS, Conrad, Reichelt): maak een klasse in
`voorraadwacht/providers/` met een `fetch(mpn, supplier_sku)` die een `StockInfo` teruggeeft
en voeg die toe aan `PROVIDER_CLASSES`.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```
