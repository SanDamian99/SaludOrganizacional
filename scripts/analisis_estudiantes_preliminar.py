# -*- coding: utf-8 -*-
"""Análisis preliminar reproducible de los dos formularios de estudiantes (Observatorio 360).
Uso: python scripts/analisis_estudiantes_preliminar.py <dir_salida> [<dir_con_los_csv>]
Es la implementación de referencia que el motor de puntuación de la plataforma debe reproducir
(ver docs/instrumentos/fixtures/resultados_preliminares_estudiantes.json).
Salida: JSON + texto. Nunca imprime nombres; el ID es un hash del nombre normalizado."""
import pandas as pd, numpy as np, hashlib, re, unicodedata, json, sys, itertools
from scipy import stats
pd.set_option('display.width',250); pd.set_option('display.max_columns',50); pd.set_option('display.max_rows',300)
ROOT=sys.argv[2] if len(sys.argv)>2 else "/Users/joseamorocho/Documents/app_360_observatorio/SaludOrganizacional/"
A=ROOT+'_¡Cuéntanos sobre tu bienestar emocional! (respuestas) - Respuestas de formulario 1.csv'
B=ROOT+'¡Cuéntanos sobre tus emociones! (respuestas) - Respuestas de formulario 1.csv'
OUT=sys.argv[1] if len(sys.argv)>1 else '.'
R={}  # resultados

def norm(s):
    s=unicodedata.normalize('NFKD',str(s)).encode('ascii','ignore').decode().lower()
    return ' '.join(re.sub(r'[^a-z ]',' ',s).split())

def load(path, form):
    df=pd.read_csv(path); df.columns=[c.replace('\xa0',' ').strip() for c in df.columns]
    df['form']=form
    df=df.rename(columns={'Marca temporal':'ts','Mi nombre completo es:':'nombre','Tengo:':'edad_txt','Mi sexo es:':'Sexo','Mi colegio es:':'colegio_raw'})
    g=[c for c in df.columns if c.startswith('Estoy en grado')][0]; df=df.rename(columns={g:'Grado'})
    df['consent']=df.iloc[:,1].str.startswith('Sí')
    df['ts']=pd.to_datetime(df['ts'],dayfirst=True)
    df['Edad']=pd.to_numeric(df['edad_txt'].str.extract(r'(\d+)')[0])
    # bloques por posición
    cols=list(df.columns)
    def block(prefix): return [c for c in cols if c.startswith(prefix)]
    sdq=block('SDQ ['); ari=block('ARI ['); rc=block('RCADS ['); erq=block('ERQ-CA ['); ms=block('MSPSS ['); td=block('Toma de decisiones')
    p0=cols.index('Siento que soy parte de mi colegio'); pssm=cols[p0:p0+18]
    assert len(sdq)==25 and len(ari)==7 and len(erq)==10 and len(ms)==12 and len(pssm)==18 and len(td)==10, (len(sdq),len(ari),len(erq),len(ms),len(pssm),len(td))
    assert len(rc) in (0,25)
    ren={}
    for i,c in enumerate(sdq): ren[c]=f'SDQ{i+1}'
    for i,c in enumerate(ari): ren[c]=f'ARI{i+1}'
    for i,c in enumerate(rc): ren[c]=f'RCADS{i+1}'
    for i,c in enumerate(erq): ren[c]=f'ERQ{i+1}'
    for i,c in enumerate(ms): ren[c]=f'MSPSS{i+1}'
    for i,c in enumerate(pssm): ren[c]=f'PSSM{i+1}'
    for i,c in enumerate(td): ren[c]=f'TD{i+1}'
    df=df.rename(columns=ren)
    return df, ren

dfA,renA=load(A,'secundaria'); dfB,renB=load(B,'primaria')
R['items_map']={'A':renA,'B':renB}
df=pd.concat([dfA,dfB],ignore_index=True)
R['recibido']={'filas_A':len(dfA),'filas_B':len(dfB),'sin_consentimiento_A':int((~dfA.consent).sum()),'sin_consentimiento_B':int((~dfB.consent).sum())}
df=df[df.consent].copy()

# ---- colegios: normalización a código institución + sede
def school_code(s):
    s=norm(s)
    if 'laura' in s: return 'LauV','Laura Vicuña',''
    if 'joaquin' in s: return 'JJC','José Joaquín Casas',''
    if 'balsa' in s: return 'LaBalsa','La Balsa',''
    if 'josemaria' in s or 'escriva' in s: return 'SJMEB','San Josemaría Escrivá de Balaguer',('Samaria' if 'samaria' in s else 'Principal')
    if 'cerca' in s: return 'CdP','Cerca de Piedra',''
    if 'diosa' in s: return 'DiosCh','Diosa Chía',('Preescolar' if 'preescolar' in s else 'Principal')
    if 'bojaca' in s: return 'Bojacá','Bojacá',('Mercedes de Calahorra' if 'calahorra' in s else 'Principal')
    if 'fagua' in s: return 'Fagua','Fagua',('Tiquiza' if 'tiquiza' in s else 'Polideportivo')
    if 'fonquet' in s: return 'Fonquetá','Fonquetá',''
    return 'OTRO',s,''
