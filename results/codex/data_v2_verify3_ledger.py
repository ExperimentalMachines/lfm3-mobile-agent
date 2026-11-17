"""Human visual judgments after viewing all 12 sheets at original size and selected full-size rows."""
from data_v2_verify3_rules import CACHE
import collections as C, json, math

notes={
 'odyssey':[
 'Facebook results support a downward content scroll.',
 'Point is the Copilot send control; blank intent avoids an unsupported rationale.',
 'Point is the Pandora launcher icon.',
 'Classical query agrees with the album goal and focused search field.',
 'App list can be scrolled to locate PayPal.',
 'Home navigation is locally plausible before switching from YouTube to Clock; viewing completion is unverified.',
 'Point selects the blank WPS document template.',
 'Point selects a blank Word document.',
 'Typing a company name into the blank document is locally plausible; earlier search result not visible.',
 'Point is Google Keep new-note control.',
 'Point is Instagram direct messages.',
 'Course name is typed into the focused document after the URL.',
 'Point is See more on a relevant Facebook post.',
 'Point focuses the Firefox search/address field.',
 'Point is the Vaulty launcher icon.',
 'Home navigation after viewing a film page is locally plausible for the next app.',
 'Home navigation after viewing K-pop band results is locally plausible.',
 'Home navigation after viewing fitness-app recommendations is locally plausible.',
 'Horizontal launcher swipe is locally plausible to find Settings.',
 'Point selects an artichoke image in the photo picker.',
 'Point focuses Play Store search.',
 'REJECT: intent says task name and due date; label types 10 mins per day into the Description field under an existing Chinese Learning title.',
 'Home navigation after inspecting a backpack recommendation is locally plausible.',
 'Point is the Likee launcher icon.',
 'Point is the Lyft destination field.',
 'Point is the Google Meet launcher icon.',
 'Point is the Clock launcher icon.',
 'UNCERTAIN: horizontal gesture in a Facebook photo viewer; intent calls this scrolling the feed. Outcome is not established by this frame.',
 'Point is Citymapper Get Me Somewhere.',
 'Point is Copy on the text-selection menu.',
 'Point is the Temu Uninstall button.',
 'Point is Choose UberX Share; downstream booking success is not asserted.'
 ],
 'amex':[
 'Minus control can lower the displayed 1.5x playback speed toward 1.3x.',
 'Point is Follow shop, explicitly requested.',
 'Point is the article bookmark control.',
 'Upward launcher swipe can open the app drawer.',
 'Horizontal launcher swipe can reveal more apps.',
 'Point is Reply on the social email.',
 'Upward launcher swipe can open the app drawer.',
 'Profile navigation is a plausible route to publisher/follow management; final follow is not proven.',
 'Project document subject agrees with the goal apart from harmless capitalization.',
 'UNCERTAIN: Repeat is selected for a goal requesting a report by the end of this month. This may add unintended recurrence; the eventual due date is not visible.',
 'Point is MyObservatory launcher icon.',
 'Point opens the TodayTix city selector.',
 'Horizontal launcher swipe can reveal Gmail.',
 'Upward launcher swipe can open the app drawer.',
 'Coding query agrees with the Reddit goal.',
 'Point selects Toronto in the city list.',
 'Point is the Reddit icon in the app drawer.',
 'Exact newsletter query agrees with the quoted word.',
 'Navigation drawer is a plausible route to Downloads.',
 'Point is Gmail launcher icon.',
 'Statue of Liberty query agrees with the goal.',
 'Point opens the date control for the grocery-shopping task.',
 'Point selects the third displayed TED Talks episode.',
 'Point downloads the second episode while the first is downloading; locally consistent with three downloads.',
 'Point focuses the message field in the Siyuan conversation.',
 'Selected playlist-name field will receive the requested My Indie Mix text.',
 'Point starts playback of the displayed DJ show; its latest/followed status is not verified by one frame.',
 'Point selects rating from 5 to 0 in the Sort sheet.',
 'App drawer can scroll down to TEMU.',
 'Upward launcher swipe can open the app drawer.',
 'Upward launcher swipe can open the app drawer.',
 'Horizontal launcher swipe can reveal more apps.'
 ],
 'screenqa':[
 'Balance Due visibly reads $0.00.',
 'EuropianMingle is named in the Facebook permission text.',
 'Offer visibly gives 30 additional days.',
 'Home tab is highlighted.',
 '19 views is visible.',
 'Log in with Facebook is visible.',
 'Full-size review shows a rain-cloud icon with blue raindrops.',
 'Username App Crawler is visible.',
 'Permission illustration says 1 of 3.',
 'Visible paragraph says designed for smartphones only.',
 'Ice row is selected and checked.',
 'Ttalk branding is visible.',
 'First day of LMP is 3/8/17, consistent with March 8, 2017.',
 'UNCERTAIN: eBay is the visible advertisement; the underlying wallpaper app is not identified. Question does not distinguish advertised app from host app.',
 'Height field explicitly requests centimeters.',
 'Length of day visibly reads 10h 59m 41s.',
 'Search near me checkbox is unchecked.',
 'SuperBeam PRO is named in the offer.',
 'Drill sergeant has the checkmark.',
 'My point shows 1.',
 'REJECT: Unread (1) is the light selected tab; Read is dark and unselected. Target says Read.',
 'Mr Voonik is named in the header and dialog.',
 'Periodicity reads Only once time.',
 'Displayed call timer is 00:4, supporting four seconds.',
 'Home is selected in the bottom row.',
 'UNCERTAIN: Horoscope.com branding is visible, but a developer identity is not explicitly shown.',
 'Price $1,250K equals 1.25 million dollars.',
 'EXERCISE tab is highlighted.',
 '22 NEW ARTICLES is visible.',
 'Date/time field shows 4:41PM EDT.',
 'First post his face says 5 days ago.',
 'Active plans says Trial.'
 ]}

