"""Generate the 6-page capstone report from recorded measurements."""
import json
import reportlab
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Flowable

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs';OUT.mkdir(exist_ok=True)
results=json.loads((ROOT/'evaluation/results.json').read_text())
live=json.loads((ROOT/'evaluation/live-results.json').read_text()) if (ROOT/'evaluation/live-results.json').exists() else {'cases':[]}
passed=sum(bool(x['passed']) for x in live['cases']);total=len(live['cases'])
fontroot=Path(reportlab.__file__).parent/"fonts"
pdfmetrics.registerFont(TTFont("GM",str(fontroot/"Vera.ttf")))
pdfmetrics.registerFont(TTFont("GMBold",str(fontroot/"VeraBd.ttf")))
pdfmetrics.registerFontFamily("GM",normal="GM",bold="GMBold",italic="GM",boldItalic="GMBold")
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleGM',fontName='GMBold',fontSize=34,leading=38,textColor=colors.HexColor('#253127'),spaceAfter=18))
styles.add(ParagraphStyle(name='SubGM',fontName='GM',fontSize=15,leading=21,textColor=colors.HexColor('#7d8d70'),spaceAfter=15))
styles.add(ParagraphStyle(name='BodyGM',fontName='GM',fontSize=10,leading=15,spaceAfter=10,textColor=colors.HexColor('#394535')))
styles.add(ParagraphStyle(name='SmallGM',fontName='GM',fontSize=8,leading=11.5,spaceAfter=7,textColor=colors.HexColor('#65715e')))
styles.add(ParagraphStyle(name='HeadingGM',fontName='GMBold',fontSize=19,leading=24,spaceAfter=16,textColor=colors.HexColor('#283627')))
styles.add(ParagraphStyle(name='LabelGM',fontName='GMBold',fontSize=8,leading=12,spaceAfter=10,textColor=colors.HexColor('#dd6b3c')))
styles.add(ParagraphStyle(name='H2GM',fontName='GMBold',fontSize=11,leading=16,spaceBefore=9,spaceAfter=6,textColor=colors.HexColor('#33492b')))
story=[]
def p(text,style='BodyGM'):return Paragraph(text,styles[style])
def add(text,style='BodyGM'):story.append(p(text,style))
def heading(n,title):add(f'GEARMATCH / CAPSTONE REPORT / {n:02d}','LabelGM');add(title,'HeadingGM')
def table(rows,widths):
    cells=[[p(escape(str(c)),'SmallGM') for c in row] for row in rows]
    t=Table(cells,colWidths=widths,hAlign='LEFT',repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9efdf')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#dce4d3'))]))
    story.append(t);story.append(Spacer(1,12))

class Architecture(Flowable):
    def __init__(self):super().__init__();self.width=475;self.height=180
    def draw(self):
        c=self.canv
        def box(x,y,w,title,sub):
            c.setFillColor(colors.HexColor('#f0f4e9'));c.setStrokeColor(colors.HexColor('#cbd9bd'));c.roundRect(x,y,w,48,6,fill=1,stroke=1)
            c.setFillColor(colors.HexColor('#304728'));c.setFont('GMBold',9);c.drawCentredString(x+w/2,y+28,title)
            c.setFont('GM',7);c.drawCentredString(x+w/2,y+14,sub)
        def arrow(x1,y1,x2,y2):
            c.setStrokeColor(colors.HexColor('#d7784d'));c.setLineWidth(1.2);c.line(x1,y1,x2,y2)
            path=c.beginPath();path.moveTo(x2,y2);path.lineTo(x2-5,y2+3);path.lineTo(x2-5,y2-3);path.close();c.setFillColor(colors.HexColor('#d7784d'));c.drawPath(path,fill=1,stroke=0)
        box(0,115,140,'User interface','Question + hard constraints');box(166,115,140,'Validated API','Pydantic / Zod');box(332,115,140,'Native tool router','gemma-4-E4B-it')
        arrow(141,139,164,139);arrow(307,139,330,139)
        box(0,25,140,'Manufacturer catalog','21 SKUs + source URLs');box(166,25,140,'Retrieval tools','Metadata + BM25 + TF-IDF');box(332,25,140,'Grounded answer','Schema + evidence checks')
        arrow(141,49,164,49);arrow(307,49,330,49)
        c.setStrokeColor(colors.HexColor('#d7784d'));c.line(402,114,402,94);c.line(402,94,235,94);c.line(235,94,235,74)
        c.setFont('GM',7);c.setFillColor(colors.HexColor('#7b8b6d'));c.drawString(250,98,'bounded execute / observe loop')

