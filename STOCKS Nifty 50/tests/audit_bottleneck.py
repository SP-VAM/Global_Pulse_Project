"""
DIAGNOSTIC AUDIT: What is pulling the model down to 55.68%?
Analyzes the data, target, and features to determine whether the bottleneck is
the data, the features, or insufficient samples. Provides a clear verdict.
"""
import os, sys, warnings, json
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,ROOT); sys.path.insert(0,os.path.join(ROOT,'improve'))
from common import load_data, get_sorted_df

out={}
df=load_data()
out['total_rows']=len(df)
out['companies']=df['Company'].nunique()
out['date_range']=[str(pd.to_datetime(df['Date']).min()), str(pd.to_datetime(df['Date']).max())]
out['n_features_total_cols']=df.shape[1]

# ---- 1. TARGET ANALYSIS ----
print("="*70)
print("[1] TARGET ANALYSIS - is the target learnable?")
print("="*70)
tdf=df.dropna(subset=['Target_Multi']).copy()
vc=tdf['Target_Multi'].value_counts(normalize=True).sort_index()
out['target_distribution']={str(k):round(float(v),4) for k,v in vc.items()}
print("Target_Multi distribution (0=DOWN,1=FLAT,2=UP):")
print(vc.to_string())

# Autocorrelation of target (persistence) - if target has strong autocorr, lag features help
tdf_sorted=tdf.sort_values(['Company','Date'])
tdf_sorted['prev']=tdf_sorted.groupby('Company')['Target_Multi'].shift(1)
valid=tdf_sorted.dropna(subset=['prev'])
autocorr=valid['Target_Multi'].corr(valid['prev'])
out['target_autocorr_lag1']=round(float(autocorr),4)
print(f"\nTarget autocorrelation lag-1 (persistence): {autocorr:.4f}")
# prev-day accuracy
prev_acc=(valid['Target_Multi']==valid['prev']).mean()
out['prev_day_direction_accuracy']=round(float(prev_acc),4)
print(f"Predicting tomorrow = today's class accuracy: {prev_acc:.4f}")

# ---- 2. FEATURE STATICNESS / LEAKAGE ----
print("\n"+"="*70)
print("[2] FEATURE ANALYSIS - constant / static / near-constant columns")
print("="*70)
# Identify columns with zero variance (static) 
num_cols=df.select_dtypes(include=[np.number]).columns
static_cols=[]; near_const=[]
for c in num_cols:
    if c in ['Company_Encoded']: continue
    nunique=df[c].nunique()
    if nunique<=1:
        static_cols.append(c)
    elif nunique<=5:
        near_const.append(c)
out['static_columns']=static_cols
out['near_constant_columns']=near_const[:20]
print(f"Static columns (single value): {len(static_cols)}")
for c in static_cols: print("   -",c)
print(f"\nNear-constant columns (<=5 unique): {len(near_const)}")
print("   sample:",near_const[:20])

# ---- 3. FUNDAMENTAL FEATURES - are they point-in-time? ----
print("\n"+"="*70)
print("[3] FUNDAMENTAL FEATURES - constant per company (audit found ratio=1.0)?")
print("="*70)
for c in ['PE_Ratio','PB_Ratio','Market_Cap','Dividend_Yield']:
    if c in df.columns:
        uniq_per_comp=df.groupby('Company')[c].nunique()
        const_frac=(uniq_per_comp==1).mean()
        out[f'{c}_const_per_company']=round(float(const_frac),3)
        print(f"  {c}: {const_frac*100:.1f}% of companies have a single constant value (NOT point-in-time)")

# ---- 4. SAMPLE COUNTS ----
print("\n"+"="*70)
print("[4] SAMPLE COUNT - how much training data?")
print("="*70)
df_sorted=get_sorted_df(df.dropna(subset=['Target_Multi']))
split_idx=int(len(df_sorted)*(1-0.15))
train=df_sorted.iloc[:split_idx]
test=df_sorted.iloc[split_idx:]
out['train_rows']=len(train); out['test_rows']=len(test)
out['train_years']=int(pd.to_datetime(train['Date']).dt.year.nunique())
print(f"Train rows: {len(train)} over {pd.to_datetime(train['Date']).dt.year.nunique()} years")
print(f"Test rows: {len(test)}")
# rows per company per year
rows_per_comp_year=df.groupby(['Company',pd.to_datetime(df['Date']).dt.year]).size()
out['median_rows_per_company_year']=int(rows_per_comp_year.median())
print(f"Median rows per company-year: {rows_per_comp_year.median():.0f} (~{rows_per_comp_year.median()/252:.2f} years of daily data per company)")

# ---- 5. NEWS SENTIMENT COVERAGE ----
print("\n"+"="*70)
print("[5] NEWS SENTIMENT - is it populated?")
print("="*70)
for c in ['Sentiment_Mean','Sentiment_Count','Sentiment_Positive']:
    if c in df.columns:
        nz=(df[c].fillna(0)!=0).mean()
        out[f'{c}_nonzero_frac']=round(float(nz),4)
        print(f"  {c}: nonzero {nz*100:.1f}%")

# ---- 6. CONFUSION PATTERN OF THE 56% MODEL ----
print("\n"+"="*70)
print("[6] WHERE THE 56% MODEL FAILS (confusion pattern)")
print("="*70)
# From main_model_metrics.json
try:
    with open(os.path.join(ROOT,'models','main_model_metrics.json')) as f:
        mm=json.load(f)
    cm=mm['confusion_matrix']
    out['best_model_acc']=mm['accuracy']
    out['direction_acc']=mm['direction_accuracy']
    print(f"Best model test acc: {mm['accuracy']:.4f}, direction acc: {mm['direction_accuracy']:.4f}")
    rec=[]
    for i,name in enumerate(['DOWN','FLAT','UP']):
        rs=sum(cm[i]); rec.append(round(cm[i][i]/rs,4) if rs else 0)
        print(f"  Actual {name:5s}: recall {cm[i][i]/rs if rs else 0:.4f} ({cm[i][i]}/{rs})")
    out['per_class_recall']=dict(zip(['DOWN','FLAT','UP'],rec))
    # How many are predicted FLAT
    pred_flat=cm[0][1]+cm[1][1]+cm[2][1]
    out['predicted_flat_fraction']=round(pred_flat/sum(map(sum,cm)),4)
    print(f"  % predicted FLAT: {pred_flat/sum(map(sum,cm))*100:.1f}%")
except Exception as e:
    print("err",e)

# ---- 7. VERDICT ----
print("\n"+"="*70)
print("VERDICT")
print("="*70)
# The target autocorrelation is the key diagnostic
if out.get('prev_day_direction_accuracy',0)>0.55:
    verdict="HIGH target persistence detected -> lag/momentum features should dominate"
else:
    verdict="LOW target persistence -> next-day direction is near-random (noise floor)"
print(verdict)
out['verdict']=verdict

with open(os.path.join(ROOT,'tests','audit_bottleneck.json'),'w') as f:
    json.dump(out,f,indent=2)
print("\nSaved tests/audit_bottleneck.json")
