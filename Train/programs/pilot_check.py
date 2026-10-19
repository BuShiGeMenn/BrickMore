from geometry import *
from checks import validate
for c in CATEGORIES:
    p=plan(c,1,1); co,la,pa,cl,e=build(p)
    s=(1000/len(co))**(1/3)
    co,la,pa,cl,e=build(p,s)
    v=validate(p,co,la,pa,e)
    print(c,len(co),v['failureReasons'],flush=True)
