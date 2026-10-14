from geometry import CATEGORIES,ZH,REQUIRED

BASE={
'basket':('椭圆提篮带封底篮壁和跨口弧形提把','An oval basket with closed base, walls and an arched carrying handle.',
 '连续篮壁围住空腔，提把两端接在相对篮壁上','Continuous walls surround the cavity; both handle ends attach to opposite sides.'),
'bed':('圆角床带床垫、弧形床头和四个床脚','A rounded bed with mattress, curved headboard and four legs.',
 '床垫承托于床框上，床头位于后端，四脚连接床框','The mattress rests on the frame; the rear headboard and four legs join that frame.'),
'bench':('圆角长凳有加长座面和四个承重脚','A rounded bench with an elongated seat and four supporting legs.',
 '长座面水平承重，四脚分居座面下方两端','A horizontal elongated seat rests on four separate legs beneath its ends.'),
'birdhouse':('弧顶椭圆鸟屋有封底居室和正面入口','An oval birdhouse with curved roof, enclosed room and front entrance.',
 '保护屋顶接居室侧壁，正面圆入口通向真实内部空腔','The protective roof joins the walls; the circular front entrance reaches a real interior cavity.'),
'bookshelf':('曲侧开放书架有连续侧框和多层层板','An open bookshelf with curved sides and several storage shelves.',
 '水平层板连接两侧框，各层之间留有放置物品的空间','Horizontal shelves join both side frames with usable storage gaps between levels.'),
'bottle':('圆肩窄颈瓶有封底空腔和开放瓶口','A rounded shoulder bottle with narrow neck, hollow interior and open mouth.',
 '瓶身经肩部收向窄颈，瓶口、颈腔与瓶腔连续相通','The body narrows through its shoulders to the neck; mouth, neck and body cavities communicate.'),
'bowl':('无把手椭圆碗带弧腹、封底和开放碗口','A handleless oval bowl with curved belly, sealed base and open rim.',
 '弧形碗壁环绕内部空腔，底部封闭，上方碗口敞开','Curved walls surround the hollow bowl; the bottom is closed and the top remains open.'),
'bus':('圆角弧顶巴士有驾驶区、侧窗和连接轮组','A rounded bus with curved roof, driving area, side windows and attached wheels.',
 '加长车体承托驾驶舱，左右轮组接车身，右侧设置车门区','The elongated body supports the cabin; wheel groups attach on both sides and a door sits on the right.'),
'camera':('圆角相机有前向圆镜头、握柄和顶部快门','A rounded camera with forward circular lens, grip and top shutter.',
 '镜筒接机身正面，握柄位于右侧，取景结构和快门位于顶部','The lens barrel joins the front body; the grip is on the right and viewfinder and shutter are above.'),
'car':('流线汽车有弧顶驾驶舱和四个分离车轮','A streamlined car with curved cabin roof and four separate wheels.',
 '驾驶舱位于车身上方，四轮分居左右前后并接车身','The cabin rises over the body; four attached wheels occupy the left and right front and rear positions.'),
'chair':('弧背四腿椅有圆角座面和后侧靠背','A curved back chair with rounded seat and four legs.',
 '后侧靠背连接座面，四腿分离承重并各自落地','The rear backrest joins the seat; four separate supporting legs each reach the ground.'),
'guitar':('圆肩收腰吉他有连续琴身、琴颈和琴头','A rounded waist guitar with continuous body, neck and headstock.',
 '上下琴腹形成收腰轮廓，琴颈接琴身上端并延伸到琴头','Upper and lower bouts form a waisted body; its connected neck extends upward into the headstock.'),
'jar':('弧腹宽口罐有封底空腔和短宽颈沿','A rounded wide mouth jar with sealed base, cavity and short broad neck.',
 '连续罐壁围住空腔，短宽颈承接口沿并开放到内部','Continuous walls enclose the cavity; a short broad neck carries a rim opening into that interior.'),
'mug':('椭圆马克杯有开放杯口和贯通环形把手','An oval mug with open mouth and a pierced loop handle.',
 '杯壁围住封底空腔，右侧环把上下根部分别连接杯壁','Walls surround a sealed bottom cavity; upper and lower roots of the right loop handle join the cup.'),
'piano':('圆尾三角钢琴有连续键盘和三个承重脚','A rounded tail grand piano with continuous keyboard and three supporting legs.',
 '键盘连接琴体前部，黑白键分区，三个琴脚承托琴壳','The keyboard joins the front case, with black and white key areas and three supporting piano legs.'),
'pot':('弧腹双耳锅有封底空腔和开放锅口','A curved twin handle cooking pot with sealed base, cavity and open rim.',
 '锅壁围住内部空间，左右两耳连接锅壁提供握持位置','Walls surround the interior; two handles join opposite sides to provide functional grips.'),
'sofa':('圆角沙发有座垫、后靠背和左右扶手','A rounded sofa with seat cushions, rear backrest and two side arms.',
 '座垫落在座框上，靠背与双扶手接座框，四脚承重','Cushions rest on the frame; rear backrest and both arms join it, with four supporting feet.'),
'table':('椭圆四腿桌有连续桌面和分离承重脚','An oval four leg table with continuous tabletop and separate supports.',
 '四脚分别连接桌面下侧并落地，桌面保留可用平面','Four legs join the underside and reach the ground, leaving a usable horizontal tabletop.'),
'tower':('圆塔有竖向塔身、底部入口和圆弧塔冠','A round tower with upright body, lower entrance and curved crown.',
 '连续塔壁从底部升至塔冠，正面底部保留通入塔内的入口','Continuous walls rise from the base to the crown; a lower front entrance opens inside.'),
'train':('弧顶列车有驾驶区、侧窗和连接轮组','A curved roof train with driving area, side windows and attached wheel groups.',
 '加长车身承托弧顶舱体，左右轨道轮组与车身面连接','An elongated body supports the curved roof cabin; rail wheel groups attach on both sides by shared faces.'),
'vessel':('圆壳单体船有艏艉、甲板和舱内开口','A rounded monohull boat with bow, stern, deck and interior opening.',
 '弧形船壳形成艏艉，甲板沿船缘连接并保留舱内开口','The curved hull defines bow and stern; the connected perimeter deck leaves an interior opening.'),
}
TECH_ZH='生成 detailed 彩色体素模型：整数网格48×48×48，X左右、Y向上、Z前后，最低真实接地点Y=0；750—1250个唯一非负坐标体素，单一六邻域连通，附件共享面连接。保留上述开口、空腔与部件数量，不加展示底板、背景、文字或无关连接杆。以语义部件连续配色；从原始参数几何统一XYZ重采样，并实测部件连接与表面可见性。'
TECH_EN='Generate a detailed colored voxel object on a 48 cubed integer grid: X lateral, Y up, Z front/back, lowest actual contact at Y=0. Use 750 to 1250 unique nonnegative occupied cells in one six neighbor component; attach parts by shared faces. Preserve the stated openings, cavities and part counts. Omit display platforms, background, text and unrelated struts. Use continuous semantic color regions. Rebuild from original geometry at uniform XYZ density and measure attachment and exposed functional features.'

