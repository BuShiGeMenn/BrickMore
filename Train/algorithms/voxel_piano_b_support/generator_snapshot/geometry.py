"""Analytic category geometry. Every density attempt rebuilds this original plan.
No random cell deletion, occupancy scaling, dedup bumps, or component bridges.
"""
import numpy as np

CATEGORIES = 'basket bed bench birdhouse bookshelf bottle bowl bus camera car chair guitar jar mug piano pot sofa table tower train vessel'.split()
ZH = '提篮 床 长凳 鸟屋 书架 瓶 碗 巴士 相机 汽车 椅子 吉他 罐 马克杯 三角钢琴 锅 沙发 桌 塔 火车 船'.split()
REQUIRED = {
 'basket':['bottom','wall','rim','handle'], 'bed':['frame','mattress','headboard','leg'],
 'bench':['seat','leg'], 'birdhouse':['bottom','wall','roof'],
 'bookshelf':['side','shelf'], 'bottle':['bottom','wall','neck','rim'],
 'bowl':['bottom','wall','rim'], 'bus':['body','cabin','wheel','window','door'],
 'camera':['body','lens','glass','grip','shutter','viewfinder'],
 'car':['body','cabin','wheel','window'], 'chair':['seat','backrest','leg'],
 'guitar':['body','neck','headstock','bridge'], 'jar':['bottom','wall','neck','rim'],
 'mug':['bottom','wall','rim','handle'], 'piano':['case','keyboard','key','leg'],
 'pot':['bottom','wall','rim','handle'], 'sofa':['frame','cushion','backrest','arm','leg'],
 'table':['top','leg'], 'tower':['wall','crown'],
 'train':['body','cabin','wheel','window','underframe','coupler'], 'vessel':['hull','deck'],
}
COLORS={'wood':(155,105,62),'tan':(204,166,105),'dark':(62,48,40),
 'cream':(235,222,188),'blue':(59,107,157),'glass':(124,186,211),
 'black':(31,34,40),'gray':(125,133,143),'red':(167,60,50),'white':(235,235,226)}

def plan(category, family, instance, redesign=0):
    # Independent design dimensions control actual category parts, not rigid transforms.
    ci=CATEGORIES.index(category)
    rng=np.random.default_rng(261010000+ci*100000+family*2000+instance*31+redesign*100003)
    u=rng.random(10)
    shape=(family-1)//5; mode=(family-1)%5
    p={'category':category,'family':family,'shapeProfile':shape,'structuralMode':mode,
       'designRevision':redesign,'widthFactor':float(.84+u[0]*.38),
       'depthFactor':float(.82+u[1]*.44),'heightFactor':float(.82+u[2]*.42),
       'partRatio':float(.36+u[3]*.36),'spacingRatio':float(.46+u[4]*.33),
       'curve':float(.10+shape*.028+u[5]*.12),'thickness':float(1.5+u[6]*.65),
       'attachmentRatio':float(.35+u[7]*.36),'openingRatio':float(.21+u[8]*.14),
       'supportSpread':float(.53+u[9]*.19)}
    p['changedAttributes']=['category body width/depth ratio','category body height/width ratio',
       'functional part proportion','support/opening spacing','continuous contour curvature']
    p['subtype']={
      'basket':'椭圆弧提把篮','bed':'弧形床头四脚床','bench':'弧边四脚长凳',
      'birdhouse':'弧顶椭圆鸟屋','bookshelf':'曲侧开放书架','bottle':'圆肩窄颈瓶',
      'bowl':'弧腹椭圆碗','bus':'弧顶客运巴士','camera':'圆角镜头相机',
      'car':'流线四轮汽车','chair':'弧背四腿椅','guitar':'圆肩收腰吉他',
      'jar':'弧腹宽口罐','mug':'椭圆环把杯','piano':'圆尾三角钢琴',
      'pot':'弧腹双耳锅','sofa':'圆角双扶手沙发','table':'椭圆四腿桌',
      'tower':'圆塔','train':'弧顶轨道列车','vessel':'圆壳单体船'}[category]
    if category=='train':p['railCoupler']=True
    return p

