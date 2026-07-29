#!/usr/bin/env python3
"""MAGALENHA v3 — figuras preenchidas via máscara, fluxo curvado, frases da música."""
from PIL import Image, ImageDraw, ImageFont
import numpy as np, img2pdf, math, sys
from scipy import ndimage as ndi
from scipy.ndimage import sobel, gaussian_filter, binary_dilation

DPI = int(sys.argv[1]) if len(sys.argv)>1 else 150
def mm(x): return x/25.4*DPI

# tamanho definido a partir da ALTURA das figuras -> margem justa
ART_H_CM=88.0; TOP_CM=13.0; BOT_CM=10.5; SIDE_CM=7.0
SRC="/mnt/user-data/uploads/A5613A3C-E617-4518-9A6A-F1AE698EFB70.png"
CROP=(600,55,1420,782)                     # 3 figuras limpas

FB="/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"
FR="/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf"
INK=(17,17,17); TERRA=(150,58,42); GREY=(105,105,105)
LINE_H=max(9,int(mm(3.5))); FS_MIN=max(7,int(mm(1.5))); FS_MAX=int(LINE_H*1.7)
GAMMA=1.5; FILLMIN=0.30

LINES=["Vem, Magalenha Rojão","Traz a lenha pro fogão","Vem fazer armação",
       "Hoje é um dia de Sol","Alegria de coió","É curtir o verão",
       "Tchê tchê tchê-tchê-tchê"]
def stream(): return list((("   ".join(LINES)+"   ")*60))
def spaced(t,n=1): return (" "*n).join(list(t))

_tiles={}
def tile(ch,fs,bold,abkt,color):
    k=(ch,fs,bold,abkt,color); t=_tiles.get(k)
    if t is None:
        f=ImageFont.truetype(FB if bold else FR,fs); bb=f.getbbox(ch)
        w=max(1,bb[2]-bb[0]); h=max(1,bb[3]-bb[1]); p=2
        im=Image.new("RGBA",(w+2*p,h+2*p),(0,0,0,0))
        ImageDraw.Draw(im).text((p-bb[0],p-bb[1]),ch,font=f,fill=color+(255,))
        if abkt: im=im.rotate(abkt*3,expand=True,resample=Image.BICUBIC)
        _tiles[k]=t=(im,w)
    return t

