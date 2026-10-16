import fitz,re,json,pathlib,shutil,zipfile,os
OUT=pathlib.Path(__file__).resolve().parent; BASE=OUT/'source_pdfs'
PAPERS=[('2022 CS1','22CS1.pdf','22CS1_A.pdf'),('2023 CS1','23CS1.pdf','23CS1_A.pdf'),('2024 CS1','24CS1.pdf','24CS1_A.pdf'),('2024 CS2','24CS2.pdf','24CS2_A.pdf'),('2025 CS1','25CS1.pdf','25CS1_A.pdf'),('2025 CS2','25CS2.pdf','25CS2_A.pdf'),('2026 CS1','26CS1.pdf','26CS1_A.pdf'),('2026 CS2','26CS2.pdf','26CS2_A.pdf')]

def pdftext(path, ocr_if_empty=False):
    d=fitz.open(path); pages=[]
    for p in d:
        t=p.get_text('text') or ''
        if ocr_if_empty and len(t.strip())<15:
            pix=p.get_pixmap(matrix=fitz.Matrix(1.6,1.6),alpha=False); tmp=OUT/'tmpocr.png';pix.save(tmp)
            import subprocess
            try:t=subprocess.run(['tesseract',str(tmp),'stdout','-l','eng'],capture_output=True,text=True,timeout=30).stdout
            except Exception:t=''
        pages.append(t)
    return pages,'\n'.join(pages)

def parse_key(path):
    _,t=pdftext(path,True); t=re.sub(r'\s+',' ',t)
    pat=re.compile(r'(?<!\d)(\d{1,2})\s+\d+\s+(MCQ|MSQ|NAT)\s+(GA|CS-1|CS-2|CS)\s+([A-D](?:\s*[;,]\s*[A-D])*|MTA|-?\d+(?:\.\d+)?\s+to\s+-?\d+(?:\.\d+)?(?:\s+OR\s+-?\d+(?:\.\d+)?\s+to\s+-?\d+(?:\.\d+)?)?)\s+([12])\b',re.I)
    keys={}
    for m in pat.finditer(t):
        q=int(m.group(1));typ=m.group(2).upper();sec=m.group(3).upper();raw=m.group(4).upper().replace(' ','');marks=int(m.group(5))
        if typ=='NAT':ans=re.findall(r'-?\d+(?:\.\d+)?',raw)
        elif raw=='MTA':ans=['MTA']
        else:ans=re.findall(r'[A-D]',raw)
        keys[q]={'type':typ,'section':sec,'key':ans,'raw':m.group(4),'marks':marks,'answer_variants':[]}
    # GATE 2023 Q27 official key permits either A,C,D or C,D. Parser previously dropped this row.
    if pathlib.Path(path).name=='23CS1_A.pdf':
        keys[27]={'type':'MSQ','section':'CS','key':['C','D'],'raw':'A, C, D OR C, D','marks':1,'answer_variants':[['A','C','D'],['C','D']]}
    return keys,t

