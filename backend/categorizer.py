"""
BlickPUNKT Archiv – Kategorisierung
Ordnet Artikel automatisch Kategorien zu (regelbasiert).
Optional mit KI-Unterstützung.
"""

import re
import os
import json
import logging

logger = logging.getLogger(__name__)

# Kategorie-Regeln: Schlüsselwörter → Kategorie
CATEGORY_RULES = {
    "Menschen & Porträts": {
        "keywords": ["porträt", "portrait", "interview", "persönlich", "lebensgeschichte",
                      "jubilar", "ehrenamt", "geehrt", "ausgezeichnet", "engagement"],
        "subcategories": {
            "Vereinsmenschen": ["vereinsvorsitzender", "ehrenamtlich", "vereinsleben"],
            "Unternehmerporträts": ["unternehmer", "geschäftsführer", "gründer", "firmenchef"],
            "Ehrenamt": ["ehrenamt", "freiwillig", "engagement", "ehrenamtlich"],
            "Jubilare": ["jubilar", "geburtstag", "jubiläum", "gratulation", "100 jahre"],
            "Familiengeschichten": ["familie", "generation", "familienbetrieb"],
            "Leserporträts": ["leser", "leserbrief", "leserin"],
        }
    },
    "Vereine & Ehrenamt": {
        "keywords": ["verein", "vereins", "ehrenamt", "mitglieder", "vorstand",
                      "jahreshauptversammlung", "satzung"],
        "subcategories": {
            "Sportvereine": ["sportverein", "fußball", "handball", "tennis", "turnen",
                             "leichtathletik", "schwimmen", "sv ", "tus ", "vfl "],
            "Schützenvereine": ["schützenverein", "schützenfest", "königin", "könig",
                                "schießen", "schützen"],
            "Kulturvereine": ["kulturverein", "theater", "musik", "chor", "orchester",
                              "plattdeutsch", "heimatverein"],
            "Feuerwehr": ["feuerwehr", "freiwillige feuerwehr", "brandschutz",
                          "jugendfeuerwehr", "löschzug"],
            "DRK / soziale Gruppen": ["drk", "rotes kreuz", "sozialverband", "awo",
                                       "caritas", "diakonie"],
            "Fördervereine": ["förderverein", "unterstützung", "spende"],
        }
    },
    "Veranstaltungen": {
        "keywords": ["veranstaltung", "fest", "feier", "markt", "konzert",
                      "programm", "einladung", "termin"],
        "subcategories": {
            "Feste": ["fest", "feier", "party", "volksfest"],
            "Märkte": ["markt", "flohmarkt", "bauernmarkt", "wochenmarkt"],
            "Konzerte": ["konzert", "musik", "auftritt", "band"],
            "Sportevents": ["turnier", "lauf", "meisterschaft", "wettkampf"],
            "Jubiläen": ["jubiläum", "jahrestag", "bestehen"],
            "Saisonveranstaltungen": ["saisonstart", "eröffnung", "saisonal"],
            "Hafenfest / Stadtfest / Weihnachtsmarkt": [
                "hafenfest", "stadtfest", "weihnachtsmarkt",
                "gallimarkt", "kram- und viehmarkt"
            ],
        }
    },
    "Region & Heimat": {
        "keywords": ["heimat", "geschichte", "tradition", "plattdeutsch", "dorf",
                      "region", "fehn", "moor"],
        "subcategories": {
            "Dorfgeschichten": ["dorf", "ortschaft", "siedlung"],
            "Historisches": ["geschichte", "historisch", "damals", "erinnerung", "chronik"],
            "plattdeutsche Themen": ["plattdeutsch", "platt", "niederdeutsch"],
            "regionale Besonderheiten": ["besonderheit", "einzigartig", "typisch"],
            "Fehn, Moor, Marsch": ["fehn", "moor", "marsch", "kanal", "torf"],
            "Ortsentwicklung": ["baugebiet", "neubau", "erschließung", "infrastruktur"],
        }
    },
    "Wirtschaft & Unternehmen": {
        "keywords": ["unternehmen", "firma", "betrieb", "geschäft", "eröffnung",
                      "wirtschaft", "handwerk"],
        "subcategories": {
            "Firmenporträts": ["firmenporträt", "betrieb", "unternehmen vorstell"],
            "Neueröffnungen": ["neueröffnung", "eröffnet", "neu am markt"],
            "Handwerk": ["handwerk", "meister", "geselle", "werkstatt", "tischler",
                         "elektriker", "installateur"],
            "Gastronomie": ["restaurant", "café", "gaststätte", "küche", "speisekarte",
                            "koch", "essen"],
            "Dienstleistungen": ["dienstleistung", "service", "beratung"],
            "Landwirtschaft": ["landwirtschaft", "bauer", "hof", "ernte", "vieh",
                               "milch", "acker"],
            "Tourismus": ["tourismus", "urlaub", "gäste", "ferienwohnung", "camping"],
        }
    },
    "Schule, Bildung & Jugend": {
        "keywords": ["schule", "schüler", "bildung", "kita", "kindergarten",
                      "jugend", "ausbildung"],
        "subcategories": {
            "Schulen": ["schule", "gymnasium", "realschule", "grundschule", "oberschule"],
            "Kitas": ["kita", "kindergarten", "kindertagesstätte", "krippe"],
            "Jugendgruppen": ["jugendgruppe", "jugendzentrum", "jugendpflege"],
            "Schülerprojekte": ["projekt", "schülerfirma", "schulprojekt"],
            "Ausbildung": ["ausbildung", "azubi", "lehrling", "berufseinstieg"],
            "Ferienaktionen": ["ferienpass", "ferienaktion", "ferienprogramm"],
        }
    },
    "Senioren & Soziales": {
        "keywords": ["senioren", "pflege", "sozial", "hilfe", "unterstützung",
                      "gesundheit"],
        "subcategories": {
            "Seniorenheime": ["seniorenheim", "altenheim", "pflegeheim", "residenz"],
            "Pflege": ["pflege", "pflegedienst", "betreuung"],
            "Begegnungsangebote": ["begegnung", "treff", "nachmittag", "kaffeekranz"],
            "soziale Projekte": ["sozial", "hilfsprojekt", "spendenaktion"],
            "Gesundheit": ["gesundheit", "arzt", "praxis", "vorsorge", "therapie"],
            "Generationenthemen": ["generation", "alt und jung", "mehrgenerationen"],
        }
    },
    "Freizeit, Ausflug & Genuss": {
        "keywords": ["freizeit", "ausflug", "genuss", "rezept", "natur",
                      "fahrrad", "wandern"],
        "subcategories": {
            "Restaurants": ["restaurant", "essen gehen", "speisen"],
            "Cafés": ["café", "kaffee", "kuchen", "torte"],
            "Ausflugstipps": ["ausflug", "ausflugsziel", "sehenswürdigkeit"],
            "Fahrradstrecken": ["fahrrad", "radtour", "radweg"],
            "Natur": ["natur", "tier", "pflanze", "garten", "wald"],
            "regionale Rezepte": ["rezept", "kochen", "backen", "zutaten"],
        }
    },
    "Bauen, Wohnen & Garten": {
        "keywords": ["bauen", "wohnen", "garten", "haus", "renovierung",
                      "energie", "immobilie"],
        "subcategories": {
            "Immobilien": ["immobilie", "grundstück", "haus kaufen", "wohnung"],
            "Handwerk": ["handwerk", "dachdecker", "maler", "fliesenleger"],
            "Renovierung": ["renovierung", "sanierung", "modernisierung", "umbau"],
            "Garten": ["garten", "beet", "rasen", "pflanze"],
            "Energie": ["energie", "solar", "photovoltaik", "strom"],
            "Wärmepumpen": ["wärmepumpe", "heizung", "wärme"],
            "regionale Baubetriebe": ["baubetrieb", "bauunternehmen", "baufirma"],
        }
    },
    "Sonderthemen": {
        "keywords": [],
        "subcategories": {
            "Hochzeit": ["hochzeit", "heirat", "trauung", "braut"],
            "Weihnachten": ["weihnacht", "advent", "nikolaus", "christkind"],
            "Ostern": ["ostern", "ostereier", "osterfeuer"],
            "Frühling": ["frühling", "frühblüher", "frühjahr"],
            "Sommer": ["sommer", "strand", "freibad", "hitze"],
            "Herbst": ["herbst", "erntedank", "laub"],
            "Winter": ["winter", "schnee", "frost", "eis"],
            "Gesundheit": ["gesundheit", "wellness", "vorsorge"],
            "Mobilität": ["mobilität", "verkehr", "bus", "bahn", "auto"],
            "Fußball-WM / EM": ["wm", "em", "fußball", "europameisterschaft",
                                  "weltmeisterschaft"],
            "lokale Sonderaktionen": ["sonderaktion", "aktion", "gewinnspiel"],
        }
    },
    "Leseraktionen": {
        "keywords": ["leseraktion", "mitmachen", "gewinnspiel", "leserfrühstück"],
        "subcategories": {
            "Leserfrühstück": ["leserfrühstück", "frühstück mit lesern"],
            "Gewinnspiele": ["gewinnspiel", "gewinn", "verlosung", "preis"],
            "Leserfotos": ["leserfoto", "eingesandt", "foto des monats"],
            "Ausflüge": ["leserausflug", "busfahrt", "tagesfahrt"],
            "Mitmachaktionen": ["mitmach", "teilnehmen", "aktion"],
        }
    },
    "Anzeigen / Advertorials": {
        "keywords": ["anzeige", "werbung", "advertorial", "sponsored",
                      "bezahlter beitrag"],
        "subcategories": {
            "Anzeige": ["anzeige"],
            "Unternehmensanzeige": ["unternehmensanzeige", "firmenwerbung"],
            "bezahlter Beitrag": ["bezahlter beitrag", "advertorial", "sponsored"],
            "Veranstaltungshinweis": ["veranstaltungshinweis"],
            "Produktwerbung": ["produkt", "angebot", "sonderpreis", "rabatt"],
        }
    },
}