sc=df['colegio_raw'].map(school_code)
df['Colegio']=[x[0] for x in sc]; df['Colegio_nombre']=[x[1] for x in sc]; df['Sede']=[x[2] for x in sc]
R['colegios_raw_a_codigo']=df.groupby(['colegio_raw','Colegio']).size().reset_index().values.tolist()

# ---- exclusiones
df['nombre_n']=df['nombre'].map(norm); df['ID']=df['nombre_n'].map(lambda s: 'E'+hashlib.sha1(s.encode()).hexdigest()[:8])
df['fecha']=df.ts.dt.date
# (b) misma persona reportada en colegios distintos el mismo día = fila de prueba
g=df.groupby(['nombre_n','fecha'])['Colegio'].nunique()
test_keys=set(g[g>1].index)
df['excl_prueba']=[(n,f) in test_keys for n,f in zip(df.nombre_n,df.fecha)]
# (c) colegio con una sola respuesta en todo el dataset (ráfaga del 4-sep)
vc=df['Colegio'].value_counts(); df['excl_colegio_unico']=df['Colegio'].map(vc)<=1
# ráfaga: mismas 5 filas
burst=df[(df.fecha==pd.Timestamp('2026-09-04').date())&(df.ts.dt.hour==10)&(df.Colegio.isin(['Bojacá','Fagua','Fonquetá']))]
df['excl_rafaga']=df.index.isin(burst.index)
R['exclusiones']={'prueba_nombre_multicolegio':int(df.excl_prueba.sum()),'colegio_unico':int(df.excl_colegio_unico.sum()),'rafaga_4sep':int(df.excl_rafaga.sum()),
                  'union':int((df.excl_prueba|df.excl_colegio_unico|df.excl_rafaga).sum())}
df=df[~(df.excl_prueba|df.excl_colegio_unico|df.excl_rafaga)].copy()
# (d) duplicados por nombre: conservar primer envío
df=df.sort_values('ts'); dup_n=int(df.duplicated('nombre_n',keep='first').sum())
df=df.drop_duplicates('nombre_n',keep='first').copy()
R['exclusiones']['duplicados_nombre_eliminados']=dup_n
R['n_final']={'total':len(df),'secundaria':int((df.form=='secundaria').sum()),'primaria':int((df.form=='primaria').sum())}

# ---- recodificación
M3={'no es cierto':0,'algo cierto':1,'muy cierto':2}
M4={'nunca':0,'algunas veces':1,'con frecuencia':2,'siempre':3}
M5_ERQ={'nada parecido a mi':1,'poco parecido a mi':2,'se parece a mi':3,'bastante parecido a mi':4,'exactamente igual a mi':5}
M5_F={'nunca':1,'casi nunca':2,'algunas veces':3,'casi siempre':4,'siempre':5}
M5_TD={'nunca':1,'casi nunca':2,'a veces':3,'casi siempre':4,'siempre':5}
def rec(cols,m):
    for c in cols:
        if df[c].dtype==object:
            v=df[c].map(lambda x: m.get(norm(x)) if pd.notna(x) else np.nan)
            bad=v.isna()&df[c].notna(); assert bad.sum()==0, (c, df.loc[bad,c].unique())
            df[c]=v
        else: df[c]=pd.to_numeric(df[c],errors='coerce')
SDQ=[f'SDQ{i}' for i in range(1,26)]; ARI=[f'ARI{i}' for i in range(1,8)]; RC=[f'RCADS{i}' for i in range(1,26)]
ERQ=[f'ERQ{i}' for i in range(1,11)]; MS=[f'MSPSS{i}' for i in range(1,13)]; PS=[f'PSSM{i}' for i in range(1,19)]; TD=[f'TD{i}' for i in range(1,11)]
rec(SDQ,M3); rec(ARI,M3); rec(RC,M4); rec(ERQ,M5_ERQ); rec(MS,M5_F); rec(PS,{}); rec(TD,M5_TD)
for c in RC: df[c]=pd.to_numeric(df[c],errors='coerce')
# ERQ inválido: 'Nada parecido a mí' en los 10 ítems (reevaluación y supresión son estrategias opuestas). Artefacto de aplicación en La Balsa secundaria (137/137).
erq_all1=(df[ERQ]==1).all(axis=1)
R['erq_invalidado']={'n_total':int(erq_all1.sum()),'por_colegio_form':df[erq_all1].groupby(['form','Colegio']).size().reset_index().values.tolist()}
df.loc[erq_all1,ERQ]=np.nan
# rangos
for cols,lo,hi in [(SDQ,0,2),(ARI,0,2),(RC,0,3),(ERQ,1,5),(MS,1,5),(PS,1,5),(TD,1,5)]:
    v=df[cols].stack(); assert v.min()>=lo and v.max()<=hi, (cols[0],v.min(),v.max())