# 1
add('BUILDING LLM-POWERED APPLICATIONS / 1-2026','LabelGM')
add('GearMatch','TitleGM');add('Mouse Lab: evidence-grounded product recommendations','SubGM')
add('Capstone project report | Chaiporn2005 | 24 October 2026','SmallGM')
story.append(Spacer(1,20))
add('Problem and users','H2GM')
add('Choosing a mouse requires combining hard constraints such as reference budget, connection and nominal weight with product-specific evidence. General chat answers can invent specifications, confuse variants or cite a price as current when it is historical. GearMatch helps Thai- and English-speaking users search a small traceable catalog, compare candidates and inspect the underlying sources.')
add('Scope','H2GM')
add('The application covers 21 mouse SKUs from Logitech, Keychron and Razer. It combines structured output, lexical-vector retrieval, a measured retrieval benchmark, native function calling and a served interface. It uses the course proxy through the Python OpenAI SDK with gemma-4-E4B-it; the hosted web runtime uses the compatible HTTP protocol. It is an original mouse-domain corpus, not the public course reference corpus.')
test=results['systems']['hybrid']['test'];base=results['systems']['bm25']['test']
table([['Measured item','Result'],['Held-out retrieval Recall@3',f"{base['recall_at_3']:.3f} baseline -> {test['recall_at_3']:.3f} improved"],['Held-out MRR@3',f"{base['mrr_at_3']:.3f} -> {test['mrr_at_3']:.3f}"],['Live class-proxy smoke cases',f'{passed}/{total} passed; separate from retrieval benchmark']],[230,245])
add('Interpretation: the small author-curated test set measures catalog retrieval, not general shopping quality. The report separates deterministic retrieval scores from live model behavior, preserves real failure traces and does not infer statistical significance.','SmallGM')
story.append(PageBreak())
# 2
heading(2,'Data and evidence boundaries')
add('Catalog construction','H2GM')
add('The dataset contains 21 explicitly named variants, researched from 33 official shop, specification, support and launch-page records on 24 October 2026. catalog.json stores normalized factual fields, source URLs and original short paraphrases. sources.json records provenance. raw/manufacturer-notes.md is a research summary, not an archived copy of manufacturer HTML. No product photographs or long marketing passages are redistributed.')
table([['Field','Treatment'],['Price','USD reference amount displayed by the manufacturer; offers are separate. Razer Cobra uses dated 2023 launch MSRP. Not a live quote or Thai retail price.'],['Weight','Manufacturer nominal figure. Cable/battery inclusion and tolerances differ; notes preserve this limitation.'],['Unknown values','null means unverified. A product with unknown weight cannot pass a maximum-weight filter.'],['Variants','Selected sensor, polling and switch variants are explicit. A flagship specification is not borrowed for a cheaper variant.'],['Handedness','Only populated when established by source text; visual symmetry alone is insufficient.']],[100,375])
add('Concrete provenance decisions','H2GM')
add('Pebble Mouse 2 M350s supports optional Logi Bolt, but the receiver is not included. The selected M6 Silent Premium Wheel is the 3395/1K variant at 86 g, not the 3950/8K headline variant. M4 4K and M3 8K weight are conservatively unknown because page-level figures were not sufficiently tied to the chosen variant. Razer Cobra reference price is explicitly historical.')
add('Sampling and rights','H2GM')
add('This is a convenience sample with only three brands, not a representative market survey. use_cases are project-authored indexing labels, not independent performance tests. Manufacturer trademarks and source rights remain with their owners; the code license does not relicense third-party content. No medical, comfort, stock or current-market claims are evaluated.')
story.append(PageBreak())
# 3
heading(3,'Architecture and guarded agent')
story.append(Architecture())
add('Retrieval design','H2GM')
add('Each product is a document containing normalized features and source notes. BM25 supplies keyword matching; a local TF-IDF cosine index supplies a second lexical ranking. Reciprocal rank fusion combines ranks with constant k=60. Fixed Thai/English aliases bridge terms such as quiet/silent and the Thai words for left-handed, vertical and Bluetooth. These are lexical embeddings, not a pretrained neural semantic model. Hard metadata filters are applied before ranking.')
add('Native function-calling loop','H2GM')
add('The router selects an allow-listed search_specs or filter_products function. Tool query arguments must pass a strict schema, and hard UI constraints are enforced server-side. The tool observation provides factual product fields and a single citation_id namespace. The model then produces a structured recommendation. A maximum of five model turns and four tool calls per turn, repeated-query detection and bounded repair prevent unbounded execution.')
add('Validation and stop behavior','H2GM')
add('A final JSON answer must pass the schema, contain at most three unique products, reference only retrieved product IDs and satisfy the user hard filters. Otherwise the model receives a bounded repair request; if it still fails, the API returns an error. A valid final answer ends the loop. An empty, supported result is represented as an explicit abstention, not an invented replacement product.')
add('Python and web runtimes','H2GM')
add('FastAPI is the canonical Python SDK application. The Sites-compatible web runtime implements the same contract in TypeScript. Both use one catalog and a canonical document representation. The parity script compares the top-three IDs on all 30 retrieval cases. API keys are never sent to browser code; local files and production runtime secrets are excluded from Git.')
story.append(PageBreak())
# 4
heading(4,'Reproducible evaluation')
add('Test set and metrics','H2GM')
add('The gold file contains 30 original author-curated examples: 20 development and 10 held-out cases, with 24 answerable and 6 unanswerable overall. Each example records the question, explicit filters, relevant product IDs and a rationale. Held-out cases include Thai paraphrases. No hyperparameters were tuned on held-out labels. There is no independent annotation or inter-annotator agreement measurement.')
add('Recall@3 is the fraction of relevant IDs retrieved among the first three results. MRR@3 is the reciprocal rank of the first relevant ID, truncated at three. Both exclude unanswerable questions. Empty-result accuracy scores only the unanswerable cases. Constraint violations count retrieved candidates that fail an explicit filter. One question has four relevant IDs, so even perfect top-three retrieval has Recall@3=0.75.')
rows=[['System','Split','Recall@3','MRR@3','Violations','Empty acc.']]
for name in ['bm25','filtered_bm25','hybrid']:
    for split in ['dev','test']:
        r=results['systems'][name][split];rows.append([name,split,f"{r['recall_at_3']:.3f}",f"{r['mrr_at_3']:.3f}",r['constraint_violations'],f"{r['abstention_accuracy']:.3f}"])