def categorize_article(article: dict) -> dict:
    """
    Ordnet einem Artikel automatisch Kategorien zu.
    Gibt dict mit categories und subcategories zurück.
    """
    text = (
        (article.get("title", "") + " " + article.get("full_text", ""))
        .lower()
    )

    matched_categories = []
    matched_subcategories = []
    scores = {}

    for cat_name, cat_data in CATEGORY_RULES.items():
        score = 0
        # Hauptkategorie-Keywords prüfen
        for kw in cat_data["keywords"]:
            if kw in text:
                score += 2

        # Unterkategorien prüfen
        for sub_name, sub_keywords in cat_data["subcategories"].items():
            sub_score = 0
            for kw in sub_keywords:
                count = text.count(kw)
                if count > 0:
                    sub_score += count
                    score += count

            if sub_score > 0:
                matched_subcategories.append((sub_name, sub_score))

        if score > 0:
            scores[cat_name] = score

    # Beste Kategorien wählen (Top 2)
    sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    matched_categories = [c[0] for c in sorted_cats[:2]]

    # Beste Unterkategorien (Top 3)
    sorted_subs = sorted(matched_subcategories, key=lambda x: x[1], reverse=True)
    best_subs = [s[0] for s in sorted_subs[:3]]

    # Fallback: Wenn keine Kategorie gefunden
    if not matched_categories:
        # Artikeltyp prüfen
        if article.get("article_type") == "anzeige":
            matched_categories = ["Anzeigen / Advertorials"]
        else:
            matched_categories = ["Sonderthemen"]

    return {
        "categories": matched_categories,
        "subcategories": best_subs,
        "all_categories": list(matched_categories) + best_subs,
    }