# ---- puntuación
def s(cols, rev=(), maxv=None, mean=False, allow_missing=0):
    X=df[cols].copy()
    for r in rev: X[r]=maxv-X[r]
    miss=X.isna().sum(axis=1); out=X.mean(axis=1) if mean else X.sum(axis=1)*len(cols)/(len(cols)-miss)  # prorrateo
    out[miss>allow_missing]=np.nan
    return out
sdq_rev=['SDQ7','SDQ11','SDQ14','SDQ21','SDQ25']
SUB={'SDQ_Emo':[3,8,13,16,24],'SDQ_Con':[5,7,12,18,22],'SDQ_Hip':[2,10,15,21,25],'SDQ_Pares':[6,11,14,19,23],'SDQ_Pro':[1,4,9,17,20]}
for k,it in SUB.items():
    cols=[f'SDQ{i}' for i in it]; df[k]=s(cols,[c for c in cols if c in sdq_rev],2,allow_missing=1).round(0)
df['SDQ_Total']=df[['SDQ_Emo','SDQ_Con','SDQ_Hip','SDQ_Pares']].sum(axis=1,min_count=4)
df['SDQ_Int']=df.SDQ_Emo+df.SDQ_Pares; df['SDQ_Ext']=df.SDQ_Con+df.SDQ_Hip
df['ARI_Total']=s(ARI[:6],allow_missing=0); df['ARI_Deterioro']=df['ARI7']
DEP=[1,4,8,10,13,15,16,18,19,21]; ANX=[i for i in range(1,26) if i not in DEP]
df['RCADS_Dep']=s([f'RCADS{i}' for i in DEP],allow_missing=1); df['RCADS_Anx']=s([f'RCADS{i}' for i in ANX],allow_missing=1); df['RCADS_Total']=s(RC,allow_missing=2)
df['ERQ_Reap']=s([f'ERQ{i}' for i in (1,3,5,7,8,10)],mean=True); df['ERQ_Sup']=s([f'ERQ{i}' for i in (2,4,6,9)],mean=True)
df['MSPSS_Total']=s(MS,mean=True,allow_missing=1); df['MSPSS_Otro']=s([f'MSPSS{i}' for i in (1,2,5,10)],mean=True); df['MSPSS_Fam']=s([f'MSPSS{i}' for i in (3,4,8,11)],mean=True); df['MSPSS_Amigos']=s([f'MSPSS{i}' for i in (6,7,9,12)],mean=True)
ps_rev=[f'PSSM{i}' for i in (3,6,9,12,16)]
df['PSSM_Total']=s(PS,ps_rev,6,mean=True,allow_missing=1); df['PSSM_Pos13']=s([c for c in PS if c not in ps_rev],mean=True,allow_missing=1)
df['TD_Total']=s(TD,mean=True,allow_missing=1)
df['RCADS18_muerte']=df['RCADS18']
SCALES=['SDQ_Emo','SDQ_Con','SDQ_Hip','SDQ_Pares','SDQ_Pro','SDQ_Total','SDQ_Int','SDQ_Ext','ARI_Total','RCADS_Dep','RCADS_Anx','RCADS_Total','ERQ_Reap','ERQ_Sup','MSPSS_Total','MSPSS_Otro','MSPSS_Fam','MSPSS_Amigos','PSSM_Total','PSSM_Pos13','TD_Total']

# ---- alfa
def alpha(X):
    X=X.dropna(); k=X.shape[1]
    if len(X)<20: return np.nan
    return float(k/(k-1)*(1-X.var(ddof=1).sum()/X.sum(axis=1).var(ddof=1)))
def alpha_ci(X, B=500, seed=1):
    X=X.dropna(); rng=np.random.default_rng(seed); a=alpha(X)
    bs=[alpha(X.iloc[rng.integers(0,len(X),len(X))]) for _ in range(B)]
    return a, float(np.nanpercentile(bs,2.5)), float(np.nanpercentile(bs,97.5))
