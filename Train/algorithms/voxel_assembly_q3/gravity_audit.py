"""Independent gravity/static-equilibrium screening with an auditable LP witness.

No empirical LEGO clutch capacity is invented. Compression-only equilibrium is
reported separately from the minimum tension needed under assumed masses.
"""
import math

VERSION='gravity_contact_equilibrium_q3_v2'
ASSUMPTIONS={'studPitchMeters':.008,'brickHeightMeters':.0096,
             'massKilogramsPerOccupiedStudBrick':.001,
             'internalContactHalfWidthStuds':.25,'groundInsetStuds':.05,
             'gravityMetersPerSecondSquared':9.80665,
             'massModel':'uniform mass proportional to occupied stud-brick volume; uncalibrated',
             'contactModel':'vertical forces at four inset square contact corners per actual overlapping stud',
             'groundModel':'unanchored horizontal plane, compression only',
             'loadCase':'self weight only; no external lateral force, impact, or baseplate anchoring',
             'clutchCapacityNewtons':None}


def hull(points):
    points=sorted(set(points))
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower=[]; upper=[]
    for p in points:
        while len(lower)>1 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
        lower.append(p)
    for p in reversed(points):
        while len(upper)>1 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
        upper.append(p)
    return lower[:-1]+upper[:-1]


def witness_residual(bricks,contacts,forces,masses):
    """Rebuild force + two gravity-relevant moment sums, independent of LP rows."""
    balances=[[-m,0.,0.] for m in masses]
    for contact,force in zip(contacts,forces):
        lower,upper,x,y=contact
        for index,sign in ((upper,1),(lower,-1)):
            if index is None:continue
            b=bricks[index]; cx=b['x']+b['h']/2; cy=b['y']+b['w']/2
            balances[index][0]+=sign*force
            balances[index][1]+=sign*force*(x-cx)
            balances[index][2]+=sign*force*(y-cy)
    return max((abs(v) for row in balances for v in row),default=0)


def expected_contacts(bricks):
    import joint_cover as j
    owner={p:i for i,b in enumerate(bricks) for p in j.q.a.Placement(**{k:b[k] for k in ('h','w','x','y','z')}).cells()}
    contacts=[];groups=[]
    for p,i in sorted(owner.items()):
        above=(p[0],p[1],p[2]+1)
        if above not in owner:continue
        group=[]
        for dx in (.25,.75):
            for dy in (.25,.75):
                group.append(len(contacts));contacts.append((i,owner[above],p[0]+dx,p[1]+dy))
        groups.append(group)
    for i,b in enumerate(bricks):
        if b['z']==0:
            for x in (b['x']+.05,b['x']+b['h']-.05):
                for y in (b['y']+.05,b['y']+b['w']-.05):contacts.append((None,i,x,y))
    return contacts,groups


def verify_witness(bricks,target,report):
    """Do not trust serialized contact locations, forces, residuals or pass flags."""
    import joint_cover as j
    if not j.q.independent_audit(bricks,target)['passed']:raise ValueError('invalid witness geometry')
    if report['assumptions']!=ASSUMPTIONS:raise ValueError('unrecognized physical assumptions')
    contacts,groups=expected_contacts(bricks);witness=report['equilibriumWitness']
    if witness['contacts']!=[list(c) for c in contacts]:raise ValueError('invented physical contact')
    forces=witness['signedForcesUnitWeights']
    if len(forces)!=len(contacts) or any(not isinstance(f,(int,float)) or not math.isfinite(f) for f in forces):raise ValueError('invalid physical force')
    masses=[b['h']*b['w'] for b in bricks]
    total=sum(masses)
    center=[sum(m*(b['x']+b['h']/2) for b,m in zip(bricks,masses))/total,
            sum(m*(b['y']+b['w']/2) for b,m in zip(bricks,masses))/total,
            sum(m*(b['z']+.5) for b,m in zip(bricks,masses))/total]
    ground=[(x,y) for b in bricks if b['z']==0 for x in (b['x']+.05,b['x']+b['h']-.05)
            for y in (b['y']+.05,b['y']+b['w']-.05)]
    polygon=hull(ground)
    if len(polygon)<3:raise ValueError('missing ground support polygon')
    margin=min(((b[0]-a[0])*(center[1]-a[1])-(b[1]-a[1])*(center[0]-a[0]))/math.hypot(b[0]-a[0],b[1]-a[1])
               for a,b in zip(polygon,polygon[1:]+polygon[:1]))
    if report['centerOfMassInternalStudBrick']!=center or report['groundSupportPolygonStuds']!=[list(p) for p in polygon]:raise ValueError('invented center of mass or ground polygon')
    angle=math.degrees(math.atan2(max(0,margin)*.008,center[2]*.0096))
    if margin<=1e-7 or abs(report['groundTippingMarginMeters']-margin*.008)>1e-12 or abs(report['gravityOnlyTippingAngleDegrees']-angle)>1e-10 or abs(report['assumedMassKilograms']-total*.001)>1e-12:raise ValueError('incorrect physical metadata')
    if report['contactPointCount']!=len(contacts):raise ValueError('incorrect contact count')
    residual=witness_residual(bricks,contacts,forces,masses)
    if residual>1e-6 or abs(residual-report['maximumBalanceResidualUnitWeights'])>1e-9:raise ValueError('unbalanced physical witness')
    if any(f<-1e-7 for f in forces[4*len(groups):]):raise ValueError('unanchored ground cannot pull')
    required=report['minimumRequiredClutchNewtonsPerStud']
    if not isinstance(required,(float,int)) or not math.isfinite(required) or required<0:raise ValueError('invalid clutch requirement')
    tension=max((sum(max(0,-forces[i]) for i in group) for group in groups),default=0)*.001*9.80665
    if tension>required+1e-7:raise ValueError('underreported clutch requirement')
    compression=all(f>=-1e-7 for f in forces)
    if report['gravityEquilibriumPassed']!=compression or (compression and required>1e-7):raise ValueError('false gravity verdict')
    if report['fullPhysics'] is not False or report['staticVerified'] is not None or report['calibratedPhysicalVerified'] is not None:raise ValueError('unsupported certification')
    return True