class Raster:
    def __init__(self,p,s):
        self.p=p; self.s=s
        # A common analytic world with symmetric sampling; never accumulated transforms.
        a=np.arange(-23,24)/s; b=np.arange(48)/s
        self.X,self.Y,self.Z=np.meshgrid(a,b,a,indexing='ij')
        self.labels=np.zeros(self.X.shape,dtype=np.uint8)
        self.parts=['air']; self.part_colors={}
        self.expected={}; self.evidence={}
    def put(self,mask,part,color='wood'):
        if part not in self.parts: self.parts.append(part)
        k=self.parts.index(part); self.labels[mask]=k; self.part_colors[part]=color
    def cut(self,mask): self.labels[mask]=0
    def box(self,x0,x1,y0,y1,z0,z1,part,color='wood'):
        self.put((self.X>=x0)&(self.X<=x1)&(self.Y>=y0)&(self.Y<=y1)&(self.Z>=z0)&(self.Z<=z1),part,color)
    def disk(self,w,d,y0,y1,part,color='wood',cx=0,cz=0):
        self.put(((self.X-cx)/w)**2+((self.Z-cz)/d)**2<=1, '_temporary',color) if False else None
        self.put((((self.X-cx)/w)**2+((self.Z-cz)/d)**2<=1)&(self.Y>=y0)&(self.Y<=y1),part,color)
    def rounded(self,w,h,d,y0,part,color='wood',roundness=.65,cz=0):
        # Superellipsoid sections make smooth ends, preserving substantial flat use surfaces.
        power=2.0+roundness*3
        mask=(np.abs(self.X/w)**power+np.abs((self.Z-cz)/d)**power<=1)&(self.Y>=y0)&(self.Y<=y0+h)
        self.put(mask,part,color)
    def legs(self,w,d,h,n=4):
        p=self.p; r=1.25; spread=p['supportSpread']
        for x,z in [(-w*spread,-d*spread),(w*spread,-d*spread),(-w*spread,d*spread),(w*spread,d*spread)][:n]:
            cx=x*(1+.12*(1-self.Y/max(h,1))); cz=z*(1+.12*(1-self.Y/max(h,1)))
            self.put((np.abs(self.X-cx)<=r)&(np.abs(self.Z-cz)<=r)&(self.Y<=h+.5),'leg','dark')
        self.expected['legCount']=n

