import io,json,re,requests,numpy as np,pandas as pd,yfinance as yf
URL="https://raw.githubusercontent.com/ahmeterenodaci/Istanbul-Stock-Exchange--BIST--including-symbols-and-logos/main/data.csv"
def symbols():
 r=requests.get(URL,timeout=20);r.raise_for_status();d=pd.read_csv(io.StringIO(r.text));c="symbol" if "symbol" in d.columns else d.columns[0]
 return sorted(set(re.sub(r"[^A-Z0-9]","",s.upper()) for s in d[c].astype(str) if 2<=len(s)<=6))
def rsi(s,n=14):
 d=s.diff();u=d.clip(lower=0).ewm(alpha=1/n,adjust=False).mean();v=(-d.clip(upper=0)).ewm(alpha=1/n,adjust=False).mean();return 100-100/(1+u/v.replace(0,np.nan))
def scan(sym):
 d=yf.download(sym+".IS",period="1y",interval="1d",auto_adjust=True,progress=False,threads=False)
 if d is None or len(d)<220:return None
 if isinstance(d.columns,pd.MultiIndex):d=d.droplevel(1,axis=1)
 c=d["Close"].astype(float);v=d["Volume"].astype(float);m20=c.rolling(20).mean();m50=c.rolling(50).mean();m200=c.rolling(200).mean();rr=rsi(c)
 mac=c.ewm(span=12,adjust=False).mean()-c.ewm(span=26,adjust=False).mean();sigm=mac.ewm(span=9,adjust=False).mean();vol=v.iloc[-1]/v.rolling(20).mean().iloc[-1];ret=(c.iloc[-1]/c.iloc[-22]-1)*100
 technical=min(100,int((20 if c.iloc[-1]>m20.iloc[-1] else 5)+(20 if m20.iloc[-1]>m50.iloc[-1] else 5)+(15 if m50.iloc[-1]>m200.iloc[-1] else 5)+(15 if 50<=rr.iloc[-1]<=70 else 8)+(15 if mac.iloc[-1]>sigm.iloc[-1] else 5)+(15 if ret>0 else 5)))
 flow=max(0,min(100,int(50+(vol-1)*35+max(0,ret)*.7)));risk=max(25,min(90,int(75-abs(rr.iloc[-1]-50)*.35)))
 fundamental=50;valuation=50;momentum=max(0,min(100,int(50+ret*1.5)))
 score=round(technical*.25+fundamental*.25+valuation*.20+flow*.10+risk*.10+momentum*.10)
 return {"code":sym,"name":sym,"price":round(float(c.iloc[-1]),2),"technical":technical,"fundamental":fundamental,"valuation":valuation,"flow":flow,"riskScore":risk,"score":score,"ret21":round(float(ret),2)}
out=[]
for s in symbols():
 try:
  x=scan(s)
  if x:out.append(x)
 except Exception as e: print("SKIP",s,e)
json.dump(out,open("data.json","w",encoding="utf-8"),ensure_ascii=False)
print("Taranan:",len(out))