def main():
    im=Image.open(SRC).convert("RGB").crop(CROP); cw,ch=im.size
    art_h=int(ART_H_CM/2.54*DPI); art_w=int(art_h*cw/ch)
    src=im.resize((art_w,art_h),Image.LANCZOS); a=np.asarray(src).astype(float)
    r,g,b=a[:,:,0],a[:,:,1],a[:,:,2]; lum=(0.299*r+0.587*g+0.114*b)/255.0
    # ---- máscara das figuras ----
    fg=lum<0.56
    fg=ndi.binary_fill_holes(fg)
    fg=ndi.binary_closing(fg,iterations=2)
    lbl,n=ndi.label(fg); sizes=np.bincount(lbl.ravel())
    big=set(np.where(sizes>0.0009*art_w*art_h)[0])-{0}
    mask=np.isin(lbl,list(big))
    mask=ndi.binary_fill_holes(mask)
    # janela de borda
    xw=np.clip(np.minimum(np.arange(art_w),art_w-1-np.arange(art_w))/(0.03*art_w),0,1)[None,:]
    yw=np.clip(np.minimum(np.arange(art_h),art_h-1-np.arange(art_h))/(0.03*art_h),0,1)[:,None]
    mask=mask&((xw*yw)>0.5)
    red=(r>105)&(r-g>30)&(r-b>30)&mask
    # ---- paisagem (contornos finos, atras das figuras) ----
    ls=gaussian_filter(lum,1.0)
    edge=np.hypot(sobel(ls,axis=1),sobel(ls,axis=0)); edge/= (edge.max()+1e-6)
    mdil=binary_dilation(mask,iterations=max(2,int(art_h*0.006)))
    yy=(np.arange(art_h)/art_h)[:,None]
    vband=np.clip((yy-0.06)/0.06,0,1)*np.clip((0.66-yy)/0.10,0,1)  # faixa alta (ceu/montanha)
    vband=np.repeat(vband,art_w,axis=1)
    xwb=np.clip(np.minimum(np.arange(art_w),art_w-1-np.arange(art_w))/(0.05*art_w),0,1)[None,:]
    land_win=vband*xwb*(~mdil)

    xs=np.arange(art_w)[None,:]; red=red&(xs>art_w*0.30)&(xs<art_w*0.70)

    PW=int((art_w/DPI*2.54+2*SIDE_CM)/2.54*DPI)
    PH=int((ART_H_CM+TOP_CM+BOT_CM)/2.54*DPI)
    PW_CM=PW/DPI*2.54; PH_CM=PH/DPI*2.54
    canvas=Image.new("RGB",(PW,PH),"white")
    ox=(PW-art_w)//2; oy=int(TOP_CM/2.54*DPI)
    st=stream(); si=0
    def probe(x,y,h):
        x0=max(0,int(x));x1=min(art_w,int(x+h*0.7));y0=max(0,int(y-h*0.5));y1=min(art_h,int(y+h*0.5))
        if x1<=x0 or y1<=y0: return 0.0,False,False
        inm=mask[y0:y1,x0:x1].mean()>0.4
        dk=(1.0-lum[y0:y1,x0:x1].mean())**GAMMA
        R=red[y0:y1,x0:x1].mean()>0.25
        return dk,inm,R

    # passada da paisagem: cinza clara, letra pequena, esparsa
    BG_FLOOR=0.14; BLH=int(LINE_H*0.95); si_bg=0
    def probe_bg(x,y,h):
        x0=max(0,int(x));x1=min(art_w,int(x+h*0.7));y0=max(0,int(y-h*0.5));y1=min(art_h,int(y+h*0.5))
        if x1<=x0 or y1<=y0: return 0.0
        w=land_win[y0:y1,x0:x1].mean()
        if w<0.05: return 0.0
        e=edge[y0:y1,x0:x1].mean(); d=1.0-lum[y0:y1,x0:x1].mean()
        if d<0.04: return 0.0          # ignora fundo claro chapado
        return min(1.0, e*6.5)*w        # so contorno -> traco fino
    yb=BLH
    while yb<art_h*0.72:
        x=0
        while x<art_w:
            sc=probe_bg(x,yb,LINE_H)
            if sc<BG_FLOOR: x+=LINE_H*0.7; continue
            fs=int(mm(1.3)+ (mm(2.2)-mm(1.3))*min(1.0,sc)); fs=max(int(mm(1.2)),fs)
            c=st[si_bg%len(st)]; si_bg+=1
            if c==" ": x+=fs*0.5; continue
            shade=int(206-56*min(1.0,sc)); col=(shade,shade,shade)
            ang=10*math.sin(2*math.pi*x/(art_w*0.3))
            tl,gw=tile(c,fs,False,int(round(max(-12,min(12,ang))/3)),col)
            canvas.paste(tl,(int(ox+x),int(oy+yb-fs*0.7)),tl)
            x+=gw*1.35+2
        yb+=BLH

    A=0.4*LINE_H; row=0; yb=LINE_H
    while yb<art_h:
        x=0
        while x<art_w:
            yoff=A*math.sin(2*math.pi*x/(art_w*0.5)+row*0.5); y=yb+yoff
            dk,inm,isred=probe(x,y,LINE_H)
            if not inm: x+=LINE_H*0.5; continue
            dk=max(dk,FILLMIN)
            fs=int(FS_MIN+(FS_MAX-FS_MIN)*(dk-FILLMIN)/(1-FILLMIN)); fs=max(FS_MIN,min(FS_MAX,fs))
            bold=dk>0.5
            c=st[si%len(st)]; si+=1
            if c==" ": x+=fs*0.34; continue
            ang=13*math.sin(2*math.pi*x/(art_w*0.22)+row*0.4+0.7*math.sin(2*math.pi*yb/(art_h*0.32)))
            abkt=int(round(max(-18,min(18,ang))/3))
            tl,gw=tile(c,fs,bold,abkt,TERRA if isred else INK)
            canvas.paste(tl,(int(ox+x),int(oy+y-fs*0.72)),tl)
            x+=gw*0.98+1
        yb+=LINE_H*0.9; row+=1

    d=ImageDraw.Draw(canvas)
    tx=ox; ty=int(mm(15))
    d.text((tx,ty),"MAGALENHA",font=ImageFont.truetype(FB,int(mm(32))),fill=INK)
    d.text((tx+4,ty+int(mm(34))),spaced("SÉRGIO MENDES · BRASILEIRO",1),
           font=ImageFont.truetype(FR,int(mm(6.8))),fill=GREY)
    ay=ty+int(mm(46)); s=int(mm(4.6)); gap=int(mm(8.2))
    for i in range(4): d.rectangle([tx+i*gap,ay,tx+i*gap+s,ay+s],fill=(TERRA if i==0 else INK))
    cap=spaced("EXPERIMENTO TIPOGRÁFICO — GUSTAVO JANNUZZI",1)
    ff=ImageFont.truetype(FR,int(mm(7.6))); cb=d.textbbox((0,0),cap,font=ff)
    d.text(((PW-(cb[2]-cb[0]))//2,PH-int(BOT_CM/2.54*DPI)+int(mm(26))),cap,font=ff,fill=(60,60,60))
    ins=int(mm(12)); d.rectangle([ins,ins,PW-ins,PH-ins],outline=(188,188,188),width=max(2,int(mm(0.4))))

    TAG=f"{PW_CM:.0f}x{PH_CM:.0f}_{DPI}"
    png=f"/home/claude/quadro/magalenha_v3_{TAG}.png"; pdf=f"/home/claude/quadro/magalenha_v3_{TAG}.pdf"
    canvas.save(png,dpi=(DPI,DPI))
    layout=img2pdf.get_layout_fun((img2pdf.mm_to_pt(PW_CM*10),img2pdf.mm_to_pt(PH_CM*10)))
    with open(pdf,"wb") as f: f.write(img2pdf.convert(png,layout_fun=layout))
    print(f"OK {canvas.size}px  pagina {PW_CM:.1f}x{PH_CM:.1f}cm @ {DPI}dpi  tiles {len(_tiles)}")
    print(png); print(pdf)

if __name__=="__main__": main()
