# 五组重构提示词

五条均重新构造措辞，不直接采用 dataset 原始 caption。dataset 文本仅保留为分级与元素证据，不送入模型。
car L3 与 piano L5 保持原人工选择；前两批均不计入本次推荐。

## camera_L2

A rounded camera carries a circular lens at the front. The barrel connects to its body, the grip is on the right side, and the shutter and viewfinder sit on top.

一台圆角相机，正面带圆镜头。镜筒连接机身，握柄在右侧，快门和取景器位于顶部。

Level 规则：基础轮廓，加部件位置与连接关系；不添加比例与配色。

训练证据：`Train/samples/models/camera/vx80k5p_20261010_A_camera_m0001/prompts.json` · `vx80k5p_20261010_A_camera_m0001_l2`

## car_L4

A streamlined car has a curved-roof cabin and four separate wheels. The cabin stands over the main body, while the wheels attach in front and rear pairs on its two sides. Rounded solid surfaces carry the connected parts. Across the whole car, width is about 0.68 of front-to-back length and height is about 0.69 of width.

一辆流线汽车，有弧顶驾驶舱和四个独立车轮。驾驶舱位于主体车身上方，前后轮对分居两侧并连接车身。圆润的实体表面承载相接的部件。整车宽度约为前后长度的 0.68 倍，高度约为宽度的 0.69 倍。

Level 规则：基础结构、连续曲面与部件连接，加 dataset 中的实际比例；不添加配色。

训练证据：`Train/samples/models/car/vx80k5p_20261010_A_car_m0001/prompts.json` · `vx80k5p_20261010_A_car_m0001_l4`

## car_L5

A streamlined car has a curved-roof cabin and four separate wheels. The cabin stands over the main body, while the wheels attach in front and rear pairs on its two sides. Rounded solid surfaces carry the connected parts. Across the whole car, width is about 0.68 of front-to-back length and height is about 0.69 of width. The body and cabin are red, the windows are light blue, and the four wheels are near black, with continuous color regions. A front view reveals the functional parts; side and overhead views show their depth, connections and arrangement.

一辆流线汽车，有弧顶驾驶舱和四个独立车轮。驾驶舱位于主体车身上方，前后轮对分居两侧并连接车身。圆润的实体表面承载相接的部件。整车宽度约为前后长度的 0.68 倍，高度约为宽度的 0.69 倍。车身和驾驶舱为红色，车窗为浅蓝色，四轮为近黑色，各部位采用连续色区。正视显示功能部件，侧视和俯视显示其厚度、连接及布局。

Level 规则：包含 L1–L4 信息，再加训练中真实存在的部件配色与观察视角。

训练证据：`Train/samples/models/car/vx80k5p_20261010_A_car_m0001/prompts.json` · `vx80k5p_20261010_A_car_m0001_l5`

## guitar_L1

A guitar with a rounded, waisted body, a narrow neck and a distinct headstock.

一把吉他，琴身圆润收腰，带细长琴颈和清晰的琴头。

Level 规则：基础轮廓与主要部件；不添加比例、配色或逐部件连接细则。

训练证据：`Train/samples/models/guitar/vx80k5p_20261010_A_guitar_m0001/prompts.json` · `vx80k5p_20261010_A_guitar_m0001_l1`

## vessel_L1

A boat with a rounded hull, bow, stern, deck and an open interior.

一艘船，圆润船壳带艏、艉、甲板和内部开口。

Level 规则：基础轮廓与主要部件；不添加比例、配色或逐部件连接细则。

训练证据：`Train/samples/models/vessel/vx80k5p_20261010_A_vessel_m0001/prompts.json` · `vx80k5p_20261010_A_vessel_m0001_l1`

## L1 修订候选（v2）

保留训练中的类别短语，后续措辞重新构造；原 v1 结果不推荐。

### guitar_L1

A rounded waist guitar whose curved body leads into a slender neck topped by a headstock.

一把圆润收腰的吉他，弧形琴身向上接入细长琴颈，顶端为琴头。

### vessel_L1

A rounded monohull boat, its bow and stern framing a deck with an open interior.

一艘圆壳单体船，艏艉之间是带内部开口的甲板。