ITEMSETS={'SDQ_Emo':([f'SDQ{i}' for i in SUB['SDQ_Emo']],[]),'SDQ_Con':([f'SDQ{i}' for i in SUB['SDQ_Con']],['SDQ7']),'SDQ_Hip':([f'SDQ{i}' for i in SUB['SDQ_Hip']],['SDQ21','SDQ25']),
 'SDQ_Pares':([f'SDQ{i}' for i in SUB['SDQ_Pares']],['SDQ11','SDQ14']),'SDQ_Pro':([f'SDQ{i}' for i in SUB['SDQ_Pro']],[]),'SDQ_Total':([f'SDQ{i}' for i in range(1,26) if i not in SUB['SDQ_Pro']],sdq_rev),
 'ARI_Total':(ARI[:6],[]),'RCADS_Dep':([f'RCADS{i}' for i in DEP],[]),'RCADS_Anx':([f'RCADS{i}' for i in ANX],[]),'RCADS_Total':(RC,[]),
 'ERQ_Reap':([f'ERQ{i}' for i in (1,3,5,7,8,10)],[]),'ERQ_Sup':([f'ERQ{i}' for i in (2,4,6,9)],[]),'MSPSS_Total':(MS,[]),'MSPSS_Otro':([f'MSPSS{i}' for i in (1,2,5,10)],[]),'MSPSS_Fam':([f'MSPSS{i}' for i in (3,4,8,11)],[]),'MSPSS_Amigos':([f'MSPSS{i}' for i in (6,7,9,12)],[]),
 'PSSM_Total':(PS,ps_rev),'PSSM_Pos13':([c for c in PS if c not in ps_rev],[]),'TD_Total':(TD,[])}
def rev_frame(cols,rev):
    X=df[cols].copy()
    for r in rev: X[r]=(2 if r.startswith('SDQ') else 6)-X[r]
    return X
R['alfa']={}
for form in ['secundaria','primaria']:
    sub=df[df.form==form]; R['alfa'][form]={}
    for k,(cols,rev) in ITEMSETS.items():
        X=rev_frame(cols,rev).loc[sub.index]
        if X.dropna().shape[0]<20: continue
        a,lo,hi=alpha_ci(X,B=300); R['alfa'][form][k]={'alpha':round(a,3),'ci':[round(lo,3),round(hi,3)],'n':int(X.dropna().shape[0])}

# ---- descriptivos
def desc(sub):
    out={}
    for k in SCALES:
        v=sub[k].dropna()
        if len(v)==0: continue
        out[k]={'n':int(len(v)),'M':round(v.mean(),2),'DE':round(v.std(ddof=1),2),'Mdn':round(v.median(),1),'min':float(v.min()),'max':float(v.max()),'pct_faltante':round(100*(1-len(v)/len(sub)),1),
                'P25':round(v.quantile(.25),1),'P75':round(v.quantile(.75),1),'P90':round(v.quantile(.9),1),'P95':round(v.quantile(.95),1)}
    return out
R['descriptivos']={f:desc(df[df.form==f]) for f in ['secundaria','primaria']}
R['muestra']={}
for f in ['secundaria','primaria']:
    sub=df[df.form==f]
    R['muestra'][f]={'n':len(sub),'sexo':sub.Sexo.value_counts().to_dict(),'edad':sub.Edad.value_counts().sort_index().to_dict(),'grado':sub.Grado.value_counts().to_dict(),
                     'colegio':sub.Colegio.value_counts().to_dict(),'edad_M':round(sub.Edad.mean(),2),'edad_DE':round(sub.Edad.std(),2),
                     'fechas':[str(sub.ts.min().date()),str(sub.ts.max().date())]}

# ---- bandas SDQ autoinforme (4 bandas, sdqinfo tabla 3)
BANDS_SELF={'SDQ_Total':[(0,14),(15,17),(18,19),(20,40)],'SDQ_Emo':[(0,4),(5,5),(6,6),(7,10)],'SDQ_Con':[(0,3),(4,4),(5,5),(6,10)],'SDQ_Hip':[(0,5),(6,6),(7,7),(8,10)],'SDQ_Pares':[(0,2),(3,3),(4,4),(5,10)],'SDQ_Pro':[(7,10),(6,6),(5,5),(0,4)]}
BANDS_PAR={'SDQ_Total':[(0,13),(14,16),(17,19),(20,40)],'SDQ_Emo':[(0,3),(4,4),(5,6),(7,10)],'SDQ_Con':[(0,2),(3,3),(4,5),(6,10)],'SDQ_Hip':[(0,5),(6,7),(8,8),(9,10)],'SDQ_Pares':[(0,2),(3,3),(4,4),(5,10)],'SDQ_Pro':[(8,10),(7,7),(6,6),(0,5)]}
BLAB=['Cercano al promedio','Ligeramente elevado','Alto','Muy alto']
def band(v,bands):
    for i,(lo,hi) in enumerate(bands):
        if lo<=v<=hi: return i
    return np.nan
def band_table(sub,bands):
    out={}
    for k,b in bands.items():
        v=sub[k].dropna(); bi=v.map(lambda x: band(x,b))
        cnt=bi.value_counts().reindex(range(4),fill_value=0)
        out[k]={'n':int(len(v)),'pct':[round(100*c/len(v),1) for c in cnt],'n_bandas':[int(c) for c in cnt]}
    return out