samples=json.loads((CACHE/'visual_samples.json').read_text()); ledger=[]
for r in samples:
    index=int(r['visual_id'].rsplit('_',1)[1])-1
    note=notes[r['source']][index]
    judgment='reject' if note.startswith('REJECT:') else 'uncertain' if note.startswith('UNCERTAIN:') else 'plausible'
    ledger.append({'visual_id':r['visual_id'],'id':r['id'],'judgment':judgment,'note':note,
                   'image':'visual/'+r['visual_id']+'.png'})
counts={s:dict(C.Counter(x['judgment'] for x in ledger if x['id'].split('/')[1]==s)) for s in notes}
def wilson(k,n):
    z=1.96; p=k/n; den=1+z*z/n; center=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [round(100*(center-half),2),round(100*(center+half),2)]
rates={s:{'n':32,'confirmed_rejects':counts[s].get('reject',0),'uncertain':counts[s].get('uncertain',0),
          'confirmed_rate_pct':100*counts[s].get('reject',0)/32,'wilson95_pct':wilson(counts[s].get('reject',0),32)} for s in notes}
(CACHE/'visual_review.json').write_text(json.dumps({'selection_seeds':[20261131,20261132,20261133],'counts':counts,'rates':rates,'rows':ledger},indent=2))
lines=['# Third-audit visual ledger','',
 '32 random train rows per source, without replacement from the four-shard sample. All 12 sheets viewed at original size; uncertain cases enlarged as needed. Judgments concern visible target/intent consistency, not device success.',
 '', '| Visual ID | Row | Judgment | Evidence |','|---|---|---|---|']
for x in ledger:lines.append(f"| [{x['visual_id']}]({x['image']}) | `{x['id']}` | {x['judgment']} | {x['note']} |")
(CACHE/'visual_review.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'counts':counts,'rates':rates},indent=2))
