"""Build the "What Is My Child Actually Learning?" module PDFs in the
codifyit brand (see tailwind.config.js).

The module text lives in the course app bundle (course/assets/index-*.js) as
the `qp` array. This script pulls that array out with Node, then lays each
module out with ReportLab.

Usage:
    pip install reportlab fonttools
    python3 scripts/parents_pdfs/build.py --fonts <dir-of-IBM-Plex-ttf> \
        --out parents-guide [--only module_01_why_is_my_child_learning_this.pdf ...]

The fonts dir needs IBMPlexSans-{Regular,Italic,Medium,SemiBold,
SemiBoldItalic,Bold,BoldItalic}.ttf and IBMPlexMono-{Regular,Medium}.ttf.
The npm packages @ibm/plex-sans and @ibm/plex-mono ship them as .woff;
fontTools converts those with `f = TTFont(path); f.flavor = None; f.save(...)`.
"""

import argparse
import glob
import html
import json
import os
import re
import subprocess

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, ListFlowable, ListItem, NextPageTemplate,
    PageBreak, PageTemplate, Paragraph, Preformatted, Spacer, Table, TableStyle,
)

# Brand tokens (tailwind.config.js / assets/brand.src.css)
TEXT = HexColor('#0f172a')      # Ink Navy
MUTED = HexColor('#475569')     # Slate
PRIMARY = HexColor('#0a369d')   # Royal Blue
CTA = HexColor('#ff6b35')       # Coral, CTAs only
BORDER = HexColor('#e2e8f0')
CODEBG = HexColor('#1e293b')
TINT = HexColor('#f1f5f9')      # cool card tint
CODE_TEXT = HexColor('#e2e8f0')

GUIDE_TITLE = 'What Is My Child Actually Learning?'
GUIDE_SUBTITLE = "A Parent's Guide to Data, Coding & AI"

PAGE_W, PAGE_H = A4
MARGIN_X = 22 * mm
MARGIN_TOP = 26 * mm
MARGIN_BOTTOM = 24 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_X


def register_fonts(font_dir):
    faces = {
        'Sans': 'IBMPlexSans-Regular', 'Sans-Italic': 'IBMPlexSans-Italic',
        'Sans-Medium': 'IBMPlexSans-Medium', 'Sans-SemiBold': 'IBMPlexSans-SemiBold',
        'Sans-SemiBoldItalic': 'IBMPlexSans-SemiBoldItalic',
        'Sans-Bold': 'IBMPlexSans-Bold', 'Sans-BoldItalic': 'IBMPlexSans-BoldItalic',
        'Mono': 'IBMPlexMono-Regular', 'Mono-Medium': 'IBMPlexMono-Medium',
    }
    for name, file in faces.items():
        pdfmetrics.registerFont(TTFont(name, os.path.join(font_dir, file + '.ttf')))
    # So <b>/<i> inside paragraphs resolve to the right Plex faces.
    addMapping('Sans', 0, 0, 'Sans')
    addMapping('Sans', 0, 1, 'Sans-Italic')
    addMapping('Sans', 1, 0, 'Sans-SemiBold')
    addMapping('Sans', 1, 1, 'Sans-SemiBoldItalic')
    addMapping('Sans-SemiBold', 0, 0, 'Sans-SemiBold')
    addMapping('Sans-SemiBold', 0, 1, 'Sans-SemiBoldItalic')
    addMapping('Sans-SemiBold', 1, 0, 'Sans-Bold')
    addMapping('Sans-SemiBold', 1, 1, 'Sans-BoldItalic')


def load_modules(repo):
    bundle = sorted(glob.glob(os.path.join(repo, 'course/assets/index-*.js')))[0]
    js = r'''
const fs=require("fs");const s=fs.readFileSync(process.argv[1],"utf8");
const st=s.indexOf("qp=[")+3;let i=st,d=0,q=null;
for(;i<s.length;i++){const c=s[i];
 if(q){if(c==="\\"){i++;continue}if(c===q)q=null;continue}
 if(c==='"'||c==="'"||c==="`"){q=c;continue}
 if(c==="["||c==="{")d++;
 if(c==="]"||c==="}"){d--;if(d===0){i++;break}}}
process.stdout.write(JSON.stringify(eval("("+s.slice(st,i)+")")));
'''
    out = subprocess.run(['node', '-e', js, bundle], check=True, capture_output=True, text=True)
    return json.loads(out.stdout)


def inline(text):
    """Escape text and turn the content's **bold** / *italic* markers into markup."""
    t = html.escape(text, quote=False)
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'<i>\1</i>', t)
    return t.replace('\n', '<br/>')


