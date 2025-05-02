from bs4 import BeautifulSoup
import requests

def get_scraper(source):
    def scrap(urls, tags):
        res=[]
        for u in urls:
            try:
                r=requests.get(u,timeout=10,headers={"User-Agent":"Mozilla/5.0"})
                soup=BeautifulSoup(r.text,'html.parser')
                info={"url":u}
                if 'title' in tags:
                    info['title']=soup.title.string.strip() if soup.title else None
                if 'description' in tags:
                    d=soup.find('meta',attrs={'name':'description'})
                    info['description']=d['content'].strip() if d else None
                for h in ['h1','h2','h3']:
                    if h in tags:
                        info[h]=[tag.get_text(strip=True) for tag in soup.find_all(h)]
                res.append(info)
            except Exception as e:
                res.append({'url':u,'error':str(e)})
        return res
    return scrap