def make(p,e,parts,colors):
    c=p['category']; z1,en1,z2,en2=BASE[c]
    if c=='bench' and 'backrest' in parts: z2+='，后靠背接座面';en2+=' A rear backrest is attached to the seat.'
    if c=='bed' and 'footboard' in parts:z2+='，前端带较低床尾板';en2+=' A lower footboard marks the front end.'
    if c=='bookshelf':z2+=f"，共有{e['shelfCount']}层";en2+=f" There are {e['shelfCount']} shelves."
    if c in ['bus','train']:z2+=f"，共{e['wheelCount']}个轮子";en2+=f" It has {e['wheelCount']} wheels."
    if c=='train' and 'coupler' in parts:z2+='，两端车钩接下部车架';en2+=' End couplers attach to the underframe.'
    if c=='sofa':z2+=f"，座垫分为{e['cushionCount']}块";en2+=f" There are {e['cushionCount']} seat cushions."
    if c=='guitar':
        z2+='，正面真实音孔通向共鸣腔' if e['acoustic'] else '，正面带拾音区'
        en2+=' A real front sound hole reaches the resonance cavity.' if e['acoustic'] else ' A pickup area occupies the front surface.'
    if c=='birdhouse' and 'perch' in parts:z2+='，入口下方接短栖木';en2+=' A short perch joins below the entrance.'
    if c=='vessel' and 'cabin' in parts:z2+='，后部接有小舱体';en2+=' A small cabin attaches toward the stern.'
    z3='主体保持连续弧线轮廓，主要表面有实际厚度，功能部件按所属主体连接。'
    en3='Curved substantial surfaces carry their continuously attached functional parts.'
    if c=='piano':
        z3='连续黑白键盘位于琴体前方，键床底托至少两层且接入承重框，四个琴脚以实心截面连接底部。'
        en3='A continuous black and white keyboard sits in front of the cabinet. Its solid keybed has at least two layers joined to the frame, and four legs attach through solid sections.'
    if c in ['basket','bottle','bowl','jar','mug','pot']:z3='横截面为椭圆，侧壁连续围住空腔，口沿有厚度，封底连接全部侧壁。';en3='Oval continuous walls enclose the cavity; a thick rim and sealed base join those walls.'
    elif c in ['bed','bench','chair','table','sofa']:z3='主体边缘圆润，承重面有厚度，四脚向下分离并以连续截面连接主体。';en3='Rounded thick surfaces attach continuously to four separate downward legs.'
    elif c=='guitar':z3='琴腹上下展开，中部收腰；琴颈向上延伸，有连续截面，琴桥接在正面。';en3='Two bouts flank the waist; a continuous upward neck and front bridge attach.'
    elif c=='camera':z3='圆镜筒沿机身正面方向伸出，镜片位于端面，右侧握柄与机身连续相接。';en3='The circular lens projects forward, with end glass and an attached curved right grip.'
    # Ratios derive from measured final part bounding boxes, not intended dimensions.
    dims=e['boundsSize']; wr=dims[0]/max(1,dims[2]);hr=dims[1]/max(1,dims[0])
    z4=f'整体宽度约为前后长度的{wr:.2f}倍，高度约为宽度的{hr:.2f}倍，部件按功能位置围绕主体布置。'
    en4=f'Overall width is {wr:.2f} times depth; height is {hr:.2f} times width. Parts follow functional positions.'
    cz={'wood':'棕木色','tan':'浅棕色','dark':'深棕色','cream':'米白色','blue':'蓝色','glass':'浅蓝色','black':'近黑色','gray':'灰色','red':'红色','white':'白色'}
    ce={'wood':'brown','tan':'tan','dark':'dark brown','cream':'cream','blue':'blue','glass':'light blue','black':'near black','gray':'gray','red':'red','white':'white'}
    # Only claim colors that are actually represented in exported cells.
    pal=sorted(set(colors.values()))[:3]
    z5='主体与附属部位采用'+ '、'.join(cz[x] for x in pal)+'的连续分区。正视显示主要功能部位，侧视显示前后厚度与连接，俯视显示横向布局和轮廓。'
    en5='Continuous '+', '.join(ce[x] for x in pal)+' color regions distinguish the body and attachments. The front reveals functional parts; side and top views reveal depth, connections and layout.'
    levels=[]
    for i in range(1,6):
        zh='。'.join([z1]+([z2] if i>=2 else [])+([z3] if i>=3 else [])+([z4] if i>=4 else [])+([z5] if i>=5 else []))+'。'
        en=' '.join([en1]+([en2] if i>=2 else [])+([en3] if i>=3 else [])+([en4] if i>=4 else [])+([en5] if i>=5 else []))
        levels.append({'promptLevel':i,'promptType':['minimal','basic_structure','geometry','proportion','comprehensive'][i-1],
           'captionZh':zh,'captionEn':en,'voxelPromptZh':zh+TECH_ZH,'voxelPromptEn':en+' '+TECH_EN,
           'factGroups':list(range(1,i+1))})
    return levels
