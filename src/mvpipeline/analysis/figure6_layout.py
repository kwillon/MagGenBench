"""Figure 6 bar-label gutter using frozen values; no metric recalculation."""
from __future__ import annotations
import csv
import hashlib
from pathlib import Path

LABEL_OFFSET_PT=4.0
MIN_FRAME_CLEARANCE_PT=7.0
MIN_RIGHT_LIMIT=124.0


def ensure_bar_label_clearance(ax,labels):
    """Extend only the display limit until every annotation fits inside the frame."""
    left,right=ax.get_xlim()
    ax.set_xlim(left,max(right,MIN_RIGHT_LIMIT))
    for _ in range(20):
        ax.figure.canvas.draw()
        renderer=ax.figure.canvas.get_renderer()
        gap=min((ax.get_window_extent(renderer).x1-label.get_window_extent(renderer).x1)*72/ax.figure.dpi for label in labels)
        if gap>=MIN_FRAME_CLEARANCE_PT:return gap
        ax.set_xlim(left,left+(ax.get_xlim()[1]-left)*1.05)
    raise RuntimeError('Could not fit Figure 6 value labels inside the frame')


def add_bar_value_labels(ax,bars,strings,*,color='black',fontsize=8.8):
    labels=[]
    for bar,text in zip(bars,strings):
        label=ax.annotate(text,(bar.get_width(),bar.get_y()+bar.get_height()/2),
            xytext=(LABEL_OFFSET_PT,0),textcoords='offset points',ha='left',va='center',
            fontsize=fontsize,color=color,clip_on=False)
        label._maggenbench_bar_value=True
        labels.append(label)
    return labels