table(rows,[105,45,78,75,75,97])
add('What the comparison establishes','H2GM')
add('The named baseline is naive BM25 with no metadata constraints or bilingual aliases. Filtered BM25 is an ablation that isolates the effect of hard constraints. The improved system adds domain aliases and TF-IDF rank fusion together. Therefore the improvement cannot be attributed to vector fusion alone. The absolute held-out Recall@3 gain over baseline is 0.531; the gain over filtered BM25 is 0.469. The small test set supports a scoped engineering result, not a statistically general claim.')
add('Reproduce: python -m evaluation.run. results.json includes every retrieved ID, dataset/catalog SHA-256 hashes and the Python version. Gold labels are explicit and inspectable.','SmallGM')
story.append(PageBreak())
# 5
heading(5,'Live results and honest failures')
add('Class-proxy smoke evaluation','H2GM')
add(f'The latest recorded run executes three real question/constraint cases through gemma-4-E4B-it with temperature0: quiet Bluetooth office use under USD30; an impossible lightweight left-handed requirement; and a lightweight gaming comparison. {passed} of {total} cases pass the automatic checks. These checks cover output parsing, selected IDs, hard constraints and expected abstention; they are not an independent judge of every sentence.')
rows=[['Live case','Result','Recorded latency']]
for r in live['cases']:
    ms=r.get('result',{}).get('elapsed_ms',r.get('elapsed_ms',0));rows.append([r['id'],'PASS' if r['passed'] else 'FAIL',f'{ms/1000:.2f} s'])
