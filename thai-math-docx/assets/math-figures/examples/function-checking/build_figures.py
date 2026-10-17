from pathlib import Path
from math import sqrt,atan2,cos,sin
from html import escape
import argparse
import json
import sys
from PIL import Image, ImageDraw, ImageFont

SOURCE_DIR=Path(__file__).resolve().parent
sys.path.insert(0,str(SOURCE_DIR.parents[3]/'scripts'))
from math_figure_style import PrintStyle

parser=argparse.ArgumentParser(description="Generate print-size-aware function graphs")
parser.add_argument('--size-cm',type=float,help="Export height override; does not change the handout configuration")
parser.add_argument('--output-dir',type=Path,required=True,help="Output folder for a size variant")
args=parser.parse_args()
CONFIG=json.loads((SOURCE_DIR/'figure-config.json').read_text())
PRINT_CM=args.size_cm if args.size_cm is not None else CONFIG['height_cm']
if args.size_cm is not None and abs(PRINT_CM-CONFIG['height_cm'])>1e-9 and args.output_dir is None:
    parser.error('A size override requires --output-dir so the current handout assets stay consistent')
STYLE=PrintStyle.load(PRINT_CM)
OUT=args.output_dir
OUT.mkdir(parents=True,exist_ok=True)
S=STYLE.raster_scale
W,H=800,800
CROP=(20,20,780,780)
LABEL_SIZE=STYLE.token('label_pt')
font='/System/Library/Fonts/Supplemental/Georgia.ttf'
FIGURE_REPORTS=[]

class Canvas:
    def __init__(self,w,h):
        self.w,self.h=w,h
        self.im=Image.new('RGB',(w*S,h*S),'white')
        self.d=ImageDraw.Draw(self.im)
        self.labels=[]
        self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{PRINT_CM}cm" height="{PRINT_CM}cm" viewBox="20 20 760 760">']
    def line(self,xy,color='#222222',width=2,dashed=False):
        width=STYLE.token({2:'tick_pt',3:'axis_pt',4:'curve_pt'}[width])
        if dashed:
            x1,y1,x2,y2=xy
            length=((x2-x1)**2+(y2-y1)**2)**.5
            for k in range(0,int(length),18):
                a,b=k/length,min(k+10,length)/length
                self.d.line(tuple(round(v*S) for v in (x1+(x2-x1)*a,y1+(y2-y1)*a,x1+(x2-x1)*b,y1+(y2-y1)*b)),fill=color,width=round(width*S))
        else:self.d.line(tuple(round(v*S) for v in xy),fill=color,width=round(width*S))
        self.svg.append(f'<line x1="{xy[0]}" y1="{xy[1]}" x2="{xy[2]}" y2="{xy[3]}" stroke="{color}" stroke-width="{width}"'+(' stroke-dasharray="10 8"' if dashed else '')+'/>')
    def poly(self,pts,color):
        self.d.polygon([(round(x*S),round(y*S)) for x,y in pts],fill=color)
        self.svg.append('<polygon points="'+' '.join(f'{x},{y}' for x,y in pts)+f'" fill="{color}"/>')
    def text(self,x,y,t,size=LABEL_SIZE):
        self.labels.append((x,y,t,size))
    def arrow(self,a,b,color='#222222',width=3):
        self.line((*a,*b),color,width)
        ang=atan2(b[1]-a[1],b[0]-a[0]);r=STYLE.token('arrow_length_pt')
        self.poly([b,(b[0]-r*cos(ang)+r*.4*sin(ang),b[1]-r*sin(ang)-r*.4*cos(ang)),(b[0]-r*cos(ang)-r*.4*sin(ang),b[1]-r*sin(ang)+r*.4*cos(ang))],color)
    def save(self,name):
        boxes=[]
        for x,y,t,size in self.labels:
            f=ImageFont.truetype(font,round(size*S))
            baseline=y+size*.82
            box=self.d.textbbox((x*S,baseline*S),t,font=f,anchor='ls')
            # Clamp labels to the printable canvas without reducing their font size.
            margin=STYLE.units(0.7)*S
            dx=max(CROP[0]*S+margin-box[0],0)-max(box[2]-(CROP[2]*S-margin),0)
            dy=max(CROP[1]*S+margin-box[1],0)-max(box[3]-(CROP[3]*S-margin),0)
            x+=dx/S;baseline+=dy/S
            box=self.d.textbbox((x*S,baseline*S),t,font=f,anchor='ls')
            for prior,label in boxes:
                if min(box[2],prior[2])>max(box[0],prior[0]) and min(box[3],prior[3])>max(box[1],prior[1]):
                    raise ValueError(f'{name}: labels {label!r} and {t!r} overlap at {PRINT_CM}cm; adjust positions or reduce tick density, never shrink fonts')
            if box[2]-box[0]>(CROP[2]-CROP[0])*S-2*margin or box[3]-box[1]>(CROP[3]-CROP[1])*S-2*margin:
                raise ValueError(f'{name}: text does not fit the canvas at {PRINT_CM}cm')
            boxes.append((box,t))
            halo=STYLE.token('halo_pt')
            self.d.text((x*S,baseline*S),t,font=f,anchor='ls',fill='#111111',stroke_width=max(1,round(halo*S)),stroke_fill='white')
            self.svg.append(f'<text x="{x}" y="{baseline}" font-family="Georgia" font-size="{size}px" fill="white" stroke="white" stroke-width="{2*halo}">{escape(t)}</text>')
            self.svg.append(f'<text x="{x}" y="{baseline}" font-family="Georgia" font-size="{size}px" fill="#111111">{escape(t)}</text>')
        cropped=self.im.crop(tuple(v*S for v in CROP))
        dpi=cropped.width/(PRINT_CM/2.54)
        cropped.save(OUT/(name+'.png'),dpi=(dpi,dpi))
        (OUT/(name+'.svg')).write_text('\n'.join(self.svg+['</svg>']))
        FIGURE_REPORTS.append({'name':name,'labels':len(boxes),'label_overlaps':0,'dpi':dpi})
