# 第二批提示词：dataset 同级原文

第一批五个候选均已由用户判为不合格，另行保留，不计入本批。
camera L2、car L5、guitar L1、vessel L1 直接采用 dataset 对应 Level 的实际 caption。
car L4 使用原交接文件同级备选原文，未改写。car L3 与 piano L5 保留。

Level 规则：L1=基础外形；L2=增加部件与连接；L3=增加几何；L4=增加实测比例；L5=增加训练配色和观察视角。
本批使用确定性解码先验证训练分布内的文本；后续有需要再按相同提示词换种子。

## camera_L2

A rounded camera with forward circular lens, grip and top shutter. The lens barrel joins the front body; the grip is on the right and viewfinder and shutter are above.

圆角相机有前向圆镜头、握柄和顶部快门。镜筒接机身正面，握柄位于右侧，取景结构和快门位于顶部。

来源：`Train/samples/models/camera/vx80k5p_20261010_A_camera_m0001/prompts.json` · `vx80k5p_20261010_A_camera_m0001_l2`

## car_L4

A sedan stretching twelve studs: long flat hoodline, angled windshield feeding the cabin, sloped rear glass to a short trunk, four dark wheels tucked under.



## car_L5

A streamlined car with curved cabin roof and four separate wheels. The cabin rises over the body; four attached wheels occupy the left and right front and rear positions. Curved substantial surfaces carry their continuously attached functional parts. Overall width is 0.68 times depth; height is 0.69 times width. Parts follow functional positions. Continuous near black, light blue, red color regions distinguish the body and attachments. The front reveals functional parts; side and top views reveal depth, connections and layout.

流线汽车有弧顶驾驶舱和四个分离车轮。驾驶舱位于车身上方，四轮分居左右前后并接车身。主体保持连续弧线轮廓，主要表面有实际厚度，功能部件按所属主体连接。。整体宽度约为前后长度的0.68倍，高度约为宽度的0.69倍，部件按功能位置围绕主体布置。。主体与附属部位采用近黑色、浅蓝色、红色的连续分区。正视显示主要功能部位，侧视显示前后厚度与连接，俯视显示横向布局和轮廓。。

来源：`Train/samples/models/car/vx80k5p_20261010_A_car_m0001/prompts.json` · `vx80k5p_20261010_A_car_m0001_l5`

## guitar_L1

A rounded waist guitar with continuous body, neck and headstock.

圆肩收腰吉他有连续琴身、琴颈和琴头。

来源：`Train/samples/models/guitar/vx80k5p_20261010_A_guitar_m0001/prompts.json` · `vx80k5p_20261010_A_guitar_m0001_l1`

## vessel_L1

A rounded monohull boat with bow, stern, deck and interior opening.

圆壳单体船有艏艉、甲板和舱内开口。

来源：`Train/samples/models/vessel/vx80k5p_20261010_A_vessel_m0001/prompts.json` · `vx80k5p_20261010_A_vessel_m0001_l1`
