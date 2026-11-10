"""Shared Ebrima Regular typography; no scientific data transformations.

Fonts are discovered locally, never vendored. Missing Ebrima is an error.
The PDF route retains existing graphical operators, including rasterized scatter
samples and historical vector statistics, and replaces only text operators.
"""
from __future__ import annotations
import hashlib
import os
import re
from collections import Counter
from pathlib import Path

FONT_SIZE_INCREASE_PT = 0.5


def publication_figure_name(name):
    """Map the former selected Figure 8 filename; leave historical variants intact."""
    if name in ('fig08_multiobjective.pdf', 'fig08_multiobjective.png', 'fig08_multiobjective.svg'):
        return name.replace('fig08_', 'fig07_', 1)
    return name

TEXT_CORRECTIONS = {
    'Min-max normalized score': 'Min–max normalized score',
    'Compound-class distribution': 'Compound class distribution',
    'Adaptation-associated changes': 'Changes associated with adaptation',
    'Magnetic-sublattice geometry': 'Magnetic sublattice geometry',
    'Descriptor-space PCA and cohort-centroid shifts': 'Descriptor space PCA and cohort centroid shifts',
    'Unique formula–space-group pairs': 'Unique formula–space group pairs',
    'Magnetic-neighbor fraction': 'Magnetic neighbor fraction',
    'Local magnetic-neighbor environment': 'Local magnetic neighbor environment',
    'Contrast: d(NM) - d(magnetic)': 'Contrast: d(NM) − d(magnetic)',
    '5-95%': '5–95%',
    'Crys-JEPA Ref.': 'Crys-JEPA Refined',
    '3d atomic-\ncontent yield': '3d atomic-content\nyield',
    'Lanthanide atomic-\ncontent yield': 'Lanthanide\natomic-content yield',
}