table(rows,[210,100,165])
add('Failure observed before repair','H2GM')
add('In the preserved pre-fix live run, only one of three smoke cases passed. The model mixed website source IDs such as pebble/pebbles with product IDs, so the citation validator correctly refused the answer. Another response used a string where limitations required a list. Repeating a vague repair message did not reliably correct the citation namespace. The revised observation exposes only a canonical citation_id and a more explicit repair contract. A separate router instruction avoids mixing tool selection with final-answer formatting.')
add('Remaining retrieval limitation','H2GM')
add('The held-out lightweight-gaming question has four relevant mice, but the interface returns only three. Its Recall@3 is0.75 even when every returned result is relevant. More generally, source notes can mention a feature to exclude it for a variant, and lexical search can still match that word. The answerer must read the caveat; keyword overlap alone is not entailment.')
add('Failure handling as behavior','H2GM')
add('An impossible request should return an abstention. A malformed or unsupported response should produce an explicit bounded-agent error. The application never silently substitutes an offline sample response for a live model answer. Tool evidence and validated citations are visible so that a user can inspect the reasoning path and source limitations.')
story.append(PageBreak())
# 6
heading(6,'Limitations, demonstration and references')
add('Limitations and next steps','H2GM')
add('The corpus is small and brand-biased. USD references age, use mixed pricing bases and do not represent local offers. Nominal weights and manufacturer claims are not lab measurements. The bilingual alias list is hand-built and cannot handle arbitrary Thai phrasing. Retrieval relevance and constraint validity do not prove free-text faithfulness. Next steps are independently annotated queries, a larger vendor-balanced corpus, sentence-level entailment review, separately ablated aliases/vector fusion and explicit price-refresh provenance.')
add('Demonstration plan','H2GM')
add('Show the running app on a real new input, then compare two mice and open manufacturer sources. Demonstrate a quiet Bluetooth recommendation and an impossible lightweight left-handed request. Explain the citation-namespace failure and the validator, then reproduce evaluation.run and interpret Recall@3 versus MRR@3. A 3-6 minute recording or an accessible working deployment is required; a catalog-only page is insufficient evidence of live LLM behavior.')
add('Reproduction and submission','H2GM')
add('README documents the Python and web setups. requirements.txt and the web lockfile record dependencies. The repo contains raw factual summaries, catalog, gold labels, scripts, results and tests. Keep secrets out of Git. The public GitHub URL, this PDF and a valid demo URL are the three separate submission items. Public repository/deployment access must be verified before submission; no placeholder URL should be submitted.')
add('Selected primary references','H2GM')
refs=[('Logitech M100','https://www.logitech.com/en-us/shop/p/m100-usb-mouse'),('Logitech Lift specifications','https://www.logitech.com/en-ae/products/mice/lift-vertical-ergonomic-mouse.html'),('Keychron M6 variants','https://www.keychron.com/products/keychron-m6-wireless-mouse'),('Keychron M2 Mini','https://www.keychron.com/products/keychron-m2-mini-wireless-mouse'),('Razer Cobra support','https://mysupport.razer.com/app/answers/detail/a_id/13184'),('OpenAI function calling','https://developers.openai.com/api/docs/guides/function-calling')]
for title,url in refs:add(f'<link href="{escape(url)}" color="#567b3d">{escape(title)}</link> - {escape(url)}','SmallGM')
add('All 33 source records and SKU-level citations are in data/sources.json and catalog.json. AI assistance was used in implementation and source research. Evaluation numbers and live traces come from executed code; the student remains responsible for reviewing the work and defending it.','SmallGM')

def footer(canvas,doc):
    canvas.setStrokeColor(colors.HexColor('#dce5d2'));canvas.line(50,44,545,44)
    canvas.setFont('GM',7);canvas.setFillColor(colors.HexColor('#8a9b79'));canvas.drawString(50,31,'GEARMATCH / MOUSE LAB - 24 OCT 2026');canvas.drawRightString(545,31,str(doc.page))

doc=SimpleDocTemplate(str(OUT/'GearMatch-report.pdf'),pagesize=(595.28,841.89),rightMargin=60,leftMargin=60,topMargin=48,bottomMargin=61,title='GearMatch - Mouse Lab Capstone Report',author='Chaiporn2005')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print('Wrote',OUT/'GearMatch-report.pdf')