def screen(bricks,target,seconds=8):
    """Final gravity equilibrium and ALL completed layer assembly prefixes."""
    import time
    import joint_cover as j
    deadline=time.monotonic()+seconds
    final=audit(bricks,target,max(.01,seconds*.55))
    final['layerPrefixGravityPassed']=False
    final['layerPrefixReports']=[]
    if not final['gravityEquilibriumPassed']:return final
    layers=sorted({b['z'] for b in bricks})
    for z in layers[:-1]:
        remaining=deadline-time.monotonic()
        if remaining<=0:
            final['layerPrefixTermination']='physics_time_budget';return final
        raw=[b for b in bricks if b['z']<=z]
        cells={p:c for p,c in target.items() if p[2]<=z}
        # A prefix can contain multiple valid stud components while assembly is
        # in progress. Evaluate each on the UNANCHORED floor separately, rather
        # than pretending the floor joins components or rejecting this legal prefix.
        labels=j.q.brick_component_labels(raw)
        groups={}
        for i,b in enumerate(raw):
            group=labels[(b['x'],b['y'],b['z'])];groups.setdefault(group,[]).append(b)
        for group,subset in sorted(groups.items()):
            subset_cells={p:c for p,c in cells.items() if labels[p]==group}
            part=audit(subset,subset_cells,max(.01,deadline-time.monotonic()))
            final['layerPrefixReports'].append({'throughLayer':z,'componentLabel':group,'physics':part})
            if not part['gravityEquilibriumPassed']:
                final['layerPrefixTermination']='prefix_equilibrium_not_passed';return final
    final['layerPrefixGravityPassed']=True;final['layerPrefixTermination']='all_completed_layers_passed'
    return final


def verify_screen(bricks,target,report):
    import joint_cover as j
    if report.get('equilibriumWitness'):verify_witness(bricks,target,report)
    expected=[]
    for z in sorted({b['z'] for b in bricks})[:-1]:
        raw=[b for b in bricks if b['z']<=z];labels=j.q.brick_component_labels(raw)
        groups={}
        for b in raw:groups.setdefault(labels[(b['x'],b['y'],b['z'])],[]).append(b)
        for group,subset in sorted(groups.items()):expected.append((z,group,subset,{p:c for p,c in target.items() if p[2]<=z and labels[p]==group}))
    rows=report['layerPrefixReports']
    if len(rows)>len(expected):raise ValueError('invented prefix')
    for row,(z,group,raw,cells) in zip(rows,expected):
        if (row['throughLayer'],row['componentLabel'])!=(z,group):raise ValueError('prefix order changed')
        if row['physics'].get('equilibriumWitness'):verify_witness(raw,cells,row['physics'])
        elif row['physics']['gravityEquilibriumPassed']:raise ValueError('missing prefix witness')
    actual=report['gravityEquilibriumPassed'] and len(rows)==len(expected) and all(r['physics']['gravityEquilibriumPassed'] for r in rows)
    if actual!=report['layerPrefixGravityPassed']:raise ValueError('false assembly-prefix verdict')
    return True