# ---------- styles ----------

def S(name, **kw):
    base = dict(fontName='Sans', fontSize=9.6, leading=15, textColor=MUTED, alignment=TA_LEFT)
    base.update(kw)
    return ParagraphStyle(name, **base)


BODY = S('body', spaceAfter=7)
LABEL = S('label', fontName='Mono-Medium', fontSize=7.4, leading=10, textColor=PRIMARY, spaceBefore=6, spaceAfter=5)
H2 = S('h2', fontName='Sans-SemiBold', fontSize=16, leading=20, textColor=TEXT, spaceBefore=12, spaceAfter=6)
QUOTE = S('quote', fontName='Sans-SemiBoldItalic', fontSize=12, leading=17, textColor=TEXT)
BOX_HEAD = S('boxhead', fontName='Sans-SemiBold', fontSize=11, leading=15, textColor=TEXT, spaceAfter=3)
BOX_BODY = S('boxbody', spaceAfter=0)
SMALL = S('small', fontSize=8.8, leading=13)
CELL = S('cell', fontSize=8.6, leading=12.5)
CELL_HEAD = S('cellhead', fontName='Sans-SemiBold', fontSize=8.6, leading=12.5, textColor=TEXT)
CODE = S('code', fontName='Mono', fontSize=8.6, leading=13, textColor=CODE_TEXT)
CTA_HEAD = S('ctahead', fontName='Sans-SemiBold', fontSize=15, leading=19, textColor=white, spaceAfter=4)
CTA_BODY = S('ctabody', textColor=HexColor('#cbd5e1'))
CTA_LABEL = S('ctalabel', fontName='Mono-Medium', fontSize=7.4, leading=10, textColor=HexColor('#93c5fd'), spaceAfter=5)
CTA_BTN = S('ctabtn', fontName='Mono-Medium', fontSize=8.4, leading=11, textColor=TEXT)


def box(flows, bg=None, border=None, bar=None, pad=11, width=CONTENT_W):
    """A card: optional fill, 1px border and a 3px left accent bar."""
    t = Table([[flows]], colWidths=[width])
    style = [
        ('LEFTPADDING', (0, 0), (-1, -1), pad + (3 if bar else 0)),
        ('RIGHTPADDING', (0, 0), (-1, -1), pad),
        ('TOPPADDING', (0, 0), (-1, -1), pad),
        ('BOTTOMPADDING', (0, 0), (-1, -1), pad),
    ]
    if bg:
        style.append(('BACKGROUND', (0, 0), (-1, -1), bg))
    if border:
        style.append(('BOX', (0, 0), (-1, -1), 0.8, border))
    if bar:
        style.append(('LINEBEFORE', (0, 0), (0, -1), 3, bar))
    if not bar:
        style.append(('ROUNDEDCORNERS', [4, 4, 4, 4]))
    t.setStyle(TableStyle(style))
    return t


