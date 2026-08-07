import io,json,time,requests,numpy as np,pandas as pd,yfinance as yf

SYMBOL_URL="https://raw.githubusercontent.com/ahmeterenodaci/Istanbul-Stock-Exchange--BIST--including-symbols-and-logos/main/bist.csv"
BATCH_SIZE=25

def get_symbols():
    r=requests.get(SYMBOL_URL,timeout=30); r.raise_for_status()
    df=pd.read_csv(io.StringIO(r.text))
    df["symbol"]=df["symbol"].astype(str).str.upper().str.strip().str.replace(r"[^A-Z0-9]","",regex=True)
    df=df[df["symbol"].str.len().between(2,6)].drop_duplicates("symbol")
    return dict(zip(df["symbol"],df["name"]))

def rsi(s,n=14):
    d=s.diff(); g=d.clip(lower=0).ewm(alpha=1/n,adjust=False).mean()
    l=(-d.clip(upper=0)).ewm(alpha=1/n,adjust=False).mean()
    return 100-100/(1+g/l.replace(0,np.nan))

def score(sym,name,d):
    if d is None or d.empty or not {"Close","Volume"}.issubset(d.columns): return None
    c=pd.to_numeric(d["Close"],errors="coerce").dropna()
    v=pd.to_numeric(d["Volume"],errors="coerce").fillna(0)
    if len(c)<220:return None
    m20=c.rolling(20).mean();m50=c.rolling(50).mean();m200=c.rolling(200).mean()
    rr=rsi(c); e12=c.ewm(span=12,adjust=False).mean();e26=c.ewm(span=26,adjust=False).mean()
    mac=e12-e26; ms=mac.ewm(span=9,adjust=False).mean()
    price=float(c.iloc[-1]); ret=float((price/c.iloc[-22]-1)*100); rv=float(rr.iloc[-1])
    vr=float(v.iloc[-1]/v.rolling(20).mean().iloc[-1]) if v.rolling(20).mean().iloc[-1]>0 else 1
    tech=(20 if price>m20.iloc[-1] else 8)+(20 if m20.iloc[-1]>m50.iloc[-1] else 8)+(20 if m50.iloc[-1]>m200.iloc[-1] else 8)
    tech+=(15 if 50<=rv<=70 else (10 if 40<=rv<50 or 70<rv<=75 else 5))
    tech+=(15 if mac.iloc[-1]>ms.iloc[-1] else 5)+(10 if ret>0 else 3)
    flow=int(max(0,min(100,50+(vr-1)*30+max(0,ret)*.8)))
    vol=float(c.pct_change().rolling(20).std().iloc[-1]*np.sqrt(252)*100)
    risk=int(max(20,min(90,85-vol*1.5)))
    fundamental=valuation=kap=50
    total=round(tech*.30+fundamental*.20+valuation*.15+kap*.10+flow*.15+risk*.10)
    return {"code":sym,"name":name,"price":round(price,2),"technical":int(tech),"fundamental":50,"valuation":50,"flow":flow,"riskScore":risk,"score":int(total),"ret21":round(ret,2),"volumeRatio":round(vr,2),"rsi":round(rv,2),"volatility":round(vol,2)}

def main():
    names=get_symbols(); syms=list(names)
    print("BIST sembol sayısı:",len(syms))
    out=[]; failed=[]
    for i in range(0,len(syms),BATCH_SIZE):
        batch=syms[i:i+BATCH_SIZE]
        print(f"[{i+1}-{i+len(batch)} / {len(syms)}]")
        try:
            raw=yf.download([s+".IS" for s in batch],period="1y",interval="1d",auto_adjust=True,group_by="ticker",threads=True,progress=False,timeout=30)
        except Exception as e:
            print("BATCH ERROR",e); raw=None
        for s in batch:
            try:
                d=None
                if raw is not None and not raw.empty and isinstance(raw.columns,pd.MultiIndex):
                    t=s+".IS"
                    if t in raw.columns.get_level_values(0): d=raw[t].copy()
                    elif t in raw.columns.get_level_values(1): d=raw.xs(t,axis=1,level=1).copy()
                x=score(s,names[s],d)
                if x: out.append(x)
                else: failed.append(s)
            except Exception as e: print("SKIP",s,e);failed.append(s)
        time.sleep(1)
    out.sort(key=lambda x:x["score"],reverse=True)
    with open("data.json","w",encoding="utf-8") as f: json.dump(out,f,ensure_ascii=False)
    print("BAŞARILI:",len(out),"VERİ YOK:",len(failed))
    print("İLK 10:",[x["code"] for x in out[:10]])
    if len(out)<100: raise RuntimeError(f"Çok az hisse döndü: {len(out)}")

if __name__=="__main__": main()