for f in ['secundaria','primaria']:
    R.setdefault('bandas_sdq',{})[f]=band_table(df[df.form==f],BANDS_SELF)
df['SDQ_banda']=df['SDQ_Total'].map(lambda x: band(x,BANDS_SELF['SDQ_Total']) if pd.notna(x) else np.nan)
# ARI cortes
for f in ['secundaria','primaria']:
    v=df.loc[df.form==f,'ARI_Total'].dropna(); d7=df.loc[df.form==f,'ARI_Deterioro'].dropna()
    R.setdefault('ari',{})[f]={'n':int(len(v)),'pct_gt2':round(100*(v>2).mean(),1),'pct_ge4':round(100*(v>=4).mean(),1),'pct_deterioro_algo_o_muy':round(100*(d7>=1).mean(),1),'pct_deterioro_muy':round(100*(d7==2).mean(),1)}
# RCADS: brutas + percentiles por sexo ; item 18
sub=df[df.form=='secundaria']
R['rcads']={'percentiles_por_sexo':{},'item18_muerte':{}}
for sx,g in sub.groupby('Sexo'):
    R['rcads']['percentiles_por_sexo'][sx]={k:{p:round(float(g[k].quantile(p/100)),1) for p in (50,75,85,90,95)} for k in ['RCADS_Dep','RCADS_Anx','RCADS_Total']}
v=sub['RCADS18'].dropna(); R['rcads']['item18_muerte']={'n':int(len(v)),'pct_nunca':round(100*(v==0).mean(),1),'pct_algunas':round(100*(v==1).mean(),1),'pct_confrec':round(100*(v==2).mean(),1),'pct_siempre':round(100*(v==3).mean(),1),'pct_ge2':round(100*(v>=2).mean(),1)}
R['rcads']['item18_por_sexo_ge2']={sx:round(100*(g['RCADS18']>=2).mean(),1) for sx,g in sub.groupby('Sexo')}
# terciles (relativos) para ERQ, MSPSS, PSSM, TD
R['terciles']={}
for f in ['secundaria','primaria']:
    g=df[df.form==f]; R['terciles'][f]={k:[round(float(g[k].quantile(q)),2) for q in (1/3,2/3)] for k in ['ERQ_Reap','ERQ_Sup','MSPSS_Total','MSPSS_Fam','MSPSS_Amigos','MSPSS_Otro','PSSM_Total','TD_Total']}
# MSPSS distribución "bajo" definido como media <3 (punto medio de la escala; descriptivo, no clínico)
for f in ['secundaria','primaria']:
    g=df[df.form==f]; R['terciles'][f]['MSPSS_pct_media_lt3']={k:round(100*(g[k]<3).mean(),1) for k in ['MSPSS_Total','MSPSS_Fam','MSPSS_Amigos','MSPSS_Otro']}
    R['terciles'][f]['PSSM_pct_media_lt3']=round(100*(g['PSSM_Total']<3).mean(),1)

# ---- comparaciones por grupo
def cohen_d(a,b):
    a,b=a.dropna(),b.dropna(); sp=np.sqrt(((len(a)-1)*a.var(ddof=1)+(len(b)-1)*b.var(ddof=1))/(len(a)+len(b)-2)); return float((a.mean()-b.mean())/sp)
R['sexo']={}
MAIN=['SDQ_Emo','SDQ_Con','SDQ_Hip','SDQ_Pares','SDQ_Pro','SDQ_Total','ARI_Total','RCADS_Dep','RCADS_Anx','ERQ_Reap','ERQ_Sup','MSPSS_Total','MSPSS_Fam','MSPSS_Amigos','MSPSS_Otro','PSSM_Total','TD_Total']
for f in ['secundaria','primaria']:
    g=df[df.form==f]; R['sexo'][f]={}
    for k in MAIN:
        a=g.loc[g.Sexo=='Mujer',k].dropna(); b=g.loc[g.Sexo=='Hombre',k].dropna()
        if len(a)<10 or len(b)<10: continue
        u=stats.mannwhitneyu(a,b); R['sexo'][f][k]={'M_mujer':round(a.mean(),2),'M_hombre':round(b.mean(),2),'d_mujer_menos_hombre':round(cohen_d(a,b),2),'p':float(u.pvalue),'n':[len(a),len(b)]}
    # bandas SDQ por sexo
    R['sexo'][f]['SDQ_pct_alto_o_muyalto']={sx:round(100*(gg['SDQ_banda']>=2).mean(),1) for sx,gg in g.groupby('Sexo')}
    if f=='secundaria':
        R['sexo'][f]['ARI_pct_gt2']={sx:round(100*(gg['ARI_Total']>2).mean(),1) for sx,gg in g.groupby('Sexo')}