def extract_entities(text: str) -> dict:
    """
    Extrahiert Personen, Vereine, Firmen und Orte aus dem Text.
    Einfache regelbasierte Erkennung.
    """
    entities = {
        "people": [],
        "clubs": [],
        "companies": [],
        "locations": [],
    }

    # Bekannte Ortsnamen
    known_locations = [
        "Westoverledingen", "Rhauderfehn", "Ostrhauderfehn",
        "Saterland", "Barßel", "Apen", "Augustfehn", "Leer",
        "Ihrhove", "Völlenerfehn", "Völlenerkönigsfehn",
        "Flachsmeer", "Steenfelde", "Großwolde", "Klostermoor",
        "Langholt", "Collinghorst", "Holterfehn",
        "Ramsloh", "Scharrel", "Sedelsberg", "Strücklingen",
        "Papenburg", "Emden", "Aurich", "Oldenburg",
        "Moormerland", "Uplengen", "Jümme", "Detern",
    ]

    for loc in known_locations:
        if loc.lower() in text.lower():
            entities["locations"].append(loc)

    # Vereine erkennen (einfache Muster)
    club_patterns = [
        r'(?:SV|TuS|VfL|VfB|TuRa|FC|FSV|TSV|SC)\s+[\w\-äöü]+',
        r'[\w\-äöü]+\s*(?:e\.?\s*V\.?)',
        r'(?:Feuerwehr|Schützenverein|Heimatverein|Sportverein|Förderverein)\s+[\w\-äöü]+',
    ]
    for pattern in club_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            match = match.strip()
            if len(match) > 3 and match not in entities["clubs"]:
                entities["clubs"].append(match)

    # Firmen (GmbH, OHG etc.)
    company_patterns = [
        r'[\w\-äöü\s]{3,40}\s+(?:GmbH|AG|OHG|KG|UG|e\.K\.|GbR)',
    ]
    for pattern in company_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            match = match.strip()
            if len(match) > 5 and match not in entities["companies"]:
                entities["companies"].append(match)

    return entities