def polish_figure6_bar_layout(source,output,*,summary_path=None):
    """Retain A/B verbatim; redraw C/D at the same positions with a label gutter."""
    import pymupdf as fitz
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from .typography import apply_ebrima_typography, _numeric_tokens
    root=Path(__file__).resolve().parents[3]
    summary_path=Path(summary_path or root/'tables/figure_sources/fig06_diversity_summary.csv')
    data_hash=hashlib.sha256(summary_path.read_bytes()).hexdigest()
    with summary_path.open(encoding='utf-8',newline='') as f:
        summary={r['analysis_cohort']:r for r in csv.DictReader(f)}
    cohorts=['mattergen_baseline','mattergen_finetuned','concdvae_baseline','concdvae_finetuned',
             'crystalformer_baseline','crystalformer_finetuned','crystallm_baseline','crystallm_finetuned',
             'crysjepa_base','crysjepa_refined']
    names=['MatterGen Base','MatterGen FT','Con-CDVAE Base','Con-CDVAE FT','CrystalFormer Base',
           'CrystalFormer FT','CrystaLLM Base','CrystaLLM FT','Crys-JEPA Base','Crys-JEPA Refined']
    source,output=Path(source),Path(output)
    if output.exists():raise FileExistsError(output)
    original=fitz.open(source);page=original[0]
    width,height=page.rect.width,page.rect.height
    boundary=620.0
    drawings=page.get_drawings()
    # Original frame coordinates and bar colors are read from the actual selected
    # figure, avoiding substitutions from historical palette modules.
    frames=sorted([d['rect'] for d in drawings if d['fill']==(1.,1.,1.) and
                   d['rect'].y0>boundary and d['rect'].width>300 and d['rect'].height>100],key=lambda r:r.x0)
    assert len(frames)==2,frames
    apply_ebrima_typography()
    fig=plt.figure(figsize=(width/72,(height-boundary)/72),dpi=150,facecolor='white')
    audit=[]
    for i,(frame,metric,count,title) in enumerate(zip(frames,
            ('unique_formula_percent','unique_formula_sg_percent'),
            ('n_unique_formula','n_unique_formula_sg'),
            ('C  Unique reduced formulas','D  Unique formula–space group pairs'))):
        raw=sorted([d for d in drawings if d['fill'] is not None and d['fill']!=(1.,1.,1.) and
                    len(d['items'])==1 and d['items'][0][0]=='re' and
                    abs(d['rect'].x0-frame.x0)<.02 and 5<d['rect'].height<30 and frame.contains(d['rect'])],key=lambda d:d['rect'].y0)
        assert len(raw)==10,len(raw)
        values=[float(summary[c][metric]) for c in cohorts]
        ratios=[r['rect'].width/v for r,v in zip(raw,values)]
        assert np.ptp(ratios)<1e-4,'Stored values disagree with the original bar geometry'
        old_limit=frame.width/np.mean(ratios)
        centers=[(r['rect'].y0+r['rect'].y1)/2 for r in raw]
        spacing=float(np.mean(np.diff(centers)))
        ymin=-(centers[0]-frame.y0)/spacing
        ymax=ymin+frame.height/spacing
        ax=fig.add_axes([frame.x0/width,(height-frame.y1)/(height-boundary),frame.width/width,frame.height/(height-boundary)])
        bars=[]
        for j,(value,style) in enumerate(zip(values,raw)):
            bar=ax.barh([j],[value],height=style['rect'].height/spacing,
                         color=style['fill'],alpha=style.get('fill_opacity',1),
                         edgecolor=style['color'] or style['fill'],linewidth=style['width'])[0]
            bars.append(bar)
        ax.set_ylim(ymax,ymin)
        ax.set_xlim(0,MIN_RIGHT_LIMIT)
        ax.set_xticks([0,20,40,60,80,100])
        ax.set_yticks(range(10),names)
        ax.tick_params(axis='both',labelsize=9.5,colors='black',width=.8)
        ax.set_xlabel('Unique entries (%)',fontsize=11.5,color='black')
        ax.set_title(title,loc='left',fontsize=14.5,fontweight='normal',pad=7,color='black')
        for spine in ax.spines.values():
            spine.set_visible(True);spine.set_color('black');spine.set_linewidth(.8)
        ax.grid(axis='x',color='#D5D5D5',linewidth=.45,alpha=.5)
        ax.set_axisbelow(True)
        strings=[f"{v:.1f}% ({int(summary[c][count])}/{int(summary[c]['n'])})" for c,v in zip(cohorts,values)]
        labels=add_bar_value_labels(ax,bars,strings)
        clearance=ensure_bar_label_clearance(ax,labels)
        audit.append(dict(panel='CD'[i],old_xlim=[0,old_limit],new_xlim=list(ax.get_xlim()),
                          offset_pt=LABEL_OFFSET_PT,min_frame_clearance_pt=clearance,
                          cohorts=cohorts,values=values,labels=strings,
                          colors=[list(d['fill']) for d in raw]))
    raw_pdf=output.with_suffix('.bars.pdf')
    output.parent.mkdir(parents=True,exist_ok=True)
    with matplotlib.rc_context({'savefig.bbox':None}):fig.savefig(raw_pdf,bbox_inches=None,pad_inches=0)
    plt.close(fig)
    bottom=fitz.open(raw_pdf)
    result=fitz.open();new_page=result.new_page(width=width,height=height)
    upper=fitz.Rect(0,0,width,boundary)
    # Remove obsolete C/D text, rather than leaving an invisible duplicate
    # underneath the clipping boundary in the composed PDF.
    upper_doc=fitz.open(stream=original.tobytes(),filetype='pdf')
    upper_doc[0].add_redact_annot(fitz.Rect(0,boundary,width,height),fill=False)
    upper_doc[0].apply_redactions(images=0,graphics=0)
    new_page.show_pdf_page(upper,upper_doc,0,clip=upper,keep_proportion=False)
    new_page.show_pdf_page(fitz.Rect(0,boundary,width,height),bottom,0,keep_proportion=False)
    result.save(output,garbage=4,deflate=True)
    final=fitz.open(output)
    before_pixels=page.get_pixmap(matrix=fitz.Matrix(2,2),clip=upper).samples
    after_pixels=final[0].get_pixmap(matrix=fitz.Matrix(2,2),clip=upper).samples
    assert before_pixels==after_pixels,'Figure 6 A/B changed during composition'
    assert _numeric_tokens(page.get_text())==_numeric_tokens(final[0].get_text()),'Figure 6 numerical labels changed'
    assert hashlib.sha256(summary_path.read_bytes()).hexdigest()==data_hash
    for document in (final,result,bottom,upper_doc,original):document.close()
    return dict(panels=audit,upper_AB_render_identical=True,numeric_tokens_unchanged=True,
                source_sha256=data_hash,all_values_order_and_colors_preserved=True)