def ebrima_font_path() -> Path:
    configured=os.environ.get('MAGGENBENCH_EBRIMA_FONT')
    candidates=[Path(configured)] if configured else [Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts/ebrima.ttf']
    from matplotlib import font_manager
    for candidate in candidates:
        if candidate.is_file():
            font_manager.fontManager.addfont(str(candidate))
            prop=font_manager.FontProperties(fname=str(candidate))
            if prop.get_name()!='Ebrima':
                raise RuntimeError(f'Expected Ebrima Regular, found {prop.get_name()}: {candidate}')
            from fontTools.ttLib import TTFont
            with TTFont(candidate) as font:
                if font['OS/2'].usWeightClass!=400:
                    raise RuntimeError('Only Ebrima Regular (weight 400) is allowed')
            return candidate.resolve()
    raise RuntimeError('Ebrima Regular is unavailable. Install it locally or set MAGGENBENCH_EBRIMA_FONT; no fallback is permitted.')


def apply_ebrima_typography():
    from matplotlib import font_manager
    import matplotlib.pyplot as plt
    path=ebrima_font_path()
    plt.rcParams.update({'font.family':['Ebrima'],'font.sans-serif':['Ebrima'],
        'font.weight':'normal','axes.titleweight':'normal','axes.labelweight':'normal',
        'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none',
        'axes.unicode_minus':True,'mathtext.fontset':'custom',
        'mathtext.rm':'Ebrima','mathtext.it':'Ebrima','mathtext.bf':'Ebrima'})
    resolved=Path(font_manager.findfont(font_manager.FontProperties(family='Ebrima',weight='normal'),fallback_to_default=False))
    if resolved.resolve()!=path:
        raise RuntimeError(f'Matplotlib resolved a different font: {resolved}')
    return path


def correct_text(text):
    for old,new in TEXT_CORRECTIONS.items():text=text.replace(old,new)
    if re.fullmatch(r'-\d+(?:\.\d+)?',text):text='−'+text[1:]
    text=re.sub(r'^(MatterGen|Con-CDVAE|CrystalFormer|CrystaLLM) Fine-tuned$',r'\1 FT',text)
    return text


def prepare_figure_typography(fig):
    """Apply one regular family to all text artists immediately before export."""
    from matplotlib.text import Text
    from matplotlib.font_manager import FontProperties
    path=apply_ebrima_typography()
    fig.canvas.draw()
    titles={t for ax in fig.axes for t in (ax.title,ax._left_title,ax._right_title)}
    axes_labels={t for ax in fig.axes for t in (ax.xaxis.label,ax.yaxis.label)}
    ticks={t for ax in fig.axes for t in [*ax.get_xticklabels(),*ax.get_yticklabels()]}
    for artist in fig.findobj(match=Text):
        artist.set_text(correct_text(artist.get_text()))
        size=14 if artist in titles or re.match(r'^[A-F](?:\s{1,3}\S|$)',artist.get_text()) else 11 if artist in axes_labels else 9 if artist in ticks else min(10,max(8.3,artist.get_fontsize()))
        if artist is fig._suptitle:size=16
        size += FONT_SIZE_INCREASE_PT
        if getattr(artist, '_maggenbench_bar_value', False):size=8.3+FONT_SIZE_INCREASE_PT
        prop=FontProperties(fname=str(path),size=size,weight='normal')
        artist.set_fontproperties(prop)
    from .figure6_layout import ensure_bar_label_clearance
    for ax in fig.axes:
        labels=[t for t in ax.texts if getattr(t,'_maggenbench_bar_value',False)]
        if labels:ensure_bar_label_clearance(ax,labels)


def _drawing_signature(page):
    # Text contributes sequence numbers, so only the scientific graphics are compared.
    return [repr({k:v for k,v in item.items() if k not in ('seqno','layer')}) for item in page.get_drawings()]


def _image_signature(page):
    return [(tuple(i['bbox']),i['width'],i['height'],bytes(i.get('digest',b'')))
            for i in page.get_image_info(hashes=True)]


def _numeric_tokens(text):
    return Counter(re.findall(r'[+−-]?\d+(?:\.\d+)?',text.replace('–','-').replace('−','-')))


def fix_ebrima_to_unicode(doc):
    """Disambiguate shared Ebrima glyphs for reliable PDF search/copy/paste."""
    for page in doc:
        for f in page.get_fonts():
            if 'Ebrima' not in f[3]:continue
            kind,value=doc.xref_get_key(f[0],'ToUnicode')
            if kind=='xref':
                ref=int(value.split()[0]);cmap=doc.xref_stream(ref)
                cmap=re.sub(rb'(<[0-9a-fA-F]+>\s*)<00[aA]0>',rb'\1<0020>',cmap)
                cmap=re.sub(rb'(<[0-9a-fA-F]+>\s*)<00[aA][dD]>',rb'\1<002d>',cmap)
                doc.update_stream(ref,cmap)


def _base_font_size(name,text,old):
    """Sizes in native page points; dense annotations remain smaller than axes."""
    title=bool(re.match(r'^[A-F]\s{1,3}\S',text)) or text in ('A','B','C','D')
    axis=text in ('Rank','PCA component coefficient','PC1','PC2','Unique entries (%)',
        'QC retention (%)','Unique-formula yield (%)','Top-5 frequency (%)',
        'Min–max normalized score','Weight combinations (%)','Share within cohort (%)',
        'Prevalence (%)','Atomic fraction','(nonzero only)','Magnetic neighbor fraction',
        'Structural QC retention (%)') or text.startswith(('CHGNet','DXMag','Contrast:','Fraction among','PC1 (','PC2 ('))
    axis = axis or text in ('Share of rejected structures (%)','Fine-tuned/Refined minus Base (pp)') or text.startswith(('Fraction closer','Fraction confirmed'))
    if name.startswith('fig04'):
        return 14 if title else 11 if axis else 10 if old>=14 else 9.5
    if title:return 14
    if name.startswith('fig06'):
        if text in ('Compound class distribution','Changes associated with adaptation'):return 14
        if old<=7.1:return 8.3
        return 11 if axis or old>=12 else 9
    if name.startswith(('fig07', 'fig08')):
        return 11 if axis else 10 if old>=10.5 else 9
    if name.startswith('fig02'):
        if text in ('Base','Fine-tuned (FT)','Crys-JEPA','Base: registered primary rejection reasons'):return 12
        return 11 if axis else 9 if old<10 else 10
    if name.startswith('fig03'):return 11 if axis else 10
    if name.startswith('fig05'):return 11 if axis else 9 if old<=10 else 10
    if name.startswith('supp01'):
        if ': PC' in text:return 14
        return 11 if axis else 9
    if name.startswith('supp02'):
        if text.startswith('Descriptor space PCA'):return 16
        if text in ('Composition and symmetry','Magnetic sublattice geometry'):return 14
        if text in ('MatterGen','Con-CDVAE','CrystalFormer','CrystaLLM','Crys-JEPA'):return 12
        return 11 if axis else 9
    return old


def _font_size(name,text,old):
    return _base_font_size(name,text,old)+FONT_SIZE_INCREASE_PT


def restyle_pdf_typography(source,output,*,figure_name=None):
    """Replace text only; prove numbers, drawings, images and page boxes unchanged."""
    import pymupdf as fitz
    source,output=Path(source),Path(output)
    name=figure_name or source.name
    if name.startswith('fig01') or source.name.startswith('fig01') or output.name.startswith('fig01'):
        raise ValueError('Figure 1 is a read-only typography reference')
    if source.resolve()==output.resolve():raise ValueError('Use a separate validation output PDF')
    if output.exists():raise FileExistsError(output)
    path=ebrima_font_path();font=fitz.Font(fontfile=str(path))
    doc=fitz.open(source)
    streams={x for page in doc for x in page.get_contents()}
    streams.update(x for x in range(1,doc.xref_length()) if doc.xref_get_key(x,'Subtype')==('name','/Form'))
    # Matplotlib Type-3 exports some minus/en-dash glyphs as vector XObjects,
    # rather than PDF text. Replace ONLY named font glyph invocations, retaining
    # every scientific path; recover negative signs before comparing numbers.
    glyphs=[[] for _ in doc]
    for suffix,char in (('minus','−'),('endash','–')):
        before=[page.get_drawings() for page in doc]
        for xref in streams:
            content=doc.xref_stream(xref)
            stripped=re.sub(rb'/[^\s/]+-'+suffix.encode()+rb'\s+Do\b',b'',content)
            if content!=stripped:doc.update_stream(xref,stripped)
        for i,page in enumerate(doc):
            after=Counter(_drawing_signature(page))
            for drawing in before[i]:
                key=repr({k:v for k,v in drawing.items() if k not in ('seqno','layer')})
                if after[key]:after[key]-=1
                else:glyphs[i].append(dict(character=char,rect=list(drawing['rect'])))
    records=[];graphics=[];images=[];changes=[];size_records=[]
    for page_index,page in enumerate(doc):
        items=[]
        graphics.append(_drawing_signature(page));images.append(_image_signature(page))
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                for span in line['spans']:
                    items.append(dict(span,direction=line['dir']))
        for glyph in glyphs[page_index]:
            rect=fitz.Rect(glyph['rect'])
            if glyph['character']=='−':
                candidates=[a for a in items if re.fullmatch(r'\d+(?:\.\d+)?',a['text']) and
                            -.5 <= a['bbox'][0]-rect.x1 < 18 and
                            a['bbox'][1] <= rect.y0 <= a['bbox'][3]]
                if not candidates:
                    # Figure 6's source Form includes a clipped-away upper half.
                    # PyMuPDF exposes its paths but correctly omits its text.
                    if name.startswith('fig06'):continue
                    raise RuntimeError(f'Cannot associate vector minus with its number: {name}, {rect}')
                item=min(candidates,key=lambda a:abs(a['bbox'][0]-rect.x1))
                item['text']='−'+item['text']
                item['bbox']=(rect.x0,*item['bbox'][1:])
                item['origin']=(rect.x0,item['origin'][1])
            elif name.startswith('fig06'):
                left=next(a for a in items if a['text']=='D  Unique formula')
                right=next(a for a in items if a['text']=='space-group pairs')
                left['text']='D  Unique formula–space-group pairs'
                left['override']='D  Unique formula–space group pairs'
                left['bbox']=(left['bbox'][0],left['bbox'][1],right['bbox'][2],left['bbox'][3])
                items.remove(right)
            else:raise RuntimeError(f'Unexpected vector en-dash in {name}')
        # Preserve the approved multiobjective matrix (now Figure 7).
        for item in items:
            text=item['text'];new=item.get('override',correct_text(text))
            if name.startswith('fig02') and new=='Crys-JEPA Refined':
                new='Crys-JEPA\nRefined'
            if name.startswith(('fig07', 'fig08')):
                if text=='3d atomic-':new='3d atomic-content'
                if text=='Lanthanide atomic-':new='Lanthanide'
                if text=='content yield':
                    above=[a for a in items if a['text'] in ('3d atomic-','Lanthanide atomic-') and
                           0<item['origin'][1]-a['origin'][1]<25]
                    parent=min(above,key=lambda a:abs((a['bbox'][0]+a['bbox'][2])-(item['bbox'][0]+item['bbox'][2])))
                    new='yield' if parent['text']=='3d atomic-' else 'atomic-content yield'
            item['new']=new
            if new!=text:changes.append(dict(figure=name,original=text,corrected=new))
        assert _numeric_tokens(' '.join(a['text'] for a in items))==_numeric_tokens(' '.join(a['new'] for a in items))
        records.append(items)
    # Remove text blocks only from content/Form streams, never image/font streams.
    removed=[]
    for xref in streams:
        content=doc.xref_stream(xref)
        stripped=re.sub(rb'(?<!\S)BT\b.*?\bET(?=\s|$)',b'',content,flags=re.S)
        if stripped!=content:doc.update_stream(xref,stripped);removed.append(xref)
    # Old font resources are now unused; prevent stale font tables in pdffonts.
    for xref in [page.xref for page in doc]+list(streams):
        kind,value=doc.xref_get_key(xref,'Resources')
        if kind=='xref':doc.xref_set_key(int(value.split()[0]),'Font','null')
        elif kind=='dict':doc.xref_set_key(xref,'Resources/Font','null')
    for page in doc:
        assert not page.get_text().strip(),'Text survived stream-only removal'
    expected=[]
    for page,items in zip(doc,records):
        page.insert_font(fontname='PublicationEbrima',fontfile=str(path))
        for item in items:
            text=item['new']
            for char in text:
                if not char.isspace() and not font.has_glyph(ord(char)):
                    raise RuntimeError(f'Ebrima has no glyph U+{ord(char):04X}: {text}')
            size=_font_size(name,text,item['size'])
            x,y=item['origin'];dx,dy=item['direction']
            old_width=fitz.Point(item['bbox'][2]-item['bbox'][0],item['bbox'][3]-item['bbox'][1])
            advance=abs(dx)*old_width.x+abs(dy)*old_width.y
            lines=text.split('\n')
            new_width=max(font.text_length(line,fontsize=size) for line in lines)
            align='left' if re.match(r'^[A-F]\s{1,3}\S',text) else 'center'
            if re.match(r'^(MatterGen|Con-CDVAE|CrystalFormer|CrystaLLM|Crys-JEPA) (Base|FT|Fine-tuned|Ref)',text):align='right'
            if name.startswith(('fig07', 'fig08')) and text.endswith('%') and item['bbox'][0]>.60*page.rect.width and item['bbox'][1]>.5*page.rect.height:align='left'
            shift=(advance-new_width)*(1 if align=='right' else .5 if align=='center' else 0)
            x+=dx*shift;y+=dy*shift
            if len(lines)>1:y-=.5*size*1.2*(len(lines)-1)
            # Font ascenders differ: keep every glyph inside the same page box.
            corners=[(x+dx*t-dy*v,y+dy*t+dx*v) for t in (0,new_width)
                     for v in (-font.ascender*size,-font.descender*size)]
            xmin,xmax=min(p[0] for p in corners),max(p[0] for p in corners)
            ymin,ymax=min(p[1] for p in corners),max(p[1] for p in corners)
            x+=max(0,1-xmin)-max(0,xmax-page.rect.width+1)
            y+=max(0,1-ymin)-max(0,ymax-page.rect.height+1)
            # Keep the original baseline and rotation; layout is not recomputed.
            angle=round(__import__('math').degrees(__import__('math').atan2(-dy,dx)))%360
            color=fitz.sRGB_to_pdf(item['color'])
            for j,line in enumerate(lines):
                lx=x+(new_width-font.text_length(line,fontsize=size) if align=='right' else 0)
                ly=y+j*size*1.2
                page.insert_text((lx,ly),line,fontsize=size,fontname='PublicationEbrima',color=color,
                                 morph=(fitz.Point(lx,ly),fitz.Matrix(angle)) if angle else None)
            size_records.append(dict(text=text,old_size=item['size'],size=size,figure=name))
            expected.append(text)
    output.parent.mkdir(parents=True,exist_ok=True)
    doc.subset_fonts()
    # Ebrima shares glyphs for SPACE/NBSP and HYPHEN/SOFT HYPHEN. Prefer the
    # visible ASCII characters in ToUnicode; never leave accidental soft hyphens.
    fix_ebrima_to_unicode(doc)
    doc.save(output,garbage=4,deflate=True)
    final=fitz.open(output)
    actual=[];bounds=[];font_names=set();embedded=True
    for i,page in enumerate(final):
        assert page.rect==doc[i].rect
        assert _drawing_signature(page)==graphics[i],f'Graphical vectors changed: {name}'
        assert _image_signature(page)==images[i],f'Rasterized data changed: {name}'
        for b in page.get_text('dict')['blocks']:
            for line in b.get('lines',[]):
                for s in line['spans']:
                    actual.append(s['text']);font_names.add(s['font'])
                    if not page.rect.contains(fitz.Rect(s['bbox'])):bounds.append(s)
        for f in page.get_fonts():
            assert 'Ebrima' in f[3],f
            embedded=embedded and bool(final.extract_font(f[0])[3])
    assert _numeric_tokens(' '.join(expected))==_numeric_tokens(' '.join(actual)),f'Numeric text changed or clipped: {name}'
    assert all('Ebrima' in n for n in font_names) and embedded
    return dict(figure=name,before_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                after_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                fonts=sorted(font_names),embedded=embedded,text_changes=changes,font_sizes=size_records,
                graphics_unchanged=True,images_unchanged=True,numeric_tokens_unchanged=True,
                outside_page=bounds,removed_text_streams=len(removed),
                vector_font_glyphs_replaced=sum(len(g) for g in glyphs))