def parse_questions(path):
    pages,t=pdftext(path,True)
    matches=list(re.finditer(r'(?i)\bQ\s*\.\s*(\d{1,2})(?!\s*[-–]\s*Q)\s*(?:[.)])?\s*',t))
    if len(matches)<20:matches=list(re.finditer(r'(?im)^\s*(\d{1,2})\s*[.)]\s+',t))
    # Find which PDF page contains each match and whether the label is near its top or bottom.
    starts=[]; pos=0
    for page in pages: starts.append(pos);pos+=len(page)+1
    def page_for(offset):
        pi=max(i for i,x in enumerate(starts) if x<=offset)
        return pi+1, max(0,offset-starts[pi])/max(1,len(pages[pi]))
    qs=[]
    # A few GATE PDFs put the question label at the bottom of the page in extraction order.
    # Segment between labels and assign the body to the label at the top OR to the next footer label.
    for i in range(len(matches)-1):
        a,b=matches[i],matches[i+1]
        ap,ar=page_for(a.start());bp,br=page_for(b.start())
        if br>0.68:
            n=int(b.group(1)); chunk=t[a.end():b.start()]; body_start=a.end()
        elif ar<0.35:
            n=int(a.group(1)); chunk=t[a.end():b.start()]; body_start=a.end()
        else:
            continue
        # If label and body are separated by a page break, remove running headers/footers only.
        chunk=re.sub(r'(?im)^\s*(?:Page\s+\d+\s+of\s+\d+|Organizing Institute:.*|Organising Institute:.*|GATE\s+20\d\d.*|Computer Science and Information Technology.*)\s*$','',chunk).strip()
        opt_matches=list(re.finditer(r'(?im)^\s*\(?\s*([A-D])\s*\)?\s*[.)]?\s+',chunk))
        opts=[]
        if len(opt_matches)>=2:
            stem=chunk[:opt_matches[0].start()].strip()
            for j,om in enumerate(opt_matches):
                oe=opt_matches[j+1].start() if j+1<len(opt_matches) else len(chunk);val=re.sub(r'\s+',' ',chunk[om.end():oe]).strip()
                if val:opts.append({'value':om.group(1).upper(),'text':val})
            chunk=stem
        chunk=re.sub(r'\s+',' ',chunk).strip()
        if len(chunk)<5 and not opts:continue
        page_num,_=page_for(body_start)
        qs.append({'number':n,'text':chunk,'options':opts,'page_hint':page_num,'source_page':page_num})
    # If the parser misses a question, keep a fallback record from the previous simple strategy.
    # Deduplicate by number, retaining the body with the most substantive text/options.
    out=[];seen={}
    for q in qs:
        if q['number'] not in seen or len(q['text'])+sum(len(o['text']) for o in q['options']) > len(out[seen[q['number']]]['text'])+sum(len(o['text']) for o in out[seen[q['number']]]['options']):
            if q['number'] in seen:out[seen[q['number']]]=q
            else:seen[q['number']]=len(out);out.append(q)
    # Ensure all expected numbers 1-65 exist by falling back to the earlier simple parser where necessary.
    missing=set(range(1,66))-set(q['number'] for q in out)
    if missing:
        old=list(re.finditer(r'(?i)\bQ\s*\.\s*(\d{1,2})(?!\s*[-–]\s*Q)\s*(?:[.)])?\s*',t))
        for i,m in enumerate(old):
            n=int(m.group(1))
            if n not in missing:continue
            chunk=t[m.end():old[i+1].start() if i+1<len(old) else len(t)].strip()
            om=list(re.finditer(r'(?im)^\s*\(?\s*([A-D])\s*\)?\s*[.)]?\s+',chunk));opts=[]
            if len(om)>=2:
                stem=chunk[:om[0].start()].strip()
                for j,x in enumerate(om):opts.append({'value':x.group(1).upper(),'text':re.sub(r'\s+',' ',chunk[x.end():om[j+1].start() if j+1<len(om) else len(chunk)]).strip()})
                chunk=stem
            pg,_=page_for(m.start());out.append({'number':n,'text':re.sub(r'\s+',' ',chunk).strip(),'options':opts,'page_hint':pg,'source_page':pg})
    # Final deduplication protects against repeated labels at page breaks.
    best={}
    for q in out:
        score=len(q['text'])+sum(len(o['text']) for o in q['options'])
        old=best.get(q['number'])
        oldscore=(len(old['text'])+sum(len(o['text']) for o in old['options'])) if old else -1
        if old is None or score>oldscore:best[q['number']]=q
    out=sorted(best.values(),key=lambda q:q['number'])
    return out,t,len(pages)

allpapers=[];summary=[]
for title,pdf,keypdf in PAPERS:
    qs,txt,pages=parse_questions(BASE/pdf);keys,keytxt=parse_key(BASE/keypdf)
    for q in qs:
        k=keys.get(q['number']);q['answer']=k['key'] if k else [];q['answer_variants']=k.get('answer_variants',[]) if k else [];q['answer_raw']=k['raw'] if k else None
        q['type']=k['type'] if k else ('MCQ' if q['options'] else 'NAT');q['section']=k['section'] if k else ('GA' if q['number']<=10 else 'CS');q['marks']=k['marks'] if k else (1 if q['number']<=35 else 2)
        q['needs_review']=not bool(k) or q['source_page'] is None or (q['type'] in ('MCQ','MSQ') and len(q['options'])<2) or (q['type']=='NAT' and not q['answer'])
    paper={'id':re.sub(r'[^a-z0-9]+','-',title.lower()).strip('-'),'title':title,'source_pdf':pdf,'key_pdf':keypdf,'pages':pages,'questions':qs,'key_count':len(keys),'text_chars':len(txt),'review_count':sum(q['needs_review'] for q in qs)}
    allpapers.append(paper);summary.append({'title':title,'pages':pages,'questions_detected':len(qs),'key_entries':len(keys),'review_needed':paper['review_count'],'questions_without_source_page':sum(q['source_page'] is None for q in qs)})
json.dump(allpapers,open(OUT/'papers.json','w',encoding='utf-8'),ensure_ascii=False)
print(json.dumps(summary,indent=2))