# edad (Spearman) y grado (Kruskal) en secundaria
sub=df[df.form=='secundaria']; R['edad']={}; R['grado']={}
GORD=['Sexto','Séptimo','Octavo','Noveno','Décimo']
for k in MAIN:
    v=sub[[k,'Edad']].dropna(); r=stats.spearmanr(v[k],v.Edad); R['edad'][k]={'rho':round(r.statistic,3),'p':float(r.pvalue)}
    groups=[sub.loc[sub.Grado==gr,k].dropna() for gr in GORD]; kw=stats.kruskal(*groups)
    R['grado'][k]={'M_por_grado':{gr:round(x.mean(),2) for gr,x in zip(GORD,groups)},'p_kruskal':float(kw.pvalue)}
R['grado']['SDQ_pct_alto_o_muyalto']={gr:round(100*(sub.loc[sub.Grado==gr,'SDQ_banda']>=2).mean(),1) for gr in GORD}
R['grado']['n']={gr:int((sub.Grado==gr).sum()) for gr in GORD}
# primaria por grado
subB=df[df.form=='primaria']
R['grado_primaria']={k:{gr:round(subB.loc[subB.Grado==gr,k].mean(),2) for gr in ['Cuarto','Quinto']} for k in MAIN if k not in ('RCADS_Dep','RCADS_Anx')}
# colegio (N>=10), secundaria
MIN_N=10; R['colegio']={}
for f in ['secundaria','primaria']:
    g=df[df.form==f]; vc=g.Colegio.value_counts(); keep=vc[vc>=MIN_N].index; R['colegio'][f]={'n':vc.to_dict(),'enmascarados':vc[vc<MIN_N].index.tolist(),'por_escala':{}}
    for k in MAIN:
        groups={c:g.loc[g.Colegio==c,k].dropna() for c in keep}
        if len(groups)<2: continue
        kw=stats.kruskal(*groups.values()); R['colegio'][f]['por_escala'][k]={'M':{c:round(x.mean(),2) for c,x in groups.items()},'p_kruskal':float(kw.pvalue),
            'eta2_aprox':round(float((kw.statistic-len(groups)+1)/(sum(len(x) for x in groups.values())-len(groups))),3)}
    R['colegio'][f]['SDQ_pct_alto_o_muyalto']={c:round(100*(g.loc[g.Colegio==c,'SDQ_banda']>=2).mean(),1) for c in keep}
    if f=='secundaria': R['colegio'][f]['RCADS_Dep_P90']={c:round(float(g.loc[g.Colegio==c,'RCADS_Dep'].quantile(.9)),1) for c in keep}

# ---- correlaciones Spearman con BH y IC (Fisher)
def bh(p):
    p=np.asarray(p); n=len(p); o=np.argsort(p); ranked=np.empty(n); ranked[o]=np.minimum.accumulate((p[o]*n/np.arange(1,n+1))[::-1])[::-1]; return np.minimum(ranked,1)
CORR_VARS={'secundaria':['SDQ_Emo','SDQ_Con','SDQ_Hip','SDQ_Pares','SDQ_Pro','SDQ_Total','ARI_Total','RCADS_Dep','RCADS_Anx','ERQ_Reap','ERQ_Sup','MSPSS_Fam','MSPSS_Amigos','MSPSS_Otro','MSPSS_Total','PSSM_Total','TD_Total'],
           'primaria':['SDQ_Emo','SDQ_Con','SDQ_Hip','SDQ_Pares','SDQ_Pro','SDQ_Total','ARI_Total','ERQ_Reap','ERQ_Sup','MSPSS_Fam','MSPSS_Amigos','MSPSS_Otro','MSPSS_Total','PSSM_Total','TD_Total']}
R['correlaciones']={}
for f,vars_ in CORR_VARS.items():
    g=df[df.form==f]; pairs=[]; 
    for a,b in itertools.combinations(vars_,2):
        v=g[[a,b]].dropna(); r=stats.spearmanr(v[a],v[b]); n=len(v); z=np.arctanh(r.statistic); se=1/np.sqrt(n-3)
        pairs.append({'a':a,'b':b,'rho':round(float(r.statistic),3),'ci':[round(float(np.tanh(z-1.96*se)),3),round(float(np.tanh(z+1.96*se)),3)],'p':float(r.pvalue),'n':n})
    q=bh([p['p'] for p in pairs])
    for p,qq in zip(pairs,q): p['q_bh']=float(qq)
    R['correlaciones'][f]=pairs
    mat=g[vars_].corr(method='spearman').round(2); R['correlaciones'][f+'_matriz']={'vars':vars_,'rho':mat.values.tolist()}

