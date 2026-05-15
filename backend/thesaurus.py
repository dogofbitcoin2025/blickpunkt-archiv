"""
BlickPUNKT Archiv – Thesaurus / Synonym-System
Fasst verwandte Begriffe zu Themengruppen zusammen.
Wird bei Suche, Ähnlichkeitserkennung und Kategorisierung genutzt.
"""

# Jede Gruppe hat einen kanonischen Begriff (erster Eintrag)
# und eine Liste von Synonymen/verwandten Begriffen.
# Bei der Suche und Ähnlichkeitsberechnung werden alle Begriffe
# einer Gruppe als gleichwertig behandelt.

SYNONYM_GROUPS = [
    # --- Handwerk & Gewerbe ---
    ["elektro", "elektriker", "elektrotechnik", "elektroinstallation",
     "elektrobetrieb", "elektrofachbetrieb", "elektrohandwerk",
     "elektrotechniker", "elektroinstallateur", "elektrofirma",
     "elektroniker", "elektrik", "elektromeister"],

    ["sanitär", "sanitärtechnik", "sanitärinstallation", "klempner",
     "sanitärbetrieb", "sanitärfachbetrieb", "installateur",
     "sanitärinstallateur", "sanitärmeister", "rohrleitungsbau"],

    ["heizung", "heizungsbau", "heizungstechnik", "heizungsbauer",
     "heizungsinstallation", "heizungsmonteur", "heizungsfirma",
     "wärmepumpe", "wärmepumpen", "heiztechnik", "heizungssanierung"],

    ["maler", "malerbetrieb", "malerfachbetrieb", "malermeister",
     "anstreicher", "lackierer", "malereibetrieb", "malerarbeiten"],

    ["tischler", "tischlerei", "tischlermeister", "schreiner",
     "schreinerei", "holzbau", "möbeltischler", "bautischler"],

    ["dachdecker", "dachdeckerei", "dachdeckerbetrieb", "dachdeckermeister",
     "bedachung", "dachsanierung", "dacheindeckung", "dachreparatur"],

    ["fliesen", "fliesenleger", "fliesenlegermeister", "fliesenfachbetrieb",
     "fliesenverlegung", "fliesen- und naturstein"],

    ["garten", "gartenbau", "gartenpflege", "landschaftsbau",
     "gärtner", "gärtnerei", "galabau", "landschaftsgärtner",
     "gartengestaltung", "gartencenter"],

    ["bau", "bauunternehmen", "baubetrieb", "baufirma", "bauhandwerk",
     "baumeister", "maurermeister", "maurer", "hochbau", "tiefbau"],

    # --- Gastronomie ---
    ["restaurant", "gaststätte", "gasthof", "wirtshaus", "lokal",
     "gasthaus", "gastronomie", "speiselokal", "essen gehen"],

    ["café", "cafe", "kaffee", "kaffeehaus", "cafeteria",
     "konditorei", "eiscafé", "eisdiele"],

    ["bäcker", "bäckerei", "backstube", "backwaren", "brot",
     "brötchen", "bäckerhandwerk", "bäckermeister"],

    ["metzger", "metzgerei", "fleischerei", "fleischer",
     "schlachter", "schlachterei", "fleischfachgeschäft"],

    # --- Vereine & Organisationen ---
    ["feuerwehr", "freiwillige feuerwehr", "jugendfeuerwehr",
     "feuerwehrhaus", "feuerwehrfest", "feuerwehrkameraden",
     "brandschutz", "löschzug", "ortsfeuerwehr", "feuerwehrverein"],

    ["schützenverein", "schützenfest", "schützenbruderschaft",
     "schützenkönig", "schützenkönigin", "schützenball",
     "schützenhaus", "schützengilde", "schützenwesen"],

    ["sportverein", "sv", "tus", "vfl", "vfb", "tura", "fc",
     "fsv", "tsv", "sc", "sport", "mannschaft", "trainer"],

    ["drk", "rotes kreuz", "deutsches rotes kreuz",
     "drk ortsverein", "blutspende", "sanitätsdienst"],

    ["kirche", "kirchengemeinde", "pastor", "pastorin", "pfarrer",
     "pfarrerin", "gottesdienst", "konfirmation", "gemeindehaus",
     "kirchenvorstand", "kirchenrat", "evangelisch", "katholisch"],

    # --- Bildung ---
    ["schule", "schulen", "grundschule", "oberschule", "gymnasium",
     "realschule", "hauptschule", "gesamtschule", "schulleiter",
     "schulleiterin", "lehrkraft", "lehrer", "lehrerin"],

    ["kita", "kindergarten", "kindertagesstätte", "krippe",
     "kinderkrippe", "kinderhort", "kiga", "erzieherin", "erzieher"],

    # --- Veranstaltungen ---
    ["weihnachtsmarkt", "adventsmarkt", "nikolausmarkt",
     "christkindlmarkt", "weihnachtsbasar", "weihnachtsfest"],

    ["hafenfest", "stadtfest", "volksfest", "dorffest",
     "straßenfest", "sommerfest", "bürgerfest"],

    ["flohmarkt", "trödelmarkt", "antikmarkt", "kinderflohmarkt"],

    # --- Gesundheit ---
    ["arzt", "ärztin", "arztpraxis", "praxis", "medizin",
     "gesundheit", "doktor", "facharzt", "fachärztin",
     "hausarzt", "hausärztin"],

    ["zahnarzt", "zahnärztin", "zahnarztpraxis", "zahnmedizin",
     "kieferorthopäde", "zahnpflege", "dental"],

    ["apotheke", "apotheker", "apothekerin", "pharmazie",
     "arzneimittel", "medikamente"],

    ["pflege", "pflegedienst", "pflegeheim", "altenpflege",
     "pflegekraft", "ambulante pflege", "seniorenpflege",
     "seniorenheim", "altenheim", "pflegeeinrichtung"],

    # --- Immobilien & Wohnen ---
    ["immobilien", "immobilie", "makler", "immobilienmakler",
     "grundstück", "haus", "wohnung", "eigentumswohnung",
     "hausbau", "baugrundstück"],

    ["solar", "solaranlage", "photovoltaik", "solarenergie",
     "solartechnik", "solarstrom", "pv-anlage", "solardach"],

    # --- Auto & Mobilität ---
    ["auto", "autohaus", "kfz", "autowerkstatt", "autohändler",
     "fahrzeug", "pkw", "neuwagen", "gebrauchtwagen",
     "kfz-werkstatt", "kfz-meister", "kfz-betrieb"],

    ["fahrrad", "rad", "radfahren", "radtour", "radweg",
     "fahrradladen", "fahrradhändler", "e-bike", "ebike",
     "fahrradwerkstatt", "zweirad"],

    # --- Finanzen & Versicherung ---
    ["bank", "sparkasse", "volksbank", "raiffeisenbank",
     "bankfiliale", "finanzberatung", "geldanlage"],

    ["versicherung", "versicherungsmakler", "versicherungsbüro",
     "versicherungsagentur", "vorsorge", "absicherung"],

    # --- Mode & Einzelhandel ---
    ["mode", "modeboutique", "modegeschäft", "bekleidung",
     "textilien", "kleidung", "fashion", "boutique"],

    ["optiker", "brillen", "augenoptik", "optik", "optikgeschäft",
     "kontaktlinsen", "sehtest"],

    ["friseur", "frisör", "friseursalon", "hairstylist",
     "friseurmeister", "haarsalon", "barbershop", "coiffeur"],

    # --- Landwirtschaft ---
    ["landwirtschaft", "landwirt", "bauer", "bauernhof",
     "landwirtschaftlich", "agrar", "ackerbau", "viehzucht",
     "milchwirtschaft", "hofcafé"],

    # --- Energie ---
    ["energie", "energieberatung", "energieversorger",
     "energieeffizienz", "energiesparen", "erneuerbare energie",
     "windenergie", "windkraft", "biogas"],
]


