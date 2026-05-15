import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

export type Article = {
  id: number
  issue_id: number
  title: string
  summary: string
  full_text: string
  gemeinde: string
  saison: string
  jahr: number
  page_start: number
  page_end: number
  article_type: 'redaktionell' | 'anzeige'
  content_type: string
  content_type_confidence: number
  ad_score: number
  editorial_score: number
  detected_signals: string[]
  status: string
  pdf_source: string
  original_url: string
  created_at: string
  updated_at: string
  category_names?: string[]
  keyword_list?: string[]
}

export type Issue = {
  id: number
  title: string
  gemeinde: string
  saison: string
  jahr: number
  ausgabe_nr: string
  pdf_url: string
  status: string
  created_at: string
}

export type Category = {
  id: number
  name: string
  parent_id: number | null
  sort_order: number
}

// Synonymgruppen (clientseitiger Thesaurus für Suche)
const SYNONYM_GROUPS: string[][] = [
  ['elektro','elektriker','elektrotechnik','elektroinstallation','elektrofachbetrieb'],
  ['sanitär','sanitärtechnik','klempner','sanitärbetrieb','installateur'],
  ['heizung','heizungsbau','heizungstechnik','wärmepumpe','wärmepumpen'],
  ['maler','malerbetrieb','malermeister','anstreicher','lackierer'],
  ['tischler','tischlerei','schreiner','schreinerei','holzbau'],
  ['dachdecker','dachdeckerei','bedachung','dachsanierung'],
  ['fliesen','fliesenleger','fliesenfachbetrieb'],
  ['garten','gartenbau','gartenpflege','landschaftsbau','gärtner'],
  ['bau','bauunternehmen','baufirma','maurer','hochbau','tiefbau'],
  ['restaurant','gaststätte','gasthof','gasthaus','gastronomie'],
  ['café','cafe','kaffee','konditorei','eiscafé'],
  ['bäcker','bäckerei','backstube'],
  ['feuerwehr','freiwillige feuerwehr','jugendfeuerwehr','feuerwehrfest'],
  ['schützenverein','schützenfest','schützenkönig'],
  ['sportverein','sv','tus','vfl','fc','sport','mannschaft'],
  ['schule','schulen','grundschule','oberschule','gymnasium'],
  ['kita','kindergarten','kindertagesstätte'],
  ['weihnachtsmarkt','adventsmarkt','weihnachtsbasar'],
  ['hafenfest','stadtfest','volksfest','sommerfest'],
  ['arzt','ärztin','arztpraxis','gesundheit','hausarzt'],
  ['zahnarzt','zahnärztin','zahnmedizin'],
  ['apotheke','apotheker','pharmazie'],
  ['pflege','pflegedienst','pflegeheim','seniorenheim','altenheim'],
  ['immobilien','makler','grundstück','hausbau'],
  ['solar','solaranlage','photovoltaik','solartechnik'],
  ['auto','autohaus','kfz','autowerkstatt','fahrzeug'],
  ['fahrrad','rad','radfahren','e-bike','zweirad'],
  ['bank','sparkasse','volksbank','finanzberatung'],
  ['friseur','frisör','friseursalon','haarsalon'],
  ['landwirtschaft','landwirt','bauer','bauernhof','agrar'],
]

export function expandSearchQuery(query: string): string[] {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean)
  const expanded = new Set(words)
  for (const word of words) {
    for (const group of SYNONYM_GROUPS) {
      if (group.some(w => w.includes(word) || word.includes(w))) {
        group.forEach(w => expanded.add(w))
        break
      }
    }
  }
  return Array.from(expanded)
}

export const GEMEINDEN = [
  'Westoverledingen',
  'Rhauderfehn',
  'Ostrhauderfehn',
  'Saterland',
  'Barßel',
  'Apen',
  'Augustfehn',
  'Stadt Leer',
]

export const SAISONEN = ['Frühling', 'Sommer', 'Herbst', 'Winter']