# ---- modelo: factores protectores → depresión / dificultades (OLS, EE robustos por conglomerado colegio)
def ols_cluster(y,X,cluster):
    X=np.column_stack([np.ones(len(X)),X]); b=np.linalg.lstsq(X,y,rcond=None)[0]; e=y-X@b; XtX_inv=np.linalg.inv(X.T@X)
    meat=np.zeros((X.shape[1],X.shape[1])); G=len(np.unique(cluster))
    for c in np.unique(cluster):
        idx=cluster==c; u=X[idx].T@e[idx]; meat+=np.outer(u,u)
    n,k=X.shape; V=XtX_inv@meat@XtX_inv*(G/(G-1))*((n-1)/(n-k)); se=np.sqrt(np.diag(V))
    t=b/se; p=2*stats.t.sf(np.abs(t),G-1); r2=1-e.var()/y.var(); return b,se,p,r2,G
R['modelos']={}
def run_model(name, sub, yv, xs):
    d=sub[[yv]+xs+['Colegio','Sexo','Edad']].dropna()
    X=d[xs].copy(); X['mujer']=(d.Sexo=='Mujer').astype(float); X['edad']=d.Edad
    Xs=(X-X.mean())/X.std(ddof=1); y=(d[yv]-d[yv].mean())/d[yv].std(ddof=1)
    b,se,p,r2,G=ols_cluster(y.values,Xs.values,d.Colegio.values)
    R['modelos'][name]={'y':yv,'n':len(d),'clusters':int(G),'R2':round(float(r2),3),'beta_std':{c:{'b':round(float(bb),3),'se':round(float(s_),3),'p':round(float(pp),4)} for c,bb,s_,pp in zip(['const']+list(Xs.columns),b,se,p)}}
sub=df[df.form=='secundaria']
run_model('dep_protectores',sub,'RCADS_Dep',['MSPSS_Fam','MSPSS_Amigos','MSPSS_Otro','PSSM_Total','ERQ_Reap','ERQ_Sup'])
run_model('anx_protectores',sub,'RCADS_Anx',['MSPSS_Fam','MSPSS_Amigos','MSPSS_Otro','PSSM_Total','ERQ_Reap','ERQ_Sup'])
run_model('sdq_total_protectores',sub,'SDQ_Total',['MSPSS_Fam','MSPSS_Amigos','MSPSS_Otro','PSSM_Total','ERQ_Reap','ERQ_Sup'])
run_model('ari_protectores',sub,'ARI_Total',['MSPSS_Fam','MSPSS_Amigos','MSPSS_Otro','PSSM_Total','ERQ_Reap','ERQ_Sup'])
run_model('conducta_td',sub,'SDQ_Con',['TD_Total','ERQ_Sup','ERQ_Reap','PSSM_Total'])
run_model('primaria_sdq_protectores',df[df.form=='primaria'],'SDQ_Total',['MSPSS_Fam','MSPSS_Amigos','MSPSS_Otro','PSSM_Total','ERQ_Reap','ERQ_Sup'])
# ICC / varianza entre colegios (secundaria, colegios >=10)
def icc1(sub,k):
    d=sub[[k,'Colegio']].dropna(); vc=d.Colegio.value_counts(); d=d[d.Colegio.isin(vc[vc>=10].index)]
    groups=[x[k].values for _,x in d.groupby('Colegio')]; n=len(d); G=len(groups); n0=(n-sum(len(g)**2 for g in groups)/n)/(G-1)
    gm=d[k].mean(); msb=sum(len(g)*(g.mean()-gm)**2 for g in groups)/(G-1); msw=sum(((g-g.mean())**2).sum() for g in groups)/(n-G)
    return round(float((msb-msw)/(msb+(n0-1)*msw)),3)
R['icc_colegio']={k:icc1(sub,k) for k in ['SDQ_Total','RCADS_Dep','RCADS_Anx','ARI_Total','PSSM_Total','MSPSS_Total','TD_Total']}

# ---- comorbilidad / solapamiento de cortes (secundaria)
g=sub; hi_sdq=g.SDQ_banda>=2; hi_ari=g.ARI_Total>2; dep90=g.RCADS_Dep>=g.RCADS_Dep.quantile(.9)
R['solapamiento']={'pct_sdq_alto':round(100*hi_sdq.mean(),1),'pct_ari_gt2':round(100*hi_ari.mean(),1),'pct_ambos':round(100*(hi_sdq&hi_ari).mean(),1),'pct_alguno':round(100*(hi_sdq|hi_ari).mean(),1),
                    'pct_ari_gt2_entre_sdq_alto':round(100*hi_ari[hi_sdq].mean(),1),'pct_ari_gt2_entre_sdq_normal':round(100*hi_ari[g.SDQ_banda==0].mean(),1),
                    'pct_dep_p90_entre_pssm_tercil_bajo':round(100*dep90[g.PSSM_Total<=g.PSSM_Total.quantile(1/3)].mean(),1),'pct_dep_p90_entre_pssm_tercil_alto':round(100*dep90[g.PSSM_Total>=g.PSSM_Total.quantile(2/3)].mean(),1),
                    'pct_dep_p90_entre_mspss_fam_tercil_bajo':round(100*dep90[g.MSPSS_Fam<=g.MSPSS_Fam.quantile(1/3)].mean(),1),'pct_dep_p90_entre_mspss_fam_tercil_alto':round(100*dep90[g.MSPSS_Fam>=g.MSPSS_Fam.quantile(2/3)].mean(),1),
                    'pct_sdq_alto_entre_pssm_tercil_bajo':round(100*hi_sdq[g.PSSM_Total<=g.PSSM_Total.quantile(1/3)].mean(),1),'pct_sdq_alto_entre_pssm_tercil_alto':round(100*hi_sdq[g.PSSM_Total>=g.PSSM_Total.quantile(2/3)].mean(),1)}