NAVY='#243d59'

def axes(c, negative_labels_right=False):
    def p(x,y): return 400+64*x,400-64*y
    c.arrow(p(-5.1,0),p(5.1,0),width=3)
    c.arrow(p(0,-5.1),p(0,5.1),width=3)
    c.text(*p(5.25,-.1),'x',STYLE.token('axis_label_pt'))
    c.text(*p(.15,5.55),'y',STYLE.token('axis_label_pt'))
    c.text(*p(-.9,-.12),'0')
    f=ImageFont.truetype(font,round(LABEL_SIZE*S))
    for k in [-4,-2,2,4]:
        a,b=p(k,0); c.line((a,b-6,a,b+6),width=2)
        width=c.d.textlength(str(k),font=f)/S
        c.text(a-width/2,b+10,str(k))
        a,b=p(0,k); c.line((a-6,b,a+6,b),width=2)
        c.text(a+14 if negative_labels_right and k<0 else a-width-12,b-33,str(k))
    return p

def curve(c,p,pts,arrows=True):
    for a,b in zip(pts,pts[1:]):
        c.line((*p(*a),*p(*b)),NAVY,4)
    if arrows:
        c.arrow(p(*pts[4]),p(*pts[0]),NAVY,4)
        c.arrow(p(*pts[-5]),p(*pts[-1]),NAVY,4)

def endpoint(c,p,x,y,filled=True):
    a,b=p(x,y);r=STYLE.token('point_radius_pt')
    fill=NAVY if filled else "white"
    c.d.ellipse(((a-r)*S,(b-r)*S,(a+r)*S,(b+r)*S),fill=fill,outline=NAVY,width=round(STYLE.token('point_border_pt')*S))
    c.svg.append(f'<circle cx="{a}" cy="{b}" r="{r}" fill="{fill}" stroke="{NAVY}" stroke-width="{STYLE.token('point_border_pt')}"/>')

# New order: source 2,4,5,1,6,3. Coordinates are chosen for clear teaching.
c=Canvas(W,H);p=axes(c)
curve(c,p,[(x,2*x-2) for x in [-1.45+4.9*i/400 for i in range(401)]])
c.save('graph-01')
c=Canvas(W,H);p=axes(c)
curve(c,p,[(x,x*x-3) for x in [-2.8+5.6*i/500 for i in range(501)]])
c.save('graph-02')
c=Canvas(W,H);p=axes(c,True)
curve(c,p,[(.5*y*y-3,y) for y in [-3.95+7.9*i/600 for i in range(601)]])
c.save('graph-03')
c=Canvas(W,H);p=axes(c,True)
curve(c,p,[(x,2*sin(2*x)) for x in [-5+10*i/650 for i in range(651)]])
c.save('graph-04')
c=Canvas(W,H);p=axes(c)
for sign in [-1,1]:
    curve(c,p,[(sign*sqrt(1+y*y),y) for y in [-4.8+9.6*i/600 for i in range(601)]])
c.save('graph-05')
c=Canvas(W,H);p=axes(c)
c.line((*p(-5,-2),*p(-2,-2)),NAVY,4)
c.arrow(p(-4.6,-2),p(-5,-2),NAVY,4)
c.line((*p(-2,2),*p(2,-2)),NAVY,4)
pts=[(x,1+.45*(x-3)**3+.45) for x in [2+2.95*i/400 for i in range(401)]]
curve(c,p,pts,arrows=False)
c.arrow(p(*pts[-5]),p(*pts[-1]),NAVY,4)
endpoint(c,p,-2,-2);endpoint(c,p,-2,2,False)
endpoint(c,p,2,-2);endpoint(c,p,2,1)
c.save('graph-06')
# Numbers remain outside the individual images.
PANEL=520
preview=Image.new('RGB',(2*PANEL,3*(PANEL+50)),'white')
d=ImageDraw.Draw(preview)
f=ImageFont.truetype(font,28)
for i in range(6):
    x=(i%2)*PANEL;y=(i//2)*(PANEL+50)
    d.text((x+25,y+8),str(i+1)+')',font=f,fill='#111111')
    panel=Image.open(OUT/f'graph-{i+1:02}.png').resize((PANEL,PANEL),Image.Resampling.LANCZOS)
    preview.paste(panel,(x,y+45))
preview.save(OUT/'preview.png')
print('Created six PNG/SVG graphs without grid, plus preview.')

report=STYLE.report()
report['figures']=FIGURE_REPORTS
report['style_source']='assets/math-figures/coordinate-graph-style.json'
(OUT/'print-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
