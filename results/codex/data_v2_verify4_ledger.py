"""Visual judgments recorded after viewing all eleven pinned-image contact sheets."""
from data_v2_verify4_rules import *

notes={
 'merge':[
 'Google shows results for the typed thriller-book query after the bottom-right search tap.',
 'Instagram shows portable-speaker search results; the next target selects a result.',
 'Facebook shows fitness-tracker search results after the bottom-right search tap.',
 'Amazon shows vanilla-extract search results; the next target scrolls those results.',
 'Firefox shows the typed San Jose bookstore query and its results.',
 'Chrome shows the Tesla stock-news query and result cards.',
 'The bank query remains in the search field and a bank-results list is visible.',
 'DuckDuckGo shows Berlin film-festival search results.',
 'Play Store shows results for Club Factory Shopping India.',
 'Play Store shows triller search results. The merged step has a stale TikTok-arrow instruction, but its bottom-right coordinate, raw search intention and resulting query/results support submission. No missing toolbar, suggestion or dismissal action is demonstrated.',
 'Explicit PRESS_ENTER follows TYPE; Etsy shows Formal Suits results and the next action opens Price.',
 'Explicit PRESS_ENTER follows TYPE; NBC search shows Asia results and the next target selects the first article.',
 'Explicit PRESS_ENTER follows TYPE; Quora shows artificial-intelligence results and the next target opens filters.',
 'Explicit PRESS_ENTER follows TYPE; ReadEra shows the queried book and the next target marks its reading status.',
 'Explicit PRESS_ENTER follows TYPE; Eventbrite shows Education results and the next target opens the date filter.',
 'Explicit PRESS_ENTER follows TYPE; Fever shows concerts results and the next target opens Sort.',
 'Explicit PRESS_ENTER follows TYPE; the San Francisco location query and matching selectable location are visible.',
 'Explicit PRESS_ENTER follows TYPE; the Los Angeles location query and matching selectable location are visible.',
 'Explicit PRESS_ENTER follows TYPE; IKEA shows Rugs results and the next target opens filters.',
 'Explicit PRESS_ENTER follows TYPE; CNN shows business results and the next target selects Photos.',
 ],
 'scroll_odyssey':[
 'Gmail composition form: the source path traverses the form above the keyboard; no slider or selection handle is being dragged.',
 'Lightroom gallery: the source path traverses photo thumbnails; the depicted clock is a photograph, not a clock control.',
 'Facebook comments: the source path moves through the comment list above the composer; no control drag is visible.',
 'Facebook search: the path traverses groups/results content.',
 'Launcher: a horizontal swipe through empty background between app pages.',
 'Launcher: a horizontal swipe through empty background between app pages.',
 'Tumblr profile: a vertical swipe through the post list.',
 'Browser: a vertical swipe through conference-page content.',
 'Yahoo Finance: a vertical swipe through search results above the keyboard.',
 'Edge: a vertical swipe through search-result content.',
 ],
 'scroll_amex':[
 'Launcher: upward swipe through empty background, consistent with opening the app drawer.',
 'Launcher: horizontal swipe through background; no icon is held or moved.',
 'Launcher: upward swipe through empty background.',
 'Launcher: upward swipe through empty background.',
 'Launcher: upward swipe through empty background.',
 'Launcher: horizontal swipe through empty background.',
 'Podcast Addict: upward swipe through the episode list, away from a playback seek control.',
 'IKEA cart: upward swipe through the item list; no quantity control or selection handle is dragged.',
 'Booking date picker: downward swipe through the scrollable month grid; no date-selection handle, clock hand or slider is visible.',
 'Launcher: upward swipe through empty background.',
 ]}
rows=json.loads((CACHE/'target_samples.json').read_text())['rows'];ledger=[]
for r in rows:
    group,index=r['visual_id'].rsplit('_',1)
    ledger.append({'visual_id':r['visual_id'],'id':r['id'],
                   'judgment':'no_false_merge_observed' if group=='merge' else 'no_control_drag_observed',
                   'note':notes[group][int(index)-1],'image':'visual/'+r['visual_id']+'.png'})
assert len(ledger)==40 and len({r['id'] for r in ledger})==40
out={'revision':PIN,'reviewed_contact_sheets':11,'post_merge_rows':20,'scroll_rows':20,
     'false_submit_merges_observed':0,'control_drags_observed':0,
     'scope':'Visible source-operation and retained-history checks; not device replay or a source-label accuracy estimate.',
     'rows':ledger}
write_json('visual_review.json',out)
lines=['**Fourth-audit B1/B2 visual ledger**','',
       'Viewed all 11 contact sheets at original resolution: 20 rows immediately after submit merges and 20 remaining new-source scroll rows. Raw paths are red; the generic executor path is green. Coordinates and histories were also checked against raw annotations through the actual current source loops. These judgments do not certify downstream task completion.','',
       '| Image | Published row | Narrow finding |','|---|---|---|']
for r in ledger:lines.append(f"| [{r['visual_id']}]({r['image']}) | `{r['id']}` | {r['note']} |")
(CACHE/'visual_review.md').write_text('\n'.join(lines)+'\n')
print('Recorded 20 post-merge and 20 scroll visual reviews; zero observed B1/B2 failures.')