# Lookup: Wort → kanonischer Begriff
_WORD_TO_CANONICAL = {}
# Lookup: kanonischer Begriff → alle Synonyme
_CANONICAL_TO_GROUP = {}

def _build_lookup():
    global _WORD_TO_CANONICAL, _CANONICAL_TO_GROUP
    if _WORD_TO_CANONICAL:
        return
    for group in SYNONYM_GROUPS:
        canonical = group[0]
        _CANONICAL_TO_GROUP[canonical] = set(group)
        for word in group:
            _WORD_TO_CANONICAL[word.lower()] = canonical

_build_lookup()


def get_canonical(word: str) -> str:
    """Gibt den kanonischen Begriff für ein Wort zurück, oder das Wort selbst."""
    return _WORD_TO_CANONICAL.get(word.lower(), word.lower())


def get_synonyms(word: str) -> set:
    """Gibt alle Synonyme für ein Wort zurück (inkl. dem Wort selbst)."""
    canonical = _WORD_TO_CANONICAL.get(word.lower())
    if canonical:
        return _CANONICAL_TO_GROUP.get(canonical, {word.lower()})
    return {word.lower()}


def normalize_text(text: str) -> str:
    """
    Normalisiert Text: ersetzt alle Synonyme durch ihren kanonischen Begriff.
    Wird für Ähnlichkeitsvergleiche genutzt.
    """
    words = text.lower().split()
    result = []
    for word in words:
        # Bereinigtes Wort (ohne Satzzeichen)
        clean = word.strip('.,;:!?()[]"\'')
        canonical = _WORD_TO_CANONICAL.get(clean)
        if canonical:
            result.append(canonical)
        else:
            result.append(clean)
    return ' '.join(result)


def expand_search_query(query: str) -> list:
    """
    Erweitert eine Suchanfrage um Synonyme.
    Gibt eine Liste aller möglichen Suchbegriffe zurück.
    """
    words = query.lower().split()
    expanded = set(words)
    for word in words:
        clean = word.strip('.,;:!?()[]"\'')
        synonyms = get_synonyms(clean)
        expanded.update(synonyms)
    return list(expanded)


def find_theme_group(text: str) -> list:
    """
    Findet alle Themengruppen, die im Text vorkommen.
    Gibt Liste von (kanonischer_begriff, gefundene_begriffe, anzahl_treffer) zurück.
    """
    text_lower = text.lower()
    found = []
    for group in SYNONYM_GROUPS:
        canonical = group[0]
        matches = []
        for word in group:
            if word in text_lower:
                count = text_lower.count(word)
                matches.append((word, count))
        if matches:
            total = sum(c for _, c in matches)
            found.append({
                "theme": canonical,
                "matches": [m[0] for m in matches],
                "count": total,
            })
    found.sort(key=lambda x: x["count"], reverse=True)
    return found