# ítems PSSM más bajos (accionables para colegios)
pss_items=rev_frame(PS,ps_rev).loc[sub.index].mean().round(2).sort_values(); R['pssm_items_secundaria']=pss_items.to_dict()
R['pssm_items_primaria']=rev_frame(PS,ps_rev).loc[df.form=='primaria'].mean().round(2).sort_values().to_dict()
# ítem de adulto de confianza
R['adulto_confianza']={f:{'pct_1_2':round(100*(df.loc[df.form==f,'PSSM7']<=2).mean(),1),'M':round(df.loc[df.form==f,'PSSM7'].mean(),2)} for f in ['secundaria','primaria']}
# MSPSS fuentes comparadas
R['mspss_fuentes']={f:{k:round(df.loc[df.form==f,k].mean(),2) for k in ['MSPSS_Fam','MSPSS_Amigos','MSPSS_Otro']} for f in ['secundaria','primaria']}

# ---- comparación con cuidadores (SDQ padres) — descriptivo, colegios distintos
cg=pd.read_csv(ROOT+'Datos_Cuidador_corregido.csv')
cg=cg[(cg['Edad del niño']>=11)&(cg['Edad del niño']<=17)]
def cg_sub(items,rev): 
    X=cg[[f'SDQ{i}' for i in items]].copy()
    for r in rev: X[f'SDQ{r}']=2-X[f'SDQ{r}']
    return X.sum(axis=1,min_count=len(items))
cgs={'SDQ_Emo':cg_sub(SUB['SDQ_Emo'],[]),'SDQ_Con':cg_sub(SUB['SDQ_Con'],[7]),'SDQ_Hip':cg_sub(SUB['SDQ_Hip'],[21,25]),'SDQ_Pares':cg_sub(SUB['SDQ_Pares'],[11,14]),'SDQ_Pro':cg_sub(SUB['SDQ_Pro'],[])}
cgs['SDQ_Total']=cgs['SDQ_Emo']+cgs['SDQ_Con']+cgs['SDQ_Hip']+cgs['SDQ_Pares']
R['cuidadores_sdq_11_17']={'n':int(cgs['SDQ_Total'].notna().sum())}
for k in cgs:
    v=cgs[k].dropna(); bi=v.map(lambda x: band(x,BANDS_PAR[k])); cnt=bi.value_counts().reindex(range(4),fill_value=0)
    R['cuidadores_sdq_11_17'][k]={'M':round(v.mean(),2),'DE':round(v.std(),2),'pct_bandas_padres':[round(100*c/len(v),1) for c in cnt]}
R['autoinforme_vs_padres_M']={k:{'estudiante_11_17':round(sub.loc[sub.Edad<=17,k].mean(),2),'cuidador':R['cuidadores_sdq_11_17'][k]['M']} for k in cgs}
# MSPSS cuidador (5 puntos) vs estudiante
if 'MSPSS_T' in cg.columns:
    R['mspss_cuidador_vs_estudiante']={'nota':'cuidador codificado 0-4; se suma 1 para llevar a 1-5','cuidador_media_item':round(float(cg['MSPSS_T'].mean()/12+1),2),'cuidador_DE':round(float((cg['MSPSS_T']/12).std()),2),'estudiante_secundaria':round(sub.MSPSS_Total.mean(),2),'estudiante_DE':round(sub.MSPSS_Total.std(),2),'n_cuidador':int(cg['MSPSS_T'].notna().sum())}

# ---- salida
json.dump(R,open(f'{OUT}/resultados.json','w'),ensure_ascii=False,indent=1,default=lambda o: float(o) if isinstance(o,(np.floating,np.integer)) else str(o))
keep=['ID','form','Edad','Sexo','Grado','Colegio','Sede','ts']+SDQ+ARI+RC+ERQ+MS+PS+TD+SCALES+['SDQ_banda','ARI_Deterioro']
df[keep].to_csv(f'{OUT}/estudiantes_puntuado_anon.csv',index=False)
print('OK', R['n_final'], 'exclusiones', R['exclusiones'])