def render_block(b):
    t = b['type']
    if t == 'label':
        return [Paragraph(html.escape(b['text'].upper(), quote=False), LABEL)]
    if t == 'p':
        return [Paragraph(inline(b['text']), BODY)]
    if t == 'h2':
        return [Paragraph(inline(b['text']), H2)]
    if t == 'hr':
        rule = Table([['']], colWidths=[CONTENT_W], rowHeights=[1])
        rule.setStyle(TableStyle([('LINEBELOW', (0, 0), (-1, -1), 0.8, BORDER)]))
        return [Spacer(1, 6), rule, Spacer(1, 10)]
    if t == 'quote':
        return [Spacer(1, 4), box([Paragraph(inline(b['text']), QUOTE)], bar=PRIMARY, pad=8), Spacer(1, 10)]
    if t == 'callout':
        return [Spacer(1, 3), KeepTogether(box([
            Paragraph(html.escape(b['heading'].upper(), quote=False), LABEL),
            Paragraph(inline(b['body']), BOX_BODY),
        ], bg=TINT, bar=PRIMARY)), Spacer(1, 10)]
    if t == 'upnext':
        return [KeepTogether(box([
            Paragraph('UP NEXT', LABEL),
            Paragraph(inline(b['heading']), BOX_HEAD),
            Paragraph(inline(b['body']), BOX_BODY),
        ], bg=TINT, bar=PRIMARY)), Spacer(1, 12)]
    if t == 'activity':
        return [Spacer(1, 4), KeepTogether(box([
            Paragraph('TRY THIS WEEK', LABEL),
            Paragraph(inline(b['heading']), BOX_HEAD),
            Paragraph(inline(b['body']), BOX_BODY),
        ], border=PRIMARY)), Spacer(1, 12)]
    if t == 'summary':
        flows = [Paragraph('IN SUMMARY', LABEL)]
        for pt in b['points']:
            flows.append(Paragraph(inline(pt['heading']), S('sh', fontName='Sans-SemiBold', fontSize=10,
                                                             leading=14, textColor=TEXT, spaceBefore=4)))
            flows.append(Paragraph(inline(pt['body']), SMALL))
        return [KeepTogether(box(flows, border=BORDER)), Spacer(1, 12)]
    if t == 'cta':
        btn = Table([[Paragraph('REGISTER YOUR INTEREST  →  CODIFYIT.CO.UK', CTA_BTN)]])
        btn.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), CTA),
            ('ROUNDEDCORNERS', [4, 4, 4, 4]),
            ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ]))
        btn.hAlign = 'LEFT'
        return [KeepTogether(box([
            Paragraph('THE COMPLETE GUIDE', CTA_LABEL),
            Paragraph(inline(b['heading']), CTA_HEAD),
            Paragraph(inline(b['body']), CTA_BODY),
            Paragraph('Seven plain-English modules · Read on any device · No technical knowledge needed',
                      S('ctameta', fontName='Mono', fontSize=7.6, leading=11, textColor=HexColor('#94a3b8'),
                        spaceBefore=6, spaceAfter=10)),
            btn,
        ], bg=TEXT, pad=16)), Spacer(1, 12)]
    if t == 'modulelist':
        rows = []
        for m in b['modules']:
            rows.append([
                Paragraph(m['num'], S('mn', fontName='Mono-Medium', fontSize=9, leading=13, textColor=PRIMARY)),
                [Paragraph(inline(m['title']), S('mt', fontName='Sans-SemiBold', fontSize=9.4, leading=13,
                                                 textColor=TEXT)),
                 Paragraph(inline(m['desc']), S('md', fontSize=8.4, leading=12))],
            ])
        inner = Table(rows, colWidths=[24, CONTENT_W - 22 - 24 - 2])
        inner.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LINEBELOW', (0, 0), (-1, -2), 0.6, BORDER),
        ]))
        return [KeepTogether(box([Paragraph(html.escape(b['label'].upper(), quote=False), LABEL), inner], border=BORDER))]
    if t == 'table':
        rows = b['rows']
        head = b.get('header', False)
        data = [[Paragraph(inline(c), CELL_HEAD if head and r == 0 else CELL) for c in row]
                for r, row in enumerate(rows)]
        n = len(rows[0])
        widths = [CONTENT_W * 0.22] + [CONTENT_W * 0.78 / (n - 1)] * (n - 1) if n > 2 else [CONTENT_W / n] * n
        tbl = Table(data, colWidths=widths, repeatRows=1 if head else 0)
        style = [
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 7), ('RIGHTPADDING', (0, 0), (-1, -1), 7),
            ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('LINEBELOW', (0, 0), (-1, -1), 0.6, BORDER),
            ('BOX', (0, 0), (-1, -1), 0.8, BORDER),
        ]
        if head:
            style += [('BACKGROUND', (0, 0), (-1, 0), TINT), ('LINEBELOW', (0, 0), (-1, 0), 1, PRIMARY)]
        tbl.setStyle(TableStyle(style))
        return [Spacer(1, 2), tbl, Spacer(1, 10)]
    if t == 'code':
        return [Spacer(1, 2), box([Preformatted(b['text'], CODE)], bg=CODEBG), Spacer(1, 10)]
    if t in ('bullets', 'numbers'):
        items = [ListItem(Paragraph(inline(i), S('li', spaceAfter=4)), leftIndent=14) for i in b['items']]
        kw = dict(bulletType='1', bulletFormat='%s.', bulletFontName='Mono-Medium') if t == 'numbers' \
            else dict(bulletType='bullet', start='–', bulletFontName='Sans-SemiBold')
        return [ListFlowable(items, bulletColor=PRIMARY, bulletFontSize=9, leftIndent=14, **kw), Spacer(1, 6)]
    raise ValueError('unknown block type ' + t)


# ---------- page furniture ----------

