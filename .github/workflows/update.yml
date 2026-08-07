import io,json,time,math,requests,numpy as np,pandas as pd,yfinance as yf

SYMBOL_URL="https://raw.githubusercontent.com/ahmeterenodaci/Istanbul-Stock-Exchange--BIST--including-symbols-and-logos/main/bist.csv"
BATCH_SIZE=25

def get_symbols():
    r=requests.get(SYMBOL_URL,timeout=30); r.raise_for_status()
    df=pd.read_csv(io.StringIO(r.text))
    df["symbol"]=df["symbol"].astype(str).str.upper().str.strip().str.replace(r"[^A-Z0-9]","",regex=True)
    df=df[df["symbol"].str.len().between(2,6)].drop_duplicates("symbol")
    return dict(zip(df["symbol"],df["name"]))

def num(x,d=0):
    try:
        x=float(x)
        return x if math.isfinite(x) else d
    except: return d

def clip(x,a=0,b=100): return int(round(max(a,min(b,x))))

def rsi(s,n=14):
    d=s.diff()
    g=d.clip(lower=0).ewm(alpha=1/n,adjust=False).mean()
    l=(-d.clip(upper=0)).ewm(alpha=1/n,adjust=False).mean()
    return (100-100/(1+g/l.replace(0,np.nan))).fillna(50)

def atr(d,n=14):
    h,l,c=d["High"],d["Low"],d["Close"]; pc=c.shift(1)
    tr=pd.concat([h-l,(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1/n,adjust=False).mean()

def adx(d,n=14):
    h,l,c=d["High"],d["Low"],d["Close"]
    up=h.diff(); down=-l.diff()
    plus=up.where((up>down)&(up>0),0.0)
    minus=down.where((down>up)&(down>0),0.0)
    pc=c.shift(1)
    tr=pd.concat([h-l,(h-pc).abs(),(l-pc).abs()],axis=1).max(axis=1)
    av=tr.ewm(alpha=1/n,adjust=False).mean().replace(0,np.nan)
    pdi=100*plus.ewm(alpha=1/n,adjust=False).mean()/av
    mdi=100*minus.ewm(alpha=1/n,adjust=False).mean()/av
    dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)
    return dx.ewm(alpha=1/n,adjust=False).mean().fillna(0)

def score(sym,name,d):
    if d is None or d.empty or not {"Close","High","Low","Volume"}.issubset(d.columns): return None
    d=d.copy()
    for k in ["Close","High","Low","Volume"]: d[k]=pd.to_numeric(d[k],errors="coerce")
    d=d.dropna(subset=["Close"])
    if len(d)<220:return None
    c,h,l,v=d["Close"],d["High"],d["Low"],d["Volume"]
    price=num(c.iloc[-1])
    m50=c.rolling(50).mean();m200=c.rolling(200).mean()
    e20=c.ewm(span=20,adjust=False).mean();e50=c.ewm(span=50,adjust=False).mean()
    rv=num(rsi(c).iloc[-1],50); ax=num(adx(d).iloc[-1])
    e12=c.ewm(span=12,adjust=False).mean();e26=c.ewm(span=26,adjust=False).mean()
    mac=e12-e26; ms=mac.ewm(span=9,adjust=False).mean()
    ret5=num((price/c.iloc[-6]-1)*100);ret21=num((price/c.iloc[-22]-1)*100);ret63=num((price/c.iloc[-64]-1)*100)
    v20=num(v.rolling(20).mean().iloc[-1]); vr=num(v.iloc[-1]/v20,1) if v20>0 else 1
    atrp=num(atr(d).iloc[-1])/price*100 if price else 0
    high20=num(c.iloc[-21:-1].max(),price); breakout=price>=high20*.995 if high20 else False
    tech=(16 if price>e20.iloc[-1] else 5)+(14 if e20.iloc[-1]>e50.iloc[-1] else 5)+(14 if m50.iloc[-1]>m200.iloc[-1] else 5)+(10 if price>m200.iloc[-1] else 3)+(8 if mac.iloc[-1]>ms.iloc[-1] else 3)+(8 if ax>=25 else (5 if ax>=18 else 2))
    technical=clip(tech)
    momentum=0
    momentum+=np.interp(ret5,[-5,0,2,5],[0,5,10,15])
    momentum+=np.interp(ret21,[-12,-2,5,15],[0,7,13,18])
    momentum+=np.interp(ret63,[-20,0,10,30],[0,7,13,17])
    momentum+=10 if 52<=rv<=70 else (7 if 45<=rv<52 or 70<rv<=75 else 3)
    momentum+=10 if breakout else 4
    momentum=clip(momentum)
    flow=clip(50+(vr-1)*35+max(0,ret5)*1.5+(8 if breakout and vr>=1.2 else 0))
    daily_vol=num(c.pct_change().rolling(20).std().iloc[-1]*np.sqrt(252)*100)
    peak60=num(c.rolling(60).max().iloc[-1]);dd=num((price/peak60-1)*100) if peak60 else 0
    risk=clip(100-max(0,daily_vol-18)*2.2-max(0,atrp-4)*5-max(0,-dd-12)*1.5,20,100)
    fundamental=valuation=kap=50
    total=round(technical*.40+momentum*.20+flow*.15+risk*.15+fundamental*.05+valuation*.05)
    return {"code":sym,"name":name,"price":round(price,2),"technical":technical,"fundamental":50,"valuation":50,"kap":50,"flow":flow,"riskScore":risk,"score":clip(total),"ret5":round(ret5,2),"ret21":round(ret21,2),"ret63":round(ret63,2),"volumeRatio":round(vr,2),"rsi":round(rv,2),"adx":round(ax,2),"atrPct":round(atrp,2),"volatility":round(daily_vol,2),"breakout":bool(breakout)}

def main():
    names=get_symbols();syms=list(names);print("BIST sembol sayısı:",len(syms))
    out=[];failed=[]
    for i in range(0,len(syms),BATCH_SIZE):
        batch=syms[i:i+BATCH_SIZE];print(f"[{i+1}-{i+len(batch)} / {len(syms)}]")
        try:
            raw=yf.download([s+".IS" for s in batch],period="1y",interval="1d",auto_adjust=True,group_by="ticker",threads=True,progress=False,timeout=30)
        except Exception as e: print("BATCH ERROR",e);raw=None
        for s in batch:
            try:
                d=None;t=s+".IS"
                if raw is not None and not raw.empty and isinstance(raw.columns,pd.MultiIndex):
                    if t in raw.columns.get_level_values(0): d=raw[t].copy()
                    elif t in raw.columns.get_level_values(1): d=raw.xs(t,axis=1,level=1).copy()
                x=score(s,names[s],d)
                if x: out.append(x)
                else: failed.append(s)
            except Exception as e: print("SKIP",s,e);failed.append(s)
        time.sleep(1)
    out.sort(key=lambda x:x["score"],reverse=True)
    with open("data.json","w",encoding="utf-8") as f: json.dump(out,f,ensure_ascii=False,allow_nan=False,separators=(",",":"))
    print("BAŞARILI:",len(out),"VERİ YOK:",len(failed));print("İLK 20:",[x["code"] for x in out[:20]])
    if len(out)<100: raise RuntimeError(f"Çok az hisse döndü: {len(out)}")
if __name__=="__main__": main()