def build(p,s=1):
    r=Raster(p,s); X,Y,Z=r.X,r.Y,r.Z
    c=p['category']; f=p['structuralMode']; q=p['shapeProfile']; t=p['thickness']
    w=p['widthFactor']; d=p['depthFactor']; h=p['heightFactor']; k=p['curve']; a=p['attachmentRatio']
    if c in ['basket','bottle','bowl','jar','mug','pot']:
        rw=(7 if c=='bowl' else 6)*w; rd=(6 if c=='bowl' else 5.5)*d
        H=({'basket':7.5,'bottle':15,'bowl':5,'jar':9,'mug':8,'pot':6}[c])*h
        if c=='bottle':
            shoulder=H*(.60+.025*f); nh=H*(.12+.02*q)
            rr=np.where(Y<shoulder, .92+.08*np.sin(Y/shoulder*np.pi/2),
                np.where(Y<H-nh, 1-(1-(.42+.02*f))*(Y-shoulder)/(H-nh-shoulder),.42+.02*f))
            r.expected.update(shoulderHeight=shoulder,neckStart=H-nh)
        elif c=='jar':
            shoulder=H*.76; rr=np.where(Y<shoulder,.90+.10*np.sin(Y/shoulder*np.pi/2),1-(.12+.025*f)*(Y-shoulder)/(H-shoulder))
            r.expected['neckStart']=shoulder
        elif c=='bowl':
            base=p.get('baseRadiusRatio',.57);exponent=p.get('bellyExponent',1.)
            rr=base+(1-base)*np.sin(np.clip(Y/H,0,1)*np.pi/2)**exponent
        else: rr=1-k/2+k*np.sin(np.clip(Y/H,0,1)*np.pi/2)
        rx=rw*rr; rz=rd*rr
        outer=(X/rx)**2+(Z/rz)**2<=1
        inner=(X/np.maximum(rx-t,.75))**2+(Z/np.maximum(rz-t,.75))**2<1
        r.put(outer&(Y<=t),'bottom','tan')
        r.put(outer&~inner&(Y>t)&(Y<=H),'wall','tan' if c=='basket' else 'blue')
        if c in ['jar','bottle']:
            ns=r.expected['neckStart']; r.put((r.labels>0)&(Y>=ns),'neck','blue')
        r.put((r.labels>0)&(Y>=H-1.2/s),'rim','dark')
        if c=='basket':
            rise=5+4*a+f*.4
            tor=(X/(rw+1))**2+((Y-H)/rise)**2
            ti=(X/max(2,rw-1.3))**2+((Y-H)/max(2,rise-2.3))**2
            r.put((tor<=1)&(ti>=1)&(Y>=H-1.7)&(np.abs(Z)<=1.25),'handle','wood')
        if c in ['mug','pot']:
            for side in ([1] if c=='mug' else [-1,1]):
                cx=side*(rw*.98+2.4); cy=H*.53
                tor=((X-cx)/(3.7+a))**2+((Y-cy)/(H*(.36+.015*f)))**2
                ti=((X-cx)/(1.6+a))**2+((Y-cy)/max(1,H*(.36+.015*f)-2.2))**2
                hm=(tor<=1)&(ti>=1)&(np.abs(Z)<=1.25)&(side*X>=rw*.70)
                r.put(hm,'handle','wood')
            r.expected['handleCount']=1 if c=='mug' else 2
        r.expected.update(cavityCenter=[0,t+1/s,0],openingHeight=H,bodyWidth=2*rw,bodyDepth=2*rd,bodyHeight=H)
    elif c in ['bed','bench','chair','sofa','table']:
        W=({'bed':7,'bench':12,'chair':6,'sofa':12,'table':9}[c])*w
        D=({'bed':12,'bench':4,'chair':5,'sofa':5,'table':6}[c])*d
        H=({'bed':4,'bench':6,'chair':7,'sofa':4,'table':10}[c])*h
        r.legs(W,D,H)
        surface='top' if c=='table' else ('frame' if c in ['bed','sofa'] else 'seat')
        if c=='table': r.disk(W,D,H,H+t,surface,'tan')
        else: r.rounded(W,t,D,H,surface,'wood',q*.12+.25)
        if c=='bed':
            r.rounded(W*.93,2.1,D*.92,H+t,'mattress','cream',.6)
            rear=-D+.5; crown=H+5+3*a+f*.3-2.5*(X/W)**2
            r.put((np.abs(X)<=W)&(Y>=H)&(Y<=crown)&(np.abs(Z-(rear+k*(X/W)**2))<=1.2),'headboard','wood')
            if f in [1,3]:
                r.box(-W,W,H,H+3,-0+D-1,D,'footboard','wood')
                r.expected['footboard']=True
        if c in ['chair','sofa'] or (c=='bench' and f%2):
            crown=H+(8 if c=='chair' else 6)*h+(f*.4)-1.4*(X/W)**2
            back=(np.abs(X)<=W)&(Y>=H)&(Y<=crown)&(np.abs(Z-(-D+.7+k*2*(X/W)**2))<=1.5)
            r.put(back,'backrest','wood')
            r.expected['backHeight']=float(H+(8 if c=='chair' else 6)*h)
        if c=='sofa':
            count=2+(f%2); edges=np.linspace(-W+.8,W-.8,count+1)
            for i in range(count):
                r.box(edges[i]+.3,edges[i+1]-.3,H+t,H+t+2.0,-D+1.8,D-.7,'cushion','cream')
            for side in [-1,1]:
                r.put((np.abs(X-side*(W-.6))<=1.8)&(np.abs(Z)<=D)&(Y>=H)&(Y<=H+5-.6*(Z/D)**2),'arm','wood')
            r.expected['cushionCount']=count
        r.expected.update(bodyWidth=2*W,bodyDepth=2*D,platformHeight=H,platformThickness=t)
    elif c=='bookshelf':
        W=8*w; D=3.5*d; H=18*h; n=3+f%3
        side=W-k*3*np.sin(Y/H*np.pi)
        r.put((np.abs(np.abs(X)-side)<=1.25)&(np.abs(Z)<=D)&(Y<=H),'side','wood')
        for y in np.linspace(0,H,n):
            r.put((np.abs(X)<=side+1)&(np.abs(Z)<=D)&(Y>=y)&(Y<=y+1.5),'shelf','tan')
        if f in [1,3]: r.box(-1.2,1.2,0,H,-D,-D+1.5,'spine','dark')
        r.expected.update(shelfCount=n,bodyWidth=2*W,bodyHeight=H,bodyDepth=2*D)
    elif c=='birdhouse':
        W=6*w; D=5*d; H=9*h
        outer=(X/W)**2+(Z/D)**2<=1
        inner=(X/(W-t))**2+(Z/(D-t))**2<1
        r.put(outer&(Y<=t),'bottom','wood')
        roof_y=H+(3.5+f*.4)*np.sqrt(np.maximum(0,1-(X/(W+1))**2))
        r.put(outer&~inner&(Y>t)&(Y<=roof_y),'wall','tan')
        r.put((np.abs(X)<=W+1)&(np.abs(Z)<=D+1)&(Y>=roof_y-1.7)&(Y<=roof_y+.3),'roof','red')
        entry_y=H*(.51+.025*q); er=1.7+p['openingRatio']*3
        r.cut((X**2+(Y-entry_y)**2<er**2)&(Z>0)&(Z<=D+2))
        if f%2: r.box(-1.1,1.1,entry_y-er-1.6,entry_y-er-.1,D-1.0,D+3.5,'perch','wood')
        r.expected.update(entryCenter=[0,entry_y,D],entryRadius=er,cavityCenter=[0,H*.5,0],bodyHeight=H,bodyWidth=2*W,bodyDepth=2*D)
    elif c in ['car','bus','train']:
        W=4.5*w; L=({'car':10,'bus':14,'train':14}[c])*d
        H=({'car':3.4,'bus':4.8,'train':4.8}[c])*h; y0=3
        r.rounded(W,H,L,y0,'body','red' if c=='car' else 'blue',.2)
        cabL=L*(.58 if c=='car' else .91); cabZ=-L*(.12 if c=='car' else 0)
        cabH=(2.8+f*.25)*h; cabW=W*.91
        cabTop=y0+H+cabH*(.7+.3*np.sqrt(np.maximum(0,1-(X/cabW)**2)))
        mask=(np.abs(X)<=cabW)&(np.abs(Z-cabZ)<=cabL)&(Y>=y0+H-.5)&(Y<=cabTop)
        r.put(mask,'cabin','red' if c=='car' else 'blue')
        axles=[-L*p['spacingRatio'],L*p['spacingRatio']]
        if c!='car' and f==2: axles.append(0.)
        R=2.05+.35*a
        for zi in axles:
            for side in [-1,1]:
                wm=((Y-R)**2+(Z-zi)**2<=R**2)&(side*X>=W-.6)&(side*X<=W+1.8)
                r.put(wm,'wheel','black')
        if c=='train' and p.get('railCoupler',False):
            r.box(-W*.68,W*.68,2.0,3.4,-L*.96,L*.96,'underframe','gray')
            for side in [-1,1]:
                z0,z1=sorted([side*(L-1.3),side*(L+3.5)])
                r.box(-1.25,1.25,3.1,5.3,z0,z1,'coupler','gray')
            r.expected['couplerCount']=2
        occ=r.labels>0
        # Paint only real exposed cabin cells, with sensible windshield/window anchors.
        cabin=r.labels==r.parts.index('cabin')
        xs=np.zeros_like(occ); xs[:-1]|=cabin[:-1]&~occ[1:]; xs[1:]|=cabin[1:]&~occ[:-1]
        window=xs&(Y>=y0+H+.25)&(Y<=y0+H+cabH-1/s)
        if c!='car': window &= np.cos((Z-cabZ)*np.pi/(3.2+f*.2))>.0
        front=np.zeros_like(occ); front[:,:,:-1]=cabin[:,:,:-1]&~occ[:,:,1:]
        r.put(window|(front&(Y>y0+H+.1)),'window','glass')
        if c=='bus':
            dm=xs&(X>0)&(Z>L*.3)&(Z<L*.3+2.2)&(Y<y0+H+cabH-1/s)
            r.put(dm,'door','dark')
        r.expected.update(wheelCount=len(axles)*2,bodyWidth=2*W,bodyDepth=2*L,bodyHeight=H+cabH,axlePositions=axles)
    elif c=='camera':
        W=7*w; H=8*h; D=3*d; rad=2.4+2*a; length=3+f*.5
        r.rounded(W,H,D,0,'body','black',.5)
        r.put((X**2+(Y-H*.53)**2<=rad**2)&(Z>=D-1)&(Z<=D+length),'lens','gray')
        occ=r.labels>0; lm=r.labels==r.parts.index('lens'); front=np.zeros_like(lm); front[:,:,:-1]=lm[:,:,:-1]&~occ[:,:,1:]
        r.put(front&(X**2+(Y-H*.53)**2<(.78*rad)**2),'glass','glass')
        r.put((((X-(W-1))/2.2)**2+((Z+.2)/(D+1))**2<=1)&(Y<=H*.85),'grip','wood')
        r.box(-3,-.5,H-.5,H+2.1,-1.2,1.2,'viewfinder','gray')
        r.box(W*.35,W*.35+1.8,H-.3,H+1.1,-1,1,'shutter','red')
        r.expected.update(bodyWidth=2*W,bodyDepth=2*D,bodyHeight=H,lensRadius=rad,lensLength=length)
    elif c=='guitar':
        H=17*h; W=6*w; D=2.7*d; N=14+4*a+f*.3
        yy=np.clip(Y/H,0,1)
        width=W*(.52+.40*np.exp(-((yy-.28)/.24)**2)+.23*np.exp(-((yy-.79)/.17)**2)-k*np.exp(-((yy-.58)/.13)**2))
        body=(np.abs(X)<=width)&(Y<=H)&(Y>=0)&(np.abs(Z)<=D)
        acoustic=f%2==0
        if acoustic:
            hollow=(np.abs(X)<width-1.8)&(Y>2)&(Y<H-2)&(np.abs(Z)<D-1.3)
            r.put(body&~hollow,'body','wood')
            cy=H*.61; er=1.7+p['openingRatio']*3
            r.cut((X**2+(Y-cy)**2<er**2)&(Z>=0))
            r.expected.update(soundHoleCenter=[0,cy,D],soundHoleRadius=er,cavityCenter=[0,cy,0],acoustic=True)
        else: r.put(body,'body','wood'); r.expected['acoustic']=False
        r.box(-1.5,1.5,H-1.5,H+N,-1.25,1.25,'neck','dark')
        r.rounded(2.6,4.5,1.6,H+N-1,'headstock','wood',.2)
        r.box(-2.8,2.8,H*.25,H*.25+1.7,D-1,D+.6,'bridge','dark')
        if not acoustic: r.box(-2.5,2.5,H*.60,H*.60+1.8,D-.5,D+.2,'pickup','gray')
        r.expected.update(bodyWidth=2*W,bodyDepth=2*D,bodyHeight=H,neckLength=N)
    elif c=='piano':
        W=9*w; D=10*d; H=5.5*h
        width=W*(.58+.42*np.clip((Z+D)/(2*D),0,1))
        shape=(np.abs(X)<=width)&(np.abs(Z)<=D)&((X/width)**4+(Z/D)**4<=1)
        r.put(shape&(Y>=H)&(Y<=H+2.7),'case','black')
        for x,z in [(-W*.65,D*.55),(W*.65,D*.55),(0,-D*.6)]:
            r.box(x-1.25,x+1.25,0,H+.5,z-1.25,z+1.25,'leg','wood')
        r.box(-W*.9,W*.9,H,H+2.2,D*.75,D+2.4,'keyboard','wood')
        keys=(r.labels>0)&(np.abs(X)<=W*.83)&(Z>=D*.92)&(Y>=H+1.5)
        r.put(keys,'key','white')
        r.put(keys&(np.cos(X*2.1)>.25)&(Z<D+1.3),'black_key','black')
        r.expected.update(legCount=3,bodyWidth=2*W,bodyDepth=2*D,bodyHeight=H+2.7)
    elif c=='tower':
        W=5*w; D=5*d; H=20*h
        taper=1-k*.5*Y/H; rx=W*taper; rz=D*taper
        outer=(X/rx)**2+(Z/rz)**2<=1; inner=(X/(rx-t))**2+(Z/(rz-t))**2<1
        r.put(outer&~inner&(Y<=H),'wall','gray')
        entry=(np.abs(X)<=1.5)&(Y<=4.5+f*.2)&(Z>0)
        r.cut(entry)
        crown=H+(3+f*.4)*np.sqrt(np.maximum(0,1-(X/(W*.95))**2-(Z/(D*.95))**2))
        r.put(((X/(W*1.04))**2+(Z/(D*1.04))**2<=1)&(Y>=H-.6)&(Y<=crown),'crown','red')
        r.expected.update(entryCenter=[0,2, D],bodyWidth=2*W,bodyDepth=2*D,bodyHeight=H)
    elif c=='vessel':
        W=5.5*w; L=14*d; H=4.5*h
        width=W*np.maximum(.05,1-(Z/L)**2)**(.38+k*.2)
        yb=H*((X/width)**2*.82+.18*(Z/L)**2)
        hull=(np.abs(Z)<=L)&(np.abs(X)<=width)&(Y>=yb)&(Y<=H)
        r.put(hull&((Y<=yb+t)|(np.abs(X)>=width-1.7)),'hull','wood')
        deck=(np.abs(Z)<=L*.91)&(np.abs(X)<=width)&(Y>=H-1)&(Y<=H+.7)
        cockpit=(np.abs(X)<W*.55)&(np.abs(Z)<L*(.40+.025*f))
        r.put(deck&~cockpit,'deck','tan')
        if f%2:
            r.box(-W*.55,W*.55,H-.4,H+3.8,-L*.48,-L*.24,'cabin','white')
        r.expected.update(cockpitCenter=[0,H,0],bodyWidth=2*W,bodyDepth=2*L,bodyHeight=H)
    else: raise ValueError(c)
    used=np.argwhere(r.labels>0)
    if len(used)==0: raise ValueError('empty geometry')
    labs=r.labels[tuple(used.T)]
    minimum=used.min(axis=0); maximum=used.max(axis=0); size=maximum-minimum+1
    r.expected['samplingBoundaryTouched']=bool(minimum[0]==0 or minimum[2]==0 or maximum[0]==46 or maximum[2]==46 or maximum[1]==47)
    shift=np.array([(48-size[0])//2,0,(48-size[2])//2])-minimum
    coords=used+shift
    # Analytic world point -> final integer coordinate.
    offset=shift+np.array([23,0,23])
    r.expected['worldToGrid']={'scale':s,'offset':offset.tolist()}
    r.expected['boundsSize']=size.tolist()
    return coords.astype(np.int16),labs,r.parts,r.part_colors,r.expected