# Optional: KI-basierte Kategorisierung
def categorize_with_ai(article: dict, api_key: str = None) -> dict:
    """
    KI-basierte Kategorisierung über die Anthropic API.
    Nur wenn AI_ENABLED=true und ein API-Key vorhanden ist.
    """
    if not api_key:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.info("Keine KI-Kategorisierung: kein API-Key")
        return categorize_article(article)

    try:
        import httpx
        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 500,
                "messages": [{
                    "role": "user",
                    "content": f"""Analysiere diesen Zeitungsartikel und gib ein JSON zurück mit:
- "categories": Liste der passenden Hauptkategorien
- "subcategories": Liste der Unterkategorien
- "keywords": 5-10 Schlagwörter
- "summary": Kurze Zusammenfassung (max 100 Wörter)
- "suggested_title": Besserer Titel
- "topic_series": Mögliche Themenreihe

Kategorien zur Auswahl:
Menschen & Porträts, Vereine & Ehrenamt, Veranstaltungen,
Region & Heimat, Wirtschaft & Unternehmen, Schule Bildung & Jugend,
Senioren & Soziales, Freizeit Ausflug & Genuss,
Bauen Wohnen & Garten, Sonderthemen, Leseraktionen,
Anzeigen / Advertorials

Titel: {article.get('title', '')}
Text: {article.get('full_text', '')[:2000]}

Antworte NUR mit JSON, ohne Markdown-Formatierung."""
                }]
            },
            timeout=30
        )
        data = response.json()
        content = data["content"][0]["text"]
        # JSON parsen
        result = json.loads(content)
        return result
    except Exception as e:
        logger.warning(f"KI-Kategorisierung fehlgeschlagen: {e}")
        return categorize_article(article)