def audit(bricks,target,seconds=8):
    """Assumption-qualified screening, NOT a full or calibrated physical verdict."""
    import numpy as np
    import scipy
    from scipy.optimize import linprog as scipy_linprog
    from scipy.sparse import coo_matrix, hstack, vstack
    import joint_cover as j
    def linprog(*args,**kwargs):
        import warnings
        kwargs['options']={**kwargs.get('options',{}),'threads':1}
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore',message='Unrecognized options detected.*threads.*')
            return scipy_linprog(*args,**kwargs)
    q=j.q
    base={'auditorVersion':VERSION,'assumptions':ASSUMPTIONS.copy(),
          'fullPhysics':False,'staticVerified':None,'calibratedPhysicalVerified':None,
          'gravityEquilibriumPassed':False,'solver':'scipy.optimize.linprog/HiGHS',
          'scipyVersion':scipy.__version__}
    check=q.independent_audit(bricks,target)
    if not check['passed']:return dict(base,status='not_evaluated_geometry_failed')
    if not math.isfinite(seconds) or seconds<=0:raise ValueError('finite positive physics budget required')
    masses=[b['h']*b['w'] for b in bricks] # force unit = assumed unit-cell weight
    total=sum(masses)
    center=[sum(m*(b['x']+b['h']/2) for b,m in zip(bricks,masses))/total,
            sum(m*(b['y']+b['w']/2) for b,m in zip(bricks,masses))/total,
            sum(m*(b['z']+.5) for b,m in zip(bricks,masses))/total]
    ground=[(x,y) for b in bricks if b['z']==0 for x in (b['x']+.05,b['x']+b['h']-.05)
            for y in (b['y']+.05,b['y']+b['w']-.05)]
    polygon=hull(ground)
    margin=min(((b[0]-a[0])*(center[1]-a[1])-(b[1]-a[1])*(center[0]-a[0]))/math.hypot(b[0]-a[0],b[1]-a[1])
               for a,b in zip(polygon,polygon[1:]+polygon[:1])) if len(polygon)>2 else -math.inf
    base.update(centerOfMassInternalStudBrick=center,groundSupportPolygonStuds=[list(p) for p in polygon],
                groundTippingMarginMeters=margin*.008,
                gravityOnlyTippingAngleDegrees=math.degrees(math.atan2(max(0,margin)*.008,center[2]*.0096)),
                assumedMassKilograms=total*.001)
    if margin<=1e-7:return dict(base,status='global_tipping_or_zero_margin',minimumRequiredClutchNewtonsPerStud=None)
    contacts,groups=expected_contacts(bricks)
    ri=[];ci=[];values=[]
    for column,(lower,upper,x,y) in enumerate(contacts):
        for index,sign in ((upper,1),(lower,-1)):
            if index is None:continue
            b=bricks[index]
            for axis,v in enumerate((sign,sign*(x-b['x']-b['h']/2),sign*(y-b['y']-b['w']/2))):
                if v:ri.append(3*index+axis);ci.append(column);values.append(v)
    matrix=coo_matrix((values,(ri,ci)),shape=(3*len(bricks),len(contacts))).tocsc()
    rhs=np.zeros(3*len(bricks));rhs[::3]=masses
    solved=linprog(np.zeros(len(contacts)),A_eq=matrix,b_eq=rhs,bounds=(0,None),method='highs',options={'time_limit':seconds})
    base.update(compressionSolverStatus=int(solved.status),contactPointCount=len(contacts))
    if solved.success:
        forces=solved.x.tolist();residual=witness_residual(bricks,contacts,forces,masses)
        verified=residual<=1e-6 and min(forces,default=0)>=-1e-7
        return dict(base,status='gravity_equilibrium_passed' if verified else 'solver_witness_rejected',
                    gravityEquilibriumPassed=verified,minimumRequiredClutchNewtonsPerStud=0 if verified else None,
                    maximumBalanceResidualUnitWeights=residual,
                    equilibriumWitness={'contacts':[list(c) for c in contacts],'signedForcesUnitWeights':forces})
    if solved.status!=2:return dict(base,status='physics_solver_inconclusive',minimumRequiredClutchNewtonsPerStud=None)
    # Compression + bounded downward clutch (same paired action/reaction). We
    # minimize maximum per-stud tension. Ground remains strictly unanchored.
    internal=4*len(groups);negative=matrix[:,:internal]
    eq=hstack((matrix,-negative,coo_matrix((matrix.shape[0],1)))).tocsc()
    r=[];c=[];v=[]
    for k,group in enumerate(groups):
        for index in group:r.append(k);c.append(len(contacts)+index);v.append(1)
        r.append(k);c.append(len(contacts)+internal);v.append(-1)
    ub=coo_matrix((v,(r,c)),shape=(len(groups),len(contacts)+internal+1)).tocsc()
    objective=np.zeros(eq.shape[1]);objective[-1]=1
    tensile=linprog(objective,A_eq=eq,b_eq=rhs,A_ub=ub,b_ub=np.zeros(len(groups)),
                    bounds=(0,None),method='highs',options={'time_limit':seconds})
    base['tensionSolverStatus']=int(tensile.status)
    if not tensile.success:return dict(base,status='clutch_requirement_inconclusive',minimumRequiredClutchNewtonsPerStud=None)
    signed=tensile.x[:len(contacts)].copy();signed[:internal]-=tensile.x[len(contacts):len(contacts)+internal]
    residual=witness_residual(bricks,contacts,signed,masses)
    required=tensile.x[-1]*.001*9.80665
    return dict(base,status='requires_uncalibrated_clutch' if residual<=1e-6 else 'solver_witness_rejected',
                minimumRequiredClutchNewtonsPerStud=float(required) if residual<=1e-6 else None,
                maximumBalanceResidualUnitWeights=residual,
                equilibriumWitness={'contacts':[list(c) for c in contacts],'signedForcesUnitWeights':signed.tolist()})