def draw_cover(c, doc):
    m = doc.module
    c.saveState()
    c.setFillColor(white)
    c.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    # Navy band with the guide name
    band_h = 58 * mm
    c.setFillColor(TEXT)
    c.rect(0, PAGE_H - band_h, PAGE_W, band_h, stroke=0, fill=1)
    c.setFillColor(PRIMARY)
    c.rect(0, PAGE_H - band_h - 3, PAGE_W, 3, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont('Mono-Medium', 9)
    c.drawString(MARGIN_X, PAGE_H - 20 * mm, 'CODIFYIT')
    c.setFillColor(HexColor('#94a3b8'))
    c.setFont('Mono', 7.6)
    c.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 20 * mm, 'A GUIDE FOR PARENTS · NO TECHNICAL KNOWLEDGE NEEDED')
    c.setFillColor(white)
    c.setFont('Sans-SemiBold', 17)
    c.drawString(MARGIN_X, PAGE_H - 38 * mm, GUIDE_TITLE)
    c.setFillColor(HexColor('#cbd5e1'))
    c.setFont('Sans', 10.5)
    c.drawString(MARGIN_X, PAGE_H - 45 * mm, GUIDE_SUBTITLE)

    # Module title block
    y = PAGE_H - band_h - 38 * mm
    c.setFillColor(PRIMARY)
    c.setFont('Mono-Medium', 9)
    c.drawString(MARGIN_X, y, m['coverKicker'].upper())
    title = Paragraph(inline(m['title']), S('ct', fontName='Sans-Bold', fontSize=34, leading=38, textColor=TEXT))
    _, th = title.wrap(CONTENT_W, 400)
    title.drawOn(c, MARGIN_X, y - 12 - th)
    y = y - 12 - th - 16
    c.setFillColor(PRIMARY)
    c.rect(MARGIN_X, y, 48, 3, stroke=0, fill=1)
    deck = Paragraph(inline(m['deck']), S('cd', fontSize=12.5, leading=18.5))
    _, dh = deck.wrap(CONTENT_W * 0.8, 400)
    deck.drawOn(c, MARGIN_X, y - 16 - dh)

    # Footer
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.8)
    c.line(MARGIN_X, 22 * mm, PAGE_W - MARGIN_X, 22 * mm)
    c.setFillColor(PRIMARY)
    c.setFont('Mono-Medium', 8)
    c.drawString(MARGIN_X, 16 * mm, 'codifyit.co.uk')
    c.setFillColor(MUTED)
    c.setFont('Mono', 7.6)
    c.drawRightString(PAGE_W - MARGIN_X, 16 * mm, 'Written by a quant, for parents')
    c.restoreState()


def draw_page(c, doc):
    c.saveState()
    top = PAGE_H - 15 * mm
    c.setFont('Mono-Medium', 7.4)
    c.setFillColor(TEXT)
    c.drawString(MARGIN_X, top, doc.module['runningHead'].upper())
    c.setFont('Mono', 7.4)
    c.setFillColor(MUTED)
    c.drawRightString(PAGE_W - MARGIN_X, top, 'codifyit.co.uk')
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.8)
    c.line(MARGIN_X, top - 5, PAGE_W - MARGIN_X, top - 5)
    bottom = 14 * mm
    c.line(MARGIN_X, bottom + 9, PAGE_W - MARGIN_X, bottom + 9)
    c.drawString(MARGIN_X, bottom, GUIDE_TITLE + '  ·  © codifyit.co.uk')
    c.setFillColor(PRIMARY)
    c.setFont('Mono-Medium', 7.4)
    c.drawRightString(PAGE_W - MARGIN_X, bottom, 'PAGE %d' % (doc.page - 1))
    c.restoreState()


def build(module, out_path):
    doc = BaseDocTemplate(
        out_path, pagesize=A4,
        title=f"{GUIDE_TITLE} — {module['title']}", author='Codifyit', subject=GUIDE_SUBTITLE,
        leftMargin=MARGIN_X, rightMargin=MARGIN_X, topMargin=MARGIN_TOP, bottomMargin=MARGIN_BOTTOM,
    )
    doc.module = module
    frame = Frame(MARGIN_X, MARGIN_BOTTOM, CONTENT_W, PAGE_H - MARGIN_TOP - MARGIN_BOTTOM,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([
        PageTemplate(id='cover', frames=[frame], onPage=draw_cover),
        PageTemplate(id='body', frames=[frame], onPage=draw_page),
    ])
    story = [NextPageTemplate('body'), PageBreak()]
    for b in module['blocks']:
        story += render_block(b)
    doc.build(story)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fonts', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--only', nargs='*')
    args = ap.parse_args()
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    register_fonts(args.fonts)
    os.makedirs(args.out, exist_ok=True)
    for m in load_modules(repo):
        if args.only and m['outfile'] not in args.only:
            continue
        path = os.path.join(args.out, m['outfile'])
        build(m, path)
        print('wrote', path)


if __name__ == '__main__':
    main()
